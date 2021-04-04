import discord
from discord.ext import commands
from utils.subclasses import AnimeContext
import copy
import datetime


class reactionrole(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.unnie_message_id = 826236025789349918
        self.unnie_emoji_to_role = {
            727995475117998111: 810336158008737792,
            796132269312049152: 826201074817957919,
            798756695949705257: 812094102673817640,
            777815702437494784: 810375644121923584,
            658386618205470780: 810337057544077363,
            665825427197001743: 810337124271783956,
            741017487994519633: 810337691282571304,
            515993072031498260: 812476108900663306,
            588504238494187525: 826204966749863978,
            810349419802132481: 826207728322084915,
        }
        self.pig_role_message_id = 812050921714089996
        self.pig_emoji_to_role = {
            701518910842732640: 701546882320826428,
            711089394031001600: 701543891119243324,
            658157341816127498: 701906891848024124,
            800088795281227828: 810336158008737792,
            "\U0001f9a2": 812052162782691338,
            800088141955858463: 812054058651091016,
            800088641267433493: 812054326871719976,
            800088680009957387: 812054426831290440,
            "\U0001f33f": 812058367739691028,
            800088726923116574: 812054545035165706,
            "\U0001f38d": 812058367098748929,
            690260332911919140: 812058368503840819,
            "\U0001fad0": 812058362028097606,
            798949801630236702: 812057014888955935,
            699503385824722964: 812058366360027146,
            798949802322427955: 812057852550185041,
            694419633150885909: 812058369279787018,
            800088895722225685: 812058369807876166,
            691499259438170152: 811804360107360267,
        }

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gives a role based on a reaction emoji."""
        # Make sure that the message the user is reacting to is the one we care about
        if payload.message_id != self.pig_role_message_id:
            return

        try:
            role_id = self.pig_emoji_to_role[
                payload.emoji.id or payload.emoji.name
            ]
        except KeyError:
            # If the emoji isn't the one we care about then exit as well.
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            # Check if we're still in the guild and it's cached.
            return

        role = guild.get_role(role_id)
        if role is None:
            # Make sure the role still exists and is valid.
            return

        try:
            # Finally add the role
            await payload.member.add_roles(role)
        except discord.HTTPException:
            # If we want to do something in case of errors we'd do it here.
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Removes a role based on a reaction emoji."""
        # Make sure that the message the user is reacting to is the one we care about
        if payload.message_id != self.pig_role_message_id:
            return

        try:
            role_id = self.pig_emoji_to_role[
                payload.emoji.id or payload.emoji.name
            ]
        except KeyError:
            # If the emoji isn't the one we care about then exit as well.
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            # Check if we're still in the guild and it's cached.
            return

        role = guild.get_role(role_id)
        if role is None:
            # Make sure the role still exists and is valid.
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            # Makes sure the member still exists and is valid
            return

        try:
            # Finally, remove the role
            await member.remove_roles(role)
        except discord.HTTPException:
            # If we want to do something in case of errors we'd do it here.
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        """Gives a role based on a reaction emoji."""
        # Make sure that the message the user is reacting to is the one we care about
        if payload.message_id != self.unnie_message_id:
            return

        try:
            role_id = self.unnie_emoji_to_role[
                payload.emoji.id or payload.emoji.name
            ]
        except KeyError:
            # If the emoji isn't the one we care about then exit as well.
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            # Check if we're still in the guild and it's cached.
            return

        role = guild.get_role(role_id)
        if role is None:
            # Make sure the role still exists and is valid.
            return

        try:
            # Finally add the role
            await payload.member.add_roles(role)
        except discord.HTTPException:
            # If we want to do something in case of errors we'd do it here.
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        """Removes a role based on a reaction emoji."""
        # Make sure that the message the user is reacting to is the one we care about
        if payload.message_id != self.unnie_message_id:
            return

        try:
            role_id = self.unnie_emoji_to_role[
                payload.emoji.id or payload.emoji.name
            ]
        except KeyError:
            # If the emoji isn't the one we care about then exit as well.
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            # Check if we're still in the guild and it's cached.
            return

        role = guild.get_role(role_id)
        if role is None:
            # Make sure the role still exists and is valid.
            return

        member = guild.get_member(payload.user_id)
        if member is None:
            # Makes sure the member still exists and is valid
            return

        try:
            # Finally, remove the role
            await member.remove_roles(role)
        except discord.HTTPException:
            # If we want to do something in case of errors we'd do it here.
            pass


def setup(bot):
    bot.add_cog(reactionrole(bot))
