import time
from datetime import timedelta
from typing import Optional, Literal
from errors import *
import discord
import asyncio
import random
import math
import copy
from vars import *

def get_counter(t: int, cooldown: Optional[int]=0) -> str:
  """
  Return a countdown message for a given time.
  t: last_x_seconds ago
  """
  td = timedelta(
    seconds = cooldown - int(time.time()) + t \
    if cooldown > 0 else \
    int(time.time()) - t
  )
  hour = td.seconds // 3600
  min = (td.seconds % 3600) // 60
  sec = td.seconds % 60
  res = ""
  if hour > 0:
    res += f"{hour}h "
  if min > 0:
    res += f"{min}m "
  res += f"{sec}s"
  return res

def fetch_stats_page(itx: discord.Interaction, user: int=None, page: Optional[Literal["Main Stats", "Command Stats", "Guild Stats", "Pet Stats"]]="Main Stats"): # game stats?
  """
  Returns user stats
  """
  if str(user) not in itx.client.db["economy"]:
    return f"{cross} It seems like this user does not own a farm!"
  userID = itx.user.id if user is None else int(user)
  db = itx.client.db["economy"][str(userID)]
  xp_emoji = "🟩"
  no_xp_emoji = "⬛"
  xp = db["levels"]["xp"]
  level = db["levels"]["level"]
  xp_needed = math.floor(xp_needed_base*1.5*(level**1.2))
  xp_bar = ""
  global_income_boost = list(itx.client.dbo["others"]["global_income_boost"].keys())
  global_income_boost = 0 if global_income_boost == [] else global_income_boost[0]
  personal_inc = 0
  personal_xp = 0
  boosts = db["boosts"]
  for type_ in boosts:
    for boost in range(len(boosts[type_])): # boost = {mult: duration}
      for k in boosts[type_][boost]:
        if type_ == "income":
          personal_inc += float(k)
        else:
          personal_xp += float(k)
  
  levels = int(xp/xp_needed * 10)
  for i in range(0, levels):
    xp_bar += xp_emoji
  for i in range(0, 10 - levels):
    xp_bar += no_xp_emoji
  base = f"""
Balance: **{db['balance']:,} {coin} | {db['income']:,} {coin} / hour**
Diamonds: **{db['diamonds']:,} {diamond}**
Level: **{db['levels']['level']:,}** (`{db['levels']['xp_mult'] + personal_xp}x`)
{xp_bar} `{xp:,} / {xp_needed:,}`
"""

  msg = {
    "Main Stats": f"""
Golden Tickets: **{db['golden_ticket']:,} {ticket}**
Reputation: **WIP**
Personal Income Multiplier: **{db['income_boost'] + personal_inc}x**
Global Income Multiplier: **{global_income_boost}x**
Daily Streak: **{db['daily_streak']:,} :arrow_up:**

**Happiness: {db['cleanliness']}%** 

Farm Age: **{((int(time.time()) - db['account_age']) // (3600*24)):,} days**
""",
    "Command Stats": f"""
Work: **{db['counting']['work']:,}**
Hunt: **{db['counting']['hunt']:,}**
Fish: **{db['counting']['fish']:,}**
Clean: **WIP**
""",
    "Guild Stats": """
Guild stats coming soon!
""",
    "Pet Stats": """
Pet stats coming soon!
"""
  }
  warning = ""
  if db["cleanliness"] < 25:
    warning = "\n*Your farm's cleanliness are at critical levels! This will affect workers' and customers' happiness, decreasing your income!*"
  return base + msg[page] + warning

async def get_quest_rewards(itx: discord.Interaction, type_: Optional[Literal["fish", "hunt", "income", "all"]]=None, to_add: bool=False):
  """
  Returns quest completion message + adds rewards
  This function is mainly for boosters calulation in the future!
  """
  reward = {
    "coins": 25000,
    "diamonds": 5
  }
  if type_ is None: return reward
  if itx.client.db["economy"][str(itx.user.id)]["last_quest"] + 3600*24 < int(time.time()): return ""
  if type_ == "all":
    done_all = True
    for q in itx.client.db["economy"][str(itx.user.id)]["quest"]:
      if not itx.client.db["economy"][str(itx.user.id)]["quest"][q]["completed"]: done_all = False
    if done_all and not itx.client.db["economy"][str(itx.user.id)]["claimed_ticket"]:
      itx.client.db["economy"][str(itx.user.id)]["golden_ticket"] += 1
      itx.client.db["economy"][str(itx.user.id)]["claimed_ticket"] = True
      await itx.client.log_action("Quests", f"**{itx.user}** claimed a golden ticket! \n[{itx.user.id}]")
      xp_msg = await itx.client.check_xp(itx.user.id, random.randint(8, 20))
      return f"You have recieved **1 {ticket}** for completing all the daily quests! Check `{prefix}shop` to view available items. \n{xp_msg}"
    return f"To claim a {ticket}, complete all daily quests!"

  add = 1 if to_add else 0
  quests = itx.client.db["economy"][str(itx.user.id)]["quest"][type_]
  quest_completed = False
  if type_ in ("hunt", "income"):
    itx.client.db["economy"][str(itx.user.id)]["quest"][type_]["times_completed"] += add
    if not quests["completed"] and quests["times_completed"] >= quests["times"]:
      quest_completed = True
  else: # type_ == "fish":
    fish_name = itx.client.db["economy"][str(itx.user.id)]["quest"]["fish"]["name"]
    itx.client.db["economy"][str(itx.user.id)]["fish"][fish_name] -= itx.client.db["economy"][str(itx.user.id)]["quest"]["fish"]["times"]
    itx.client.db["economy"][str(itx.user.id)]["quest"]["fish"]["completed"] = True
    quest_completed = True # (check done by fishing / quests command)
      
  if quest_completed:
    itx.client.db["economy"][str(itx.user.id)]["balance"] += reward["coins"]
    itx.client.db["economy"][str(itx.user.id)]["diamonds"] += reward["diamonds"]
    itx.client.db["economy"][str(itx.user.id)]["quest"][type_]["completed"] = True
    xp_msg = await itx.client.check_xp(itx.user.id, random.randint(3, 6))
    return f"\n**{type_.title()} quest completed!** You have recieved **{reward['coins']:,} {coin}** and **{reward['diamonds']} {diamond}**."

  if not quests["completed"]:
    return f"\n**{type_.title()} quest:** `{quests['times_completed']} / {quests['times']}`"
  return "\n"
      

async def view_inv(itx: discord.Interaction, button: discord.ui.Button=None):
  await itx.client.check_quests(itx)
  fishdb = itx.client.db["economy"][str(itx.user.id)]["fish"]
  fishes = {
    "tuna": fishdb["tuna"],
    "grouper": fishdb["grouper"],
    "snapper": fishdb["snapper"],
    "salmon": fishdb["salmon"],
    "cod": fishdb["cod"]
  }
  msg = ""
  for fish in fishes:
    if fishes[fish] > 0:
      msg += f"**{fishes[fish]:,}x {fish.title()}** ({fish_values[fish]:,} {coin} each) \n"
  if msg == "":
    msg = f"You have not caught any fishes! Go do some fishing and come back!"

  embed = discord.Embed(title = "Fishing Inventory", description = msg, color = blurple)
  embed.set_footer(text = "Upgrade your rod to unlock different kinds of fishes!")
  view = SellFish(itx.user.id, itx.client)
  await itx.response.send_message(embed = embed, view = view)

async def craft_rod_(itx: discord.Interaction, button: discord.ui.Button):
  materials_needed = [
    None, #index based on level
    {"description": "decreases rod cooldown", "tuna": 30, "grouper": 20, "snapper": 8, "coins": 10_000},
    {"description": "unlocks a new fish", "tuna": 45, "grouper": 32, "snapper": 18, "coins": 20_000},
    {"description": "decreases rod cooldown", "tuna": 60, "grouper": 45, "snapper": 32, "salmon": 12, "coins": 50_000},
    {"description": "unlocks a new fish", "tuna": 80, "grouper": 60, "snapper": 45, "salmon": 30, "coins": 100_000}
  ]
  fishdb = itx.client.db["economy"][str(itx.user.id)]["fish"]
  balance = itx.client.db["economy"][str(itx.user.id)]["balance"]
  fishes = {
    "tuna": fishdb["tuna"],
    "grouper": fishdb["grouper"],
    "snapper": fishdb["snapper"],
    "salmon": fishdb["salmon"],
    "cod": fishdb["cod"],
    "coins": balance
  }
  rod_level = fishdb["rod_level"]
  msg = ""
  if rod_level >= len(materials_needed):
    msg = f"Your rod is already maxed out!"
  else:
    can_upgrade = True
    for fish_needed in materials_needed[rod_level]:
      if fish_needed == "description": continue
      if fish_needed == "coins":
        msg += f"**{materials_needed[rod_level]['coins']:,} {coin}** `{balance:,} / {materials_needed[rod_level]['coins']:,}` \n"
      else:
        msg += f"**{materials_needed[rod_level][fish_needed]}x {fish_needed}** `{fishes[fish_needed]} / {materials_needed[rod_level][fish_needed]}` \n"
      if fishes[fish_needed] < materials_needed[rod_level][fish_needed]:
        can_upgrade = False
    msg += f"\n*This new rod {materials_needed[rod_level]['description']} and increases your odds to catch more rare fish!*"
  embed = discord.Embed(
    title = "Craft a Rod",
    description = msg,
    color = blurple
  )
  if rod_level >= len(materials_needed):
    await itx.response.send_message(embed=embed)
  else:
    view = CraftRodButton(itx.user.id, can_upgrade)
    await itx.response.send_message(embed=embed, view=view)
    await view.wait()
    if view.value and rod_level == itx.client.db["economy"][str(itx.user.id)]["fish"]["rod_level"]:
      for fish in materials_needed[rod_level]:
        if fish == "description": continue
        if fish == "coins":
          itx.client.db["economy"][str(itx.user.id)]["balance"] -= materials_needed[rod_level][fish]
        else:
          itx.client.db["economy"][str(itx.user.id)]["fish"][fish] -= materials_needed[rod_level][fish]
        
      itx.client.db["economy"][str(itx.user.id)]["fish"]["rod_level"] += 1
      msg = "Your rod cooldown has decreased!" if materials_needed[rod_level]["description"].startswith("decreases") else "You have unlocked a new fish!"
      embed = discord.Embed(title="New Rod Aquired", description=f"You have successfully crafted a new rod! \n**{msg}**", color=green)
      await itx.edit_original_response(embed=embed, view=None)
      await itx.client.log_action("New Rod", f"**{itx.user}** has crafted a new rod (level {itx.client.db['economy'][str(itx.user.id)]['fish']['rod_level']}! \n[{itx.user.id}]")

async def complete_quest_(itx: discord.Interaction, button: discord.ui.Button):
  if not itx.client.db["economy"][str(itx.user.id)]["quest"]["fish"]["completed"]:
    quest_msg = await get_quest_rewards(itx, "fish")
    await itx.response.send_message(quest_msg, ephemeral=True)
  else:
    await itx.response.send_message("This quest has already been completed", ephemeral=True)


class DailyButton(discord.ui.View):
  def __init__(self, userID: int):
    self.userID = userID
    self.value = False
    super().__init__(timeout=None)

  @discord.ui.button(label="Claim Daily Reward", emoji="🎁", style=discord.ButtonStyle.success)
  async def claim_daily(self, itx: discord.Interaction, button: discord.ui.Button):
    self.value = True
    button.disabled = True
    self.stop()
    await itx.response.edit_message(view=self)

  async def interaction_check(self, itx: discord.Interaction):
    if self.userID == itx.user.id:
      return True
    return await itx.client.itx_check(itx)

class StatsDropdown(discord.ui.Select):
  def __init__(self, user):
    self.user = user
    options = [
      discord.SelectOption(label="Main Stats", description="View your general stats", emoji="🟩"),
      discord.SelectOption(label="Command Stats", description="View how many times you used a command", emoji="🟥"),
      discord.SelectOption(label="Guild Stats", description="View your guild's stats", emoji="🟦"),
      discord.SelectOption(label="Pet Stats", description="Your favourite colour is blue", emoji="🟩"),
    ]
    super().__init__(placeholder="View more stats... ", min_values=1, max_values=1, options=options)

  async def callback(self, itx: discord.Interaction):
    # The values attribute gets a list of the user's
    # selected options. We only want the first one.
    embed = discord.Embed(title=f"{self.user.name}'s Stats", description=fetch_stats_page(itx, self.user.id, self.values[0]), color=green)
    await itx.response.edit_message(embed=embed)


class CraftRodButton(discord.ui.View):
  def __init__(self, userID: int, can_upgrade: bool):
    self.userID = userID
    self.value = False
    super().__init__(timeout=120)
    self.craft.disabled = not can_upgrade 

  @discord.ui.button(label="Craft Rod", emoji="🧵", style=discord.ButtonStyle.success)
  async def craft(self, itx: discord.Interaction, button: discord.ui.Button):
    self.value = True
    button.disabled = True
    self.stop()
    await itx.response.edit_message(view=self)

  async def interaction_check(self, itx: discord.Interaction):
    if self.userID == itx.user.id:
      return True
    return await itx.client.itx_check(itx)

class FishingWelcomeButton(discord.ui.View):
  def __init__(self, userID):
    self.userID = userID
    self.value = False
    super().__init__(timeout=120)
    self.add_item(CallBackButton())

  @discord.ui.button(label="Go Fishing", emoji="🎣", style=discord.ButtonStyle.success)
  async def start_fishing(self, itx: discord.Interaction, button: discord.ui.Button):
    self.value = True
    for child in self.children:
      child.disabled = True
    self.stop()
    await itx.response.edit_message(view=self)

  @discord.ui.button(label="View Inventory", emoji="🧰", style=discord.ButtonStyle.success)
  async def get_inventory(self, itx: discord.Interaction, button: discord.ui.Button):
    await view_inv(itx, button)

  @discord.ui.button(label="Craft New Rod", emoji="🧵", style=discord.ButtonStyle.success)
  async def craft_rod(self, itx: discord.Interaction, button: discord.ui.Button):
    await craft_rod_(itx, button)

  async def interaction_check(self, itx: discord.Interaction):
    if self.userID == itx.user.id:
      return True
    return await itx.client.itx_check(itx)

class FishButtons(discord.ui.View):
  def __init__(self, userID, cooldown, *, timeout=5*60):
    self.userID = userID
    self.value = None
    self.cooldown = cooldown
    super().__init__(timeout=timeout)
    self.add_item(CallBackButton())
    
  @discord.ui.button(label="Fish Again", style = discord.ButtonStyle.green, emoji = "🎣")
  async def fish_again(self, itx:discord.Interaction, button:discord.ui.Button):
    if (str(self.userID) not in itx.client.cache["fishing_cooldown"]["users"] or itx.client.cache["fishing_cooldown"]["users"][str(itx.user.id)] + self.cooldown <= int(time.time())):
      itx.client.cache["fishing_cooldown"]["users"][str(itx.user.id)] = int(time.time()) 
      self.value = True
      for child in self.children:
        child.disabled = True
      self.stop()
      await itx.response.edit_message(view = self)
    else:
      time_left = itx.client.cache["fishing_cooldown"]["users"][str(itx.user.id)] + self.cooldown - int(time.time())
      embed = discord.Embed(title = "Fishing", description = f"{cross} You can only fish once every **{self.cooldown} seconds**! ({time_left}s left) \n*Upgrade your fishing rod to decrease the cooldown!*", color = red)
      await itx.response.send_message(embed = embed, ephemeral = True)

  @discord.ui.button(label = "View Inventory", style = discord.ButtonStyle.green, emoji = "🧰")
  async def view_inventory(self, itx: discord.Interaction, button: discord.ui.Button):
    await view_inv(itx, button)

  @discord.ui.button(label = "Craft New Rod", style = discord.ButtonStyle.green, emoji = "🧵")
  async def craft_rod(self, itx: discord.Interaction, button: discord.ui.Button):
    await craft_rod_(itx, button)

  async def interaction_check(self, itx: discord.Interaction):
    if self.userID == itx.user.id:
      return True
    return await itx.client.itx_check(itx)

class SellIndiFish(discord.ui.Button):
  def __init__(self, fish):
    super().__init__(style=discord.ButtonStyle.success, label=f"Sell {fish.title()}")
    self.fish = fish

  async def callback(self, itx: discord.Interaction):
    view: SellFish = self.view
    self.disabled = True
    await itx.response.edit_message(view = view)
    await view.sell_fish(view, itx, self.fish)

  async def interaction_check(self, itx: discord.Interaction):
    if self.userID == itx.user.id:
      return True
    return await itx.client.itx_check(itx)
    

class SellFish(discord.ui.View):
  def __init__(self, userID, dbval, *, timeout=5*60):
    self.userID = userID
    self.value = None
    self.dbval = dbval
    super().__init__(timeout=timeout)
    self.complete_quest.label = "Complete quest: Submit " + str(dbval.db["economy"][str(userID)]["quest"]["fish"]["times"]) + " " + dbval.db["economy"][str(userID)]["quest"]["fish"]["name"] + "s"
    self.fish_name = dbval.db["economy"][str(userID)]["quest"]["fish"]["name"]
    self.fish_needed = dbval.db["economy"][str(userID)]["quest"]["fish"]["times"]
    self.complete_quest.disabled = dbval.db["economy"][str(userID)]["quest"]["fish"]["completed"] or dbval.db["economy"][str(userID)]["fish"][self.fish_name] < self.fish_needed
    #self.sell_tuna.label = "tuna"
    fishdb = self.dbval.db["economy"][str(userID)]["fish"]
    fishes = {
    "tuna": fishdb["tuna"],
    "grouper": fishdb["grouper"],
    "snapper": fishdb["snapper"],
    "salmon": fishdb["salmon"],
    "cod": fishdb["cod"]
  }
    for fish in fishes:
      if fishes[fish] > 0:
        self.add_item(SellIndiFish(fish))
    self.add_item(CallBackButton())

  async def sell_fish(self, ins, itx: discord.Interaction, type: str):
    await itx.edit_original_response(view = ins)
    fishdb = itx.client.db["economy"][str(itx.user.id)]["fish"]
    fishes = {
    "tuna": fishdb["tuna"],
    "grouper": fishdb["grouper"],
    "snapper": fishdb["snapper"],
    "salmon": fishdb["salmon"],
    "cod": fishdb["cod"]
  }
    temp = {type: fishes[type]} if type != True else fishes
    money = 0
    for fish in temp:
      money += fish_values[fish] * fishes[fish]
      itx.client.db["economy"][str(itx.user.id)]["fish"][fish] = 0

    itx.client.db["economy"][str(itx.user.id)]["balance"] += money
    balance = itx.client.db["economy"][str(itx.user.id)]["balance"]
    embed = discord.Embed(title = "Fish", description = f"You sold all your {'fishes' if type == True else type} for a total of **{money:,}{coin}**! \nBalance: **{balance:,}{coin}**", color = green)
    await itx.followup.send(embed = embed)
    
    
  @discord.ui.button(label="Sell All", style = discord.ButtonStyle.green, emoji = "💸")
  async def sell_all(self, itx: discord.Interaction, button: discord.ui.Button):
    for child in self.children:
      child.disabled = True
    await itx.response.edit_message(view = self)
    await self.sell_fish(self, itx, True)

  @discord.ui.button(label="Complete Quest", style = discord.ButtonStyle.blurple, row=3)
  async def complete_quest(self, itx: discord.Interaction, button: discord.ui.Button):
    await complete_quest_(itx, button)
    button.disabled = True
    await itx.edit_original_response(view=self)
    

  async def interaction_check(self, itx: discord.Interaction):
    if self.userID == itx.user.id:
      return True
    return await itx.client.itx_check(itx)

class BackButton(discord.ui.View):
  def __init__(self, user=None):
    self.user = user
    super().__init__(timeout=None)
    self.add_item(CallBackButton())

class CallBackButton(discord.ui.Button):
  def __init__(self):
    super().__init__(label="Back", style=discord.ButtonStyle.blurple)
    
  async def callback(self, itx: discord.Interaction):
    await get_stats(itx)

class QuestsButton(discord.ui.View):
  def __init__(self, itx):
    self.userID = itx.user.id
    super().__init__(timeout=None)
    self.claim_ticket.disabled = itx.client.db["economy"][str(self.userID)]["claimed_ticket"]
    self.complete_quest.label = "Complete fishing quest: Submit " + str(itx.client.db["economy"][str(self.userID)]["quest"]["fish"]["times"]) + " " + itx.client.db["economy"][str(self.userID)]["quest"]["fish"]["name"] + "s"
    self.fish_name = itx.client.db["economy"][str(self.userID)]["quest"]["fish"]["name"]
    self.fish_needed = itx.client.db["economy"][str(self.userID)]["quest"]["fish"]["times"]
    self.complete_quest.disabled = itx.client.db["economy"][str(self.userID)]["quest"]["fish"]["completed"] or itx.client.db["economy"][str(self.userID)]["fish"][self.fish_name] < self.fish_needed
    self.add_item(CallBackButton())

  @discord.ui.button(label="Complete Fishing Quest", style=discord.ButtonStyle.blurple)
  async def complete_quest(self, itx: discord.Interaction, button: discord.ui.Button):
    await complete_quest_(itx, button)
    button.disabled = True
    await itx.edit_original_response(view=self)

  @discord.ui.button(label="Claim Golden Ticket", style=discord.ButtonStyle.blurple)
  async def claim_ticket(self, itx: discord.Interaction, button: discord.ui.Button):
    msg = await get_quest_rewards(itx, "all")
    if (claimed := itx.client.db["economy"][str(self.userID)]["claimed_ticket"]):
      button.disabled = True
      await itx.response.edit_message(view=self)
    embed = discord.Embed(title="Quests", description=msg, color=blurple)
    await itx.response.send_message(embed=embed, ephemeral=not claimed)

  async def interaction_check(self, itx: discord.Interaction):
    if self.userID == itx.user.id:
      return True
    return await itx.client.itx_check(itx)

class StatsButtons(discord.ui.View):
  def __init__(self, user):
    super().__init__(timeout=None)
    self.add_item(StatsDropdown(user))

  @discord.ui.button(label = "Daily", style = discord.ButtonStyle.success)
  async def to_daily(self, itx: discord.Interaction, button: discord.ui.Button):
    await get_daily(itx)

  @discord.ui.button(label = "Upgrades", style = discord.ButtonStyle.success)
  async def to_upgrade(self, itx: discord.Interaction, button: discord.ui.Button):
    await get_upgrade(itx, "view", "Farm")

  @discord.ui.button(label = "Quests", style = discord.ButtonStyle.success)
  async def to_quests(self, itx: discord.Interaction, button: discord.ui.Button):
    await get_quests(itx)

  @discord.ui.button(label = "Fish", style = discord.ButtonStyle.success)
  async def to_fish(self, itx: discord.Interaction, button: discord.ui.Button):
    await get_fish(itx)

  @discord.ui.button(label = "Work", style = discord.ButtonStyle.success)
  async def to_work(self, itx: discord.Interaction, button: discord.ui.Button):
    await get_work(itx)

  @discord.ui.button(label = "Boosts", style = discord.ButtonStyle.success)
  async def to_boosts(self, itx: discord.Interaction, button: discord.ui.Button):
    await get_boosts(itx)

  async def interaction_check(self, itx: discord.Interaction):
    blacklist = itx.client.dbo["others"]["user_blacklist"]
    if str(itx.user.id) in blacklist:
      if int(time.time()) < blacklist[str(itx.user.id)]["time"]:
        duration = blacklist[str(itx.user.id)]["time"]
        reason = blacklist[str(itx.user.id)]["reason"]
        await itx.response.send_message(
          f"""
You are currently blacklisted! 
Reason: {reason}
Blacklist ends <t:{duration}:R>
Dm me `.info` to join the support server!
""",
          ephemeral = True
  )
        return False
    return True

class UpgradesButton(discord.ui.View):
  def __init__(self, userID):
    self.userID = userID
    self.value = False
    super().__init__(timeout=None)
    self.add_item(CallBackButton())

  @discord.ui.button(label = "Upgrade Again", style = discord.ButtonStyle.blurple)
  async def upgrade_again(self, itx: discord.Interaction, button: discord.ui.Button):
    self.value = True
    for child in self.children:
      child.disabled = True
    await itx.response.edit_message(view=self)
    self.stop()

  async def interaction_check(self, itx: discord.Interaction):
    if self.userID == itx.user.id:
      return True
    return await itx.client.itx_check(itx)

async def get_daily(itx):

  def get_streak_emoji(streak: int, voted: bool=False):
    reward = 5 # how many daily streak do you need to recieve reward?
    emoji, streak_emoji, no_streak_emoji = "", "🟡", "⚫"
    streak_msg = ""
    
    for number in range(streak % reward):
      emoji += streak_emoji
    for number in range(reward - streak % reward):
      emoji += no_streak_emoji

    if streak%reward == 0:
      earned = 1 if not voted else 2
      itx.client.db["economy"][str(itx.user.id)]["golden_ticket"] += earned
      streak_msg = f"\nYou earned **{earned} {ticket}**"
      
    return emoji + streak_msg
  
  if itx.client.db["economy"][str(itx.user.id)]["levels"]["level"] >= 3:
    color = green
    streak_msg = ""
    income = itx.client.db["economy"][str(itx.user.id)]["income"]
    balance = itx.client.db["economy"][str(itx.user.id)]["balance"]
    last_daily = itx.client.db["economy"][str(itx.user.id)]["last_daily"]
    currenttime = int(time.time())
    daily_coins = income * 5
    daily_streak = itx.client.db["economy"][str(itx.user.id)]["daily_streak"]
    
    if currenttime >= (last_daily + 86400):
      embed = discord.Embed(
        title = "Claim Daily Reward",
        description = f"""
Click the button below to claim your daily reward!

Tip: Vote for the **{bot_name} discord server** to earn double daily rewards, including golden tickets!
{adv_msg}
""",
        color = blurple
      )
      view = DailyButton(itx.user.id)
      await itx.response.send_message(embed=embed, view=view)
      await view.wait()
      # Recheck in case of exploits
      last_daily = itx.client.db["economy"][str(itx.user.id)]["last_daily"]
      currenttime = int(time.time())
      if (not view.value or not currenttime >= (last_daily + 86400)):
        return await itx.followup.send("You already claimed your daily reward :/", ephemeral=True)
      streak_bonus = 500
      if currenttime >= (last_daily + 86400*4) and daily_streak != 0:
        itx.client.db["economy"][str(itx.user.id)]["daily_streak"] = 1
        streak_msg = f"*You lost your **{daily_streak} days** daily streak!*"
      else:
        itx.client.db["economy"][str(itx.user.id)]["daily_streak"] += 1
      daily_streak = itx.client.db["economy"][str(itx.user.id)]["daily_streak"]
      streak_coins = itx.client.db["economy"][str(itx.user.id)]["daily_streak"] * streak_bonus if daily_streak != 1 else 0
      upd_user = itx.guild.get_member(itx.user.id)
      voted = upd_user.get_role(server_voter_role)
      print(voted)
      vote_bonus = daily_coins + streak_coins if voted else 0
        
      daily_streak = itx.client.db["economy"][str(itx.user.id)]["daily_streak"]
      streak_emoji = get_streak_emoji(daily_streak, voted)
      total_coins = daily_coins + streak_coins + vote_bonus
      xp_msg = await itx.client.check_xp(itx.user.id, 5)
  
      itx.client.db["economy"][str(itx.user.id)]["last_daily"] = time.time()
      itx.client.db["economy"][str(itx.user.id)]["balance"] += total_coins
      updated_bal = balance + total_coins
      unlocked_fragments = len(itx.client.db["economy"][str(itx.user.id)]["unlocked_upgrades"]) > 1
      fragment_msg = ""
      if unlocked_fragments:
        fragment_msg = "\n" + await itx.client.add_fragment(itx)
      await itx.client.log_action("Daily Reward", f"**{itx.user}** has claimed their daily reward! \nDaily, Streak bonus, vote bonus, total: {daily_coins:,}, {streak_coins:,}, {vote_bonus:,}, {total_coins:,} \nStreak: `{daily_streak}` \n[{itx.user.id}]")
      msg = f"""
Daily reward: **{daily_coins:,}{coin}** 
Streak Bonus: **{streak_coins:,}{coin}** 
Vote Bonus: **{vote_bonus:,} {coin}**
Total Reward: **{total_coins:,}{coin}** 

Current Balance: **{updated_bal:,}{coin}** 

Daily Streak: `{daily_streak}`  
{streak_emoji} 
*Get a {ticket} for every 5 daily streaks!* 
{xp_msg}
{streak_msg} {fragment_msg}"""
      
    else:
      td = timedelta(seconds=86400-currenttime+last_daily)
      hours_left = td.seconds // 3600
      mins_left = (td.seconds % 3600) // 60
      secs_left = td.seconds % 60
      msg, color = f"You can claim your daily gift in `{hours_left}h {mins_left}m {secs_left}s`. \nDaily Streak: `{daily_streak}`", red
    
  else:
    msg = "You need to be level 3 and above to claim your daily reward!"
    color = red
  embed = discord.Embed(
      title = "Daily Reward",
      description = msg,
      color = color
    )
  view = BackButton()
  if not itx.response.is_done():
    await itx.response.send_message(embed=embed, view=view)
  else:
    await itx.followup.send(embed=embed, view=view)

async def get_stats(itx, user=None):
  if user is None:
    user = itx.user
  embed = discord.Embed(
    title = f"{user.name}'s profile:",
    description = f"Getting {user.name}'s statistics...", 
    color = discord.Color.blue()
  )
  embed.set_footer(text = f"Do {itx.client.prefix}stats <@user> to check someone's profile!")
  await itx.response.send_message(embed=embed)
  new_embed = discord.Embed(title=f"{user.name}'s Stats", description=fetch_stats_page(itx, user.id), color=discord.Color.blue())
  new_embed.set_footer(text = f"Do {itx.client.prefix}stats <@user> to check someone's profile!")
  view = StatsButtons(user)
  await itx.edit_original_response(embed=new_embed, view=view)

async def get_upgrade(itx: discord.Interaction, type: str, name: str):
  """Upgrades!!!"""
  # TODO: Cocoa bean grinder, chocolate moudling machine, storage tank, chocolate freezer, packaging machine, workers
  # Formula for upgrades: base_cost * multiplier ** level (start from 1)
  title, color, multiplier = "Upgrades", blurple, 1.75
  upgrades_map = {
    "farm": ["farmer", "store", "van", "storage_tank", "warehouse"],
    "factory": ["bean_grinder", "chocolate_moulder", "chocolate_freezer", "workers", "chocolate_packager"],
    "distribution_center": ["fork_lifts", "packaging_machine", "storage_shelves", "trucks", "managers"]
  }
  # [a for a in [i for i in list(upgrades_map.values())]]
  if type == "buy":
    for upgrade_location in upgrades_map:
      if name in upgrades_map[upgrade_location]:
        upgrade_type = upgrade_location
        break
  else:
    upgrade_type = name.lower().replace(" ", "_")
  if name is not None and upgrade_type not in itx.client.db["economy"][str(itx.user.id)]["unlocked_upgrades"]:
    embed = discord.Embed(title=title, description=f"{cross} You have not unlocked the **{upgrade_type.replace('_', ' ')}** yet! \nUnlock more upgrades using `{itx.client.prefix}location`.", color=red)
    await itx.response.send_message(embed=embed, ephemeral=True)
    return

  base_upgrades = {
    "farmer": 50, "store": 250, "van": 4500, "storage_tank": 10000, "warehouse": 40000,
    "bean_grinder": 15000, "chocolate_moulder": 30000, "chocolate_freezer": 50000, "workers": 58000, "chocolate_packager": 72_000, "fork_lifts": 52_000, "packaging_machine": 120_000, "storage_shelves": 220_000, "trucks": 350_000, "managers": 400_000
  }
  upgrade_again = True
  while upgrade_again:
    upgrade_again = False
    upgrades = {}
    upgrades.update(copy.deepcopy(itx.client.db["economy"][str(itx.user.id)]["upgrades"]["farm"]))
    upgrades.update(copy.deepcopy(itx.client.db["economy"][str(itx.user.id)]["upgrades"]["factory"]))
    upgrades.update(copy.deepcopy(itx.client.db["economy"][str(itx.user.id)]["upgrades"]["distribution_center"]))
    # IGNORE COORDS (OLD FEATURE)
    #Farm
    upgrades["farmer"]["income"] = 25
    upgrades["farmer"]["coords"] = (250, 200)
    upgrades["store"]["income"] = 40
    upgrades["store"]["coords"] = (800, 200)
    upgrades["van"]["income"] = 60
    upgrades["van"]["coords"] = (860, 300)
    upgrades["storage_tank"]["income"] = 85
    upgrades["storage_tank"]["coords"] = (1000, 500)
    upgrades["warehouse"]["income"] = 120
    upgrades["warehouse"]["coords"] = (400, 500)
    # Factory 
    upgrades["bean_grinder"]["income"] = 80
    upgrades["bean_grinder"]["coords"] = (250, 200)
    upgrades["chocolate_moulder"]["income"] = 100
    upgrades["chocolate_moulder"]["coords"] = (800, 200)
    upgrades["chocolate_freezer"]["income"] = 135
    upgrades["chocolate_freezer"]["coords"] = (800, 350)
    upgrades["workers"]["income"] = 250 #workers more = less mechenical breakdown
    upgrades["workers"]["coords"] = (800, 450)
    upgrades["chocolate_packager"]["income"] = 320
    upgrades["chocolate_packager"]["coords"] = (250, 450)
    # Distribution center
    upgrades["fork_lifts"]["income"] = 125
    upgrades["fork_lifts"]["coords"] = (800, 200)
    upgrades["packaging_machine"]["income"] = 180
    upgrades["packaging_machine"]["coords"] = (800, 500)
    upgrades["storage_shelves"]["income"] = 250
    upgrades["storage_shelves"]["coords"] = (1000, 500)
    upgrades["trucks"]["income"] = 350
    upgrades["trucks"]["coords"] = (1000, 500)
    upgrades["managers"]["income"] = 500
    upgrades["managers"]["coords"] = (1000, 500)

    # cost 
    for upgrade in upgrades:
      upgrades[upgrade]["cost"] = int(base_upgrades[upgrade]*multiplier**(upgrades[upgrade]["level"] - 1))

    if type == "view":
      msg = ""
      for upgrade in upgrades_map[upgrade_type]:
        maxed = upgrades[upgrade]['level'] >= upgrades[upgrade]['max']
        cost = upgrades[upgrade]['cost']
        if cost != "Maxed!": cost = f"{upgrades[upgrade]['cost']:,}"
        msg += f"""
{upgrades[upgrade]['name']} | `{upgrades[upgrade]['level']}/{upgrades[upgrade]['max']}` 
Income: **{upgrades[upgrade]['income']} {coin} / hr** 
Cost: **{cost if not maxed else 'Maxed!'} {coin if not maxed else ''}** \n
"""
      balance = itx.client.db["economy"][str(itx.user.id)]["balance"]
      msg += f"Balance: **{balance:,} {coin}** \nView more upgrades using `{prefix}upgrades view <location>` \nUpgrade using `{prefix}upgrades buy <upgrade>`"
      embed = discord.Embed(title = f"{name} Upgrades", description = msg, color = color)
      #embed.set_image(url="attachment://temp.png")
      view = BackButton()
      await itx.response.send_message(embed = embed, view=view) #file=file when img added
    else:
      view = discord.utils.MISSING
      cost = upgrades[name]["cost"]
      balance = itx.client.db["economy"][str(itx.user.id)]["balance"]
      if balance >= cost and upgrades[name]["level"] < upgrades[name]["max"]:
        itx.client.db["economy"][str(itx.user.id)]["upgrades"][upgrade_type][name]["level"] += 1
        itx.client.db["economy"][str(itx.user.id)]["balance"] -= cost
        itx.client.db["economy"][str(itx.user.id)]["income"] += upgrades[name]["income"]
        balance -= cost
        income = itx.client.db["economy"][str(itx.user.id)]["income"]
        level = itx.client.db["economy"][str(itx.user.id)]["upgrades"][upgrade_type][name]["level"]
        xp_msg = await itx.client.check_xp(itx.user.id, math.floor(level**(4/5)))
        msg, color, ephemeral = f"You have upgraded your **{name.replace('_', ' ')}** to **level {level}** \nBalance: **{balance} {coin}** \nIncome: **{income} {coin} / hr** {xp_msg}", green, False 
        upgrade_again = True
        view = UpgradesButton(itx.user.id)
      elif upgrades[name]["level"] >= upgrades[name]["max"]:
        msg, color, ephemeral = f"You have maxed out this upgrade!", red, True
      else:
        msg, color, ephemeral = f"You do not have enough money for this upgrade! \nBalance: **{balance} {coin}** \nAmount needed: **{cost} {coin}**", red, True
      embed = discord.Embed(title = "Upgrade", description = msg, color = color)
      if not itx.response.is_done():
        await itx.response.send_message(embed=embed, ephemeral=ephemeral, view=view)
      else:
        await itx.followup.send(embed=embed, ephemeral=ephemeral, view=view)
      if view is discord.utils.MISSING: 
        break
      await view.wait()
      # looped

async def get_quests(itx):
# 3 quests. 1 fishing, 1 hunting, 1 work x times
  new_q, fish_msg, hunt_msg, work_msg = await itx.client.check_quests(itx)
  last_quest = itx.client.db["economy"][str(itx.user.id)]["last_quest"]
  new_q_msg = "**A new set of quests has been generated!**\n" if new_q else ""
  embed = discord.Embed(title = "Daily Quests", description = f"{new_q_msg}Quest resetting <t:{last_quest + 86400}:R> \nEach quest gives you **25,000 {coin}** and **5 {diamond}** \nCompleting all quests gives you **1 {ticket}**", color = blurple)
  embed.add_field(name = "Fishing Quest: ", value = fish_msg, inline = False)
  embed.add_field(name = "Hunting Quest: ", value = hunt_msg, inline = False)
  embed.add_field(name = "Income Quest: ", value = work_msg, inline = False)
  view = QuestsButton(itx)
  await itx.response.send_message(embed=embed, view=view)

async def get_fish(itx: discord.Interaction):
  view = "placeholder"
  fishdb = itx.client.db["economy"][str(itx.user.id)]["fish"]
  fishes = ["tuna", "grouper", "snapper", "salmon", "cod"]
  fish_xp = {"tuna": 1, "grouper": 1, "snapper": 3, "salmon": 10, "cod": 25}
  
  loop, first_loop = True, True
  while loop:
    itx.client.increment_command_counter()
    odds = random.randint(1, 101)
    level = itx.client.db["economy"][str(itx.user.id)]["fish"]["rod_level"]
    if level == 1:
      cooldown = 15
      if odds < 65: fish = "tuna"
      if 65 <= odds < 90: fish = "grouper"
      if odds >= 90: fish = "snapper"
    if level == 2:
      cooldown = 10
      if odds < 60: fish = "tuna"
      if 60 <= odds < 85: fish = "grouper"
      if odds >= 85: fish = "snapper"
    if level == 3:
      cooldown = 10
      if odds < 55: fish = "tuna"
      if 55 <= odds < 80: fish = "grouper"
      if 80 <= odds < 99: fish = "snapper"
      if odds >= 99: fish = "salmon" # 2% chance
    if level == 4:
      cooldown = 5
      if odds < 50: fish = "tuna"
      if 50 <= odds < 75: fish = "grouper"
      if 75 <= odds < 90: fish = "snapper"
      if odds >= 90: fish = "salmon"
    if level == 5:
      cooldown = 5
      if odds < 40: fish = "tuna"
      if 40 <= odds < 65: fish = "grouper"
      if 65 <= odds < 88: fish = "snapper"
      if 88 <= odds < 100: fish = "salmon"
      if odds >= 100: fish = "cod" if random.randint(0, 1) else "tuna"
    #cooldown = 1 # uncomment for testing
    #if itx.user.id == owner: cooldown = 1
    
    if first_loop:
      embed = discord.Embed(
        title="Fishing Stats",
        description=f"""
  Total Fish Caught: TODO
  Rod Level: **{level}**
  Fishing Cooldown: **{cooldown}s**
  \nTip: *Upgrade your rod to decrease cooldowns and increase rewards!*
  """,
        color=blurple
      )
      view = FishingWelcomeButton(itx.user.id)
      await itx.response.send_message(embed=embed, view=view)
      first_loop = False
      await view.wait()
      if not view.value:
        return
    if time.time() < itx.client.db["economy"][str(itx.user.id)]["fish"]["last_fish"] + cooldown:
      view = None
      embed = discord.Embed(
        title = "Fishing", 
        description = f"You cannot fish so soon! You can fish once every **{cooldown} seconds**. \n*Upgrade your fishing rod to decrease the cooldown!*", 
        color = discord.Color.orange()
      )
      loop = False
      view = BackButton()
    elif time.time() >= itx.client.db["economy"][str(itx.user.id)]["fish"]["last_fish"] + cooldown:
      luck = random.randint(1,101)
      if luck > 10:
        itx.client.db["economy"][str(itx.user.id)]["fish"][fish] += 1
        itx.client.db["economy"][str(itx.user.id)]["fish"]["last_fish"] = int(time.time())
        xp_msg = await itx.client.check_xp(itx.user.id, fish_xp[fish])
        unlocked_fragments = len(itx.client.db["economy"][str(itx.user.id)]["unlocked_upgrades"]) > 1
        fragment_msg = ""
        if random.randint(1, 101) > 95 and unlocked_fragments:
          fragment_msg = "\n" + await itx.client.add_fragment(itx)
        embed = discord.Embed(
          title = "Fishing", 
          description = f"You went fishing and caught a **{'LEGENDARY ' if fish == 'cod' else ''}{fish}**! {xp_msg} {fragment_msg}", 
          color = discord.Color.green()
        )
        if fish == "cod": await itx.client.log_action("Cod Obtained", f"**{itx.user}** went fishing and got a **LEGENDARY COD**!")
      else:
        money = random.randint(100*level, 1000*level)
        itx.client.db["economy"][str(itx.user.id)]["balance"] -= money
        itx.client.db["economy"][str(itx.user.id)]["fish"]["last_fish"] = int(time.time())
        if itx.client.db["economy"][str(itx.user.id)]["balance"] < 0: itx.client.db["economy"][str(itx.user.id)]["balance"] = 0
        embed = discord.Embed(
          title = "Fishing", 
          description = f"You went fishing and fished out an eel! You got electrocuted and had to pay **{money}{coin}** to see the doctor", 
          color = discord.Color.red()
        )
      itx.client.cache["fishing_cooldown"]["users"][str(itx.user.id)] = int(time.time())
      itx.client.db["economy"][str(itx.user.id)]["counting"]["fish"] += 1
      view = FishButtons(itx.user.id, cooldown) if view is not None else None
    if not itx.response.is_done():
      await itx.response.send_message(embed = embed, view = view)
    else:
      await itx.followup.send(embed = embed, view = view)
    if view is not None:
      await view.wait()
      if not view.value:
        loop = False

async def get_work(itx: discord.Interaction):
  # to self: add multipliers and boosters
  color = blurple
  quest_msg = await get_quest_rewards(itx, "income")
  last_work = itx.client.db["economy"][str(itx.user.id)]["last_work"]
  level = itx.client.db["economy"][str(itx.user.id)]["levels"]["level"]
  time_diff = int(time.time()) - last_work
  cooldown = 60*10
  if time_diff >= cooldown:  

    # Selling stuff
    prices = {"normal": 2, "dark": 3, "milk": 4, "almond": 6, "white": 8, "caramel": 12, "peanut butter": 15, "strawberry": 20}
    fragments = itx.client.db["economy"][str(itx.user.id)]["recipes"]["fragments"]
    unlocked_fragments = len(itx.client.db["economy"][str(itx.user.id)]["unlocked_upgrades"]) > 1
    recipes = [rec for rec in fragments if fragments[rec] >= 20]
    income = itx.client.db["economy"][str(itx.user.id)]["income"]
    amt_sold = random.randint(income//5, int(income*1.5))*(level//4 if level//4 > 1 else 1)
    recipes_amt_sold = {}
    
    if unlocked_fragments: 
      recipes_amt_sold = {recipe: random.randint(income//75, income//10) for recipe in recipes}
      
    total = amt_sold
    if recipes_amt_sold != {}:
      for rec in recipes_amt_sold:
        total += recipes_amt_sold[rec]*prices[rec]*fragments[rec]//20
    
    latest_location = itx.client.db["economy"][str(itx.user.id)]["unlocked_upgrades"][-1]
    if latest_location == "farm": item_sold = "bags of cocoa beans"
    if latest_location == "factory": item_sold = "chocolate bars"
    if latest_location == "distribution_center": item_sold = "boxes of chocolate"

    itx.client.db["economy"][str(itx.user.id)]["balance"] += total
    itx.client.db["economy"][str(itx.user.id)]["last_work"] = int(time.time())
    itx.client.db["economy"][str(itx.user.id)]["counting"]["work"] += 1
    
    balance = itx.client.db["economy"][str(itx.user.id)]["balance"]
    fragment_msg = ""
    if random.randint(1, 101) > 75 and unlocked_fragments:
      fragment_msg = "\n" + await itx.client.add_fragment(itx)
    quest_msg = await get_quest_rewards(itx, "income", True) 
    xp_msg = await itx.client.check_xp(itx.user.id, random.randint(1, 4))
    tip = "\n*Tip: Unlock new chocolate recipes to earn more money!*" #if unlocked_fragments and random.randint(1,3) == 1 else "" #33% chance of getting a suggestion (tip)

    tail = f"\nBalance: **{balance:,}{coin}** {xp_msg} {fragment_msg} {tip}"
    msg = f"You sold some **{item_sold}** and earned **{total}{coin}** \n" 
    msg += f"{amt_sold//5}x bags of Cocoa Beans - {amt_sold} {coin} \n"
    if unlocked_fragments:
      for sold in recipes_amt_sold:
        msg += f"{recipes_amt_sold[sold]}x {sold} {item_sold} - {recipes_amt_sold[sold]*prices[sold]} {coin} \n"
      
    msg += tail 
    
  else:
    cooldown_msg = get_counter(last_work, cooldown)
    msg = f"You cannot work so soon! \nCooldown: `{cooldown_msg}`" # cooldown based on level/patreon
    color = red

  msg += "\n" + quest_msg
  embed = discord.Embed(title = bot_name, description = msg, color = color)
  view = BackButton()
  await itx.response.send_message(embed=embed, view=view)

async def get_boosts(itx: discord.Interaction):
  msg = ""
  boosts = itx.client.db["economy"][str(itx.user.id)]["boosts"].copy()
  boosts["global"] = [itx.client.dbo["others"]["global_income_boost"]]
  # boosts = {"income": [{mult: duration}, {x: y}], "xp": [{x: y}]}
  for type_ in boosts:
    msg += f"\n**{type_.title()}: ** \n" # boosts[type_] = [{mult: duration}, {x: y}]
    if boosts[type_] in ([], [{}]):
      msg += f"You do not have any active boosts! \n"
    else:
      for boost in boosts[type_]: # boosts[type_][boost] = {mult: duration}
        msg += f"- **{list(boost.keys())[0]}x** boost ends in **{list(boost.values())[0]} hour(s)** \n"
    

  embed = discord.Embed(
    title = "Active Boosts",
    description = msg,
    color = blurple
  )
  await itx.response.send_message(embed=embed, view=BackButton())