import discord
from discord import ui
from vars import *
from itertools import chain, starmap
from discord.ext import commands, menus

class HelpPageSource(menus.ListPageSource):
    def __init__(self, data, helpcommand):
        super().__init__(data, per_page=6)
        self.helpcommand = helpcommand

    def format_command_help(self, no, command):
        signature = self.helpcommand.get_command_signature(command)
        docs = self.helpcommand.get_command_brief(command)
        return f"{no}. {signature}\n{docs}"
    
    async def format_page(self, menu, entries):
        page = menu.current_page
        max_page = self.get_max_pages()
        starting_number = page * self.per_page + 1
        iterator = starmap(self.format_command_help, enumerate(entries, start=starting_number))
        page_content = "\n".join(iterator)
        embed = discord.Embed(
            title=f"Help Command[{page + 1}/{max_page}]", 
            description=page_content,
            color=0xffcccb
        )
        author = menu.ctx.author
        embed.set_footer(text=f"Requested by {author}", icon_url=author.avatar)  # author.avatar in 2.0
        return embed

class MyMenuPages(ui.View, menus.MenuPages):
    def __init__(self, source, *, delete_message_after=False):
        super().__init__(timeout=60)
        self._source = source
        self.current_page = 0
        self.ctx = None
        self.message = None
        self.delete_message_after = delete_message_after

    async def start(self, ctx, *, channel=None, wait=False):
        # We wont be using wait/channel, you can implement them yourself. This is to match the MenuPages signature.
        await self._source._prepare_once()
        self.ctx = ctx
        self.message = await self.send_initial_message(ctx, ctx.channel)

    async def _get_kwargs_from_page(self, page):
        """This method calls ListPageSource.format_page class"""
        value = await super()._get_kwargs_from_page(page)
        if 'view' not in value:
            value.update({'view': self})
        return value

    async def interaction_check(self, interaction):
        """Only allow the author that invoke the command to be able to use the interaction"""
        return interaction.user == self.ctx.author

    @ui.button(emoji='<:before_fast_check:754948796139569224>', style=discord.ButtonStyle.blurple)
    async def first_page(self, interaction, button):
        await self.show_page(0)
        await interaction.response.defer()

    @ui.button(emoji='<:before_check:754948796487565332>', style=discord.ButtonStyle.blurple)
    async def before_page(self, interaction, button):
        await self.show_checked_page(self.current_page - 1)
        await interaction.response.defer()

    @ui.button(emoji='<:stop_check:754948796365930517>', style=discord.ButtonStyle.blurple)
    async def stop_page(self, interaction, button):
        self.stop()
        if self.delete_message_after:
            await self.message.edit(view = None)

    @ui.button(emoji='<:next_check:754948796361736213>', style=discord.ButtonStyle.blurple)
    async def next_page(self, interaction, button):
        await self.show_checked_page(self.current_page + 1)
        await interaction.response.defer()

    @ui.button(emoji='<:next_fast_check:754948796391227442>', style=discord.ButtonStyle.blurple)
    async def last_page(self, interaction, button):
        await self.show_page(self._source.get_max_pages() - 1)
        await interaction.response.defer()

class MyHelp(commands.HelpCommand):
  def get_command_brief(self, command):
    return command.short_doc or "Command is not documented."
  
  async def send_bot_help(self, mapping):
    all_commands = await self.filter_commands(list(chain.from_iterable(mapping.values()))) # .filter_commands() ??
    formatter = HelpPageSource(all_commands, self)
    menu = MyMenuPages(formatter, delete_message_after=True)
    await menu.start(self.context)

  async def send_cog_help(self, mapping):
    all_commands = list(chain.from_iterable(mapping.values()))
    formatter = HelpPageSource(all_commands, self)
    menu = MyMenuPages(formatter, delete_message_after=True)
    await menu.start(self.context)

  async def send_command_help(self, command):
    embed = discord.Embed(title="Help", color = discord.Color.blurple())
    embed.add_field(name=self.get_command_signature(command), value=command.help)
    alias = command.aliases
    if alias:
        embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

    channel = self.get_destination()
    await channel.send(embed=embed)

  async def command_not_found(self, command):
    embed = discord.Embed(title = "Help", description = f"The command `{command}` does not exist. Use `{self.context.bot.prefix}help` to view all bot commands!", color = red)
    channel = self.get_destination()
    await channel.send(embed = embed)

  async def send_group_help(self, command):
    all_commands = [x for x in command.walk_commands()] # .filter_commands() ??
    formatter = HelpPageSource(all_commands, self)
    menu = MyMenuPages(formatter, delete_message_after=True)
    await menu.start(self.context)

"""class Help_cmd(commands.HelpCommand):
  async def send_bot_help(self, mapping):
    embed = discord.Embed(title="Help")
    for cog, commands in mapping.items():
       command_signatures = [self.get_command_signature(c) for c in commands]
       if command_signatures:
            cog_name = getattr(cog, "qualified_name", "No Category")
            embed.add_field(name=cog_name, value="\n".join(command_signatures), inline=False)

    channel = self.get_destination()
    await channel.send(embed=embed)
    
  async def send_command_help(self, command):
    embed = discord.Embed(title=self.get_command_signature(command))
    embed.add_field(name="Help", value=command.help)
    alias = command.aliases
    if alias:
        embed.add_field(name="Aliases", value=", ".join(alias), inline=False)

    channel = self.get_destination()
    await channel.send(embed=embed)"""

"""  async def send_error_message(self, error):
    embed = discord.Embed(title="Error", description=error)
    channel = self.get_destination()
    await channel.send(embed=embed)"""

class Help(commands.Cog):
  def __init__(self, bot):
    self._original_help_command = bot.help_command
    attrs = {
      "name" : "help",
      "help" : "Shows a help page!",
      'cooldown': commands.CooldownMapping.from_cooldown(3, 8, commands.BucketType.user),
      "verify_checks" : False
    }
    bot.help_command = MyHelp(command_attrs = attrs)
    bot.help_command.cog = self

  def cog_unload(self):
    self.help_command = self._original_help_command
  
async def setup(bot):
  await bot.add_cog(Help(bot))