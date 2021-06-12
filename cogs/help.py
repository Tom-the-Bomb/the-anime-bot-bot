import difflib
import random

import discord
from discord.ext import commands, menus
from utils.subclasses import AnimeContext

from jishaku.models import copy_context_with
from jishaku.paginators import PaginatorEmbedInterface


class HelpMenuSource(menus.ListPageSource):
    def __init__(self, data):
        self.data = data
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):
        return {
            "embed": discord.Embed(
                color=menu.ctx.bot.color,
                title="Help command",
                description="\n".join(entries),
            )
            .set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()} Total Entries: {len(self.data)}")
            .set_author(name=menu.ctx.author.name, icon_url=str(menu.ctx.author.avatar_url_as(static_format="png")))
        }


class HelpCommand(commands.HelpCommand):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    async def command_callback(self, ctx, *, command=None):
        await self.prepare_help_command(ctx, command)
        bot = ctx.bot

        if command is None:
            mapping = self.get_bot_mapping()
            return await self.send_bot_help(mapping)

        # Check if it's a cog
        for cog in bot.cogs.keys():
            if cog.lower() == command.lower():
                return await self.send_cog_help(bot.get_cog(cog))

        maybe_coro = discord.utils.maybe_coroutine

        # If it's not a cog then it's a command.
        # Since we want to have detailed errors when someone
        # passes an invalid subcommand, we need to walk through
        # the command group chain ourselves.
        keys = command.split(" ")
        cmd = bot.all_commands.get(keys[0])
        if cmd is None:
            string = await maybe_coro(self.command_not_found, self.remove_mentions(keys[0]))
            return await self.send_error_message(string)

        for key in keys[1:]:
            try:
                found = cmd.all_commands.get(key)
            except AttributeError:
                string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                return await self.send_error_message(string)
            else:
                if found is None:
                    string = await maybe_coro(self.subcommand_not_found, cmd, self.remove_mentions(key))
                    return await self.send_error_message(string)
                cmd = found

        if isinstance(cmd, commands.Group):
            return await self.send_group_help(cmd)
        else:
            return await self.send_command_help(cmd)

    def get_command_signature(self, command):
        return f"{self.clean_prefix}{command.qualified_name}{'|' if command.aliases else ''}{'|'.join(command.aliases)} {command.signature}"

    async def send_group_help(self, group):
        lists = [self.get_command_signature(i) for i in await self.filter_commands(group.walk_commands())]
        pages = menus.MenuPages(source=HelpMenuSource(lists), delete_message_after=True)
        await pages.start(self.context)

    async def send_command_help(self, command):
        no_help_responses = [
            "Is a mystery",
            "idk",
            "<:rooThink:596576798351949847>",
            "hmm now this is hm",
            "cool no help idk what to do now",
            "uhh good question idk <:rooPog:829501231000584272>",
            "i is wonder",
            "why no help",
            "owner lazy u no can blame me",
            "yes we need some help on this help command",
            "hmm",
            "amongus be like",
            "this so sus",
            "oh wow no help",
            "smh no help",
            "ok blame on dyno",
            "ok blame on MEE6",
            "ok idk what to blame",
            "hmm idk",
        ]
        embed = discord.Embed(
            color=self.context.bot.color,
            title=self.get_command_signature(command),
            description=command.help or random.choice(no_help_responses),
        )
        embed.add_field(name="Category", value=command.cog_name)
        try:
            can_run = await command.can_run(self.context)
        except commands.CommandError:
            can_run = False
        embed.add_field(name="Runnable by you", value=can_run)
        usage = await self.context.bot.db.fetchval(
            "SELECT usages FROM commandsusage WHERE command = $1", command.qualified_name
        )
        embed.add_field(name="Usage", value=usage or "0")

        await self.context.send(embed=embed)

    async def send_cog_help(self, cog):
        commands_ = await self.filter_commands(cog.get_commands())
        lists_ = []
        for i in commands_:
            if isinstance(i, commands.Group):
                for v in await self.filter_commands(i.walk_commands()):
                    lists_.append(self.get_command_signature(v))
                lists_.insert(0, self.get_command_signature(i))
            else:
                lists_.append(self.get_command_signature(i))
        lists = [f"**{i}**" for i in lists_]
        pages = menus.MenuPages(source=HelpMenuSource(lists), delete_message_after=True)
        await pages.start(self.context)

    async def send_bot_help(self, mapping):
        cogs = "\n".join(self.context.bot.cogs.keys())

        embed = discord.Embed(
            color=self.context.bot.color,
            description=f"""
        Hi Welcome to The Anime bot's help command
        You can use the following commands

        **{self.context.prefix}help [command]**

        **{self.context.prefix}help [module]**

        **Available Modules are:**

<:rooAww:747680003021471825> Fun
<:rooBless:597589960270544916> Utility
<:rooCop:596577110982918146> Moderations
<:rooPog:829501231000584272> Chat
<:rooThink:596576798351949847> Music
<:rooPopcorn:744346001304977488> Others
<a:rooLove:744346239075877518> Anime
<a:rooCool:747680120763973654> Todo
<a:rooClap:759933903959228446> Tag
<:roodab:805915304190279691> CommandsUsage
<:rooDuck:739614767941156874> ReactionRole
<:rooEZ:596577109695266837> Reminder
<:rooEZSip:596577108675788800> UserHistory
<:rooFat:744345098531242125> Pictures
<a:rooFight:747679958440345621> Logging
<a:rooHacker:744349119061032970> Socket
        """,
        )
        embed.set_thumbnail(url=str(self.context.me.avatar_url_as(format="png")))
        await self.context.send(embed=embed)
        # is_working = True
        # dicts = {
        #     739614767941156874: "animes",
        #     747680003021471825: "fun",
        #     596577110982918146: "moderations",
        #     747680120763973654: "Music",
        #     759933903959228446: "others",
        #     597589960270544916: "pictures",
        #     744346239075877518: "utility"
        # }
        # embed = discord.Embed(color=self.context.bot.color,
        #                       description="**Hi welcome to The Anime Bot's help menu**\n```diff\nBefore we start something you need to know about\n <argument> means that argument is require\n[requirment] mean that argument is optional\n```")
        # embed.add_field(name="Categorys", value="**Animes:** <:rooDuck:739614767941156874>\n**Fun:** <:rooAww:747680003021471825>\n**Moderations:** <:rooCop:596577110982918146>\n**Music:** <a:rooCool:747680120763973654>\n**Others:** <a:rooClap:759933903959228446>\n**Pictures:** <:rooBless:597589960270544916>\n**Utility:** <a:rooLove:744346239075877518>")
        # channel = self.get_destination()
        # message = await channel.send(embed=embed)
        # for i in dicts.keys():
        #     await message.add_reaction(self.context.bot.get_emoji(i))
        # def check(payload):
        #     return payload.message_id == message.id and payload.author_id == self.context.author.id and payload.emoji.id in dicts.keys()
        # payload = await self.context.bot.wait_for("raw_reaction_add", check=check)
        # await self.context.bot.invoke(copy_context_with(self.context, content="ovo help " + dicts.get(payload.emoji.id)))
        # await message.delete()

    async def command_not_found(self, string: str):
        matches = difflib.get_close_matches(string, self.context.bot.all_commands.keys())
        if not matches:
            return f"Command {string!r} is not found."
        commands_found = "\n".join(matches[:3])
        return f"command {string!r} is not found. Did you mean:\n{commands_found}"


class Help(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        bot.help_command = HelpCommand(show_hidden=False, verify_checks=False)


def setup(bot):
    bot.add_cog(help(bot))
