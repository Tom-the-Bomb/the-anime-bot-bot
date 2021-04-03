from collections import Counter

import discord
from discord.ext import commands
from utils.subclasses import AnimeContext

from menus import menus

from jishaku.paginators import PaginatorInterface, PaginatorEmbedInterface

class CommandsUsageMenu(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=10)
    async def format_page(self, menu, entries):
        return {"embed": discord.Embed(color=menu.ctx.bot.color, title=f"Command Usage", description="\n".join(entries))}

class commandsusage(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_command_completion(self, ctx: AnimeContext):
        self.bot.command_counter += 1
        self.bot.commandsusages[ctx.command.qualified_name] += 1
        await self.bot.db.execute("INSERT INTO commandsusage VALUES ($1, $2) ON CONFLICT (command) DO UPDATE SET usages = commandsusage.usages + 1", ctx: AnimeContext.command.qualified_name, 1)
    @commands.command()
    async def commandusage(self, ctx: AnimeContext):
        counter = 0
        lists = [f"Total {self.bot.command_counter} commands invoked"]
        for i, (n, v) in enumerate(self.bot.commandsusages.most_common()):
            counter += 1
            lists.append(f"`{counter}. {n:<20} {v}`")
        pages = menus.MenuPages(source=CommandsUsageMenu(lists), delete_message_after=True)
        await pages.start(ctx)

def setup(bot):
    bot.add_cog(commandsusage(bot))
