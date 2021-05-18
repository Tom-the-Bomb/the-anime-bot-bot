import discord
from discord.ext import commands
from io import BytesIO
import ujson
import re
import asyncpg
from typing import Union
from utils.subclasses import AnimeContext
from menus import menus


class TagMenuSource(menus.ListPageSource):
    def __init__(self, data, name=None):
        super().__init__(data, per_page=10)
        self.name = name
        self.data = data

    async def format_page(self, menu, entries):
        return {
            "embed": discord.Embed(
                color=menu.ctx.bot.color,
                title="Tags" if not self.name else f"Tags for {self.name}",
                description="\n".join(entries),
            ).set_footer(text=f"Page {menu.current_page + 1}/{self.get_max_pages()} Total Entries: {len(self.data)}")
        }


class tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.random_tag_regex = re.compile(r"Random tag found: (?P<tag_name>.+)\n(?P<tag_content>(.|\n)+)")

    @commands.Cog.listener("on_message")
    async def on_message_for_random_tag_(self, message):
        if not message.content.startswith("!random tag"):
            return
        m = await self.bot.wait_for(
            "message",
            check=lambda i: i.author.id == 80528701850124288 and i.channel.id == message.channel.id,
            timeout=1,
        )
        if m.embeds and m.embeds[0].type == "rich":
            return
        content = m.content
        matches = self.random_tag_regex.findall(content)
        if matches:
            tag_name = matches[0][0]
            tag_content = matches[0][1]
            try:
                await self.bot.db.execute(
                    "INSERT INTO tags (tag_name, tag_content, author_id, message_id, uses) VALUES ($1, $2, $3, $4, $5)",
                    tag_name,
                    tag_content,
                    80528701850124288,
                    m.id,
                    0,
                )
            except asyncpg.exceptions.UniqueViolationError:
                tags = await self.bot.db.fetchrow("SELECT author_id FROM tags WHERE tag_name = $1", tag_name)
                if tags["author_id"] == 80528701850124288:
                    await self.bot.db.execute(
                        "UPDATE tags SET tag_content = $1 WHERE tag_name = $2",
                        tag_content,
                        tag_name,
                    )

    @commands.Cog.listener("on_message")
    async def on_message_for_random_tag(self, message):
        if not message.content.startswith("?random tag"):
            return
        m = await self.bot.wait_for(
            "message",
            check=lambda i: i.author.id == 80528701850124288 and i.channel.id == message.channel.id,
            timeout=1,
        )
        if m.embeds and m.embeds[0].type == "rich":
            return
        content = m.content
        matches = self.random_tag_regex.findall(content)
        if matches:
            tag_name = matches[0][0]
            tag_content = matches[0][1]
            try:
                await self.bot.db.execute(
                    "INSERT INTO tags (tag_name, tag_content, author_id, message_id, uses) VALUES ($1, $2, $3, $4, $5)",
                    tag_name,
                    tag_content,
                    80528701850124288,
                    m.id,
                    0,
                )
            except asyncpg.exceptions.UniqueViolationError:
                tags = await self.bot.db.fetchrow("SELECT author_id FROM tags WHERE tag_name = $1", tag_name)
                if tags["author_id"] == 80528701850124288:
                    await self.bot.db.execute(
                        "UPDATE tags SET tag_content = $1 WHERE tag_name = $2",
                        tag_content,
                        tag_name,
                    )

    @commands.Cog.listener("on_message")
    async def on_message_for_normal_tag_weird_prefix(self, message):
        if not message.content.startswith("!tag "):
            return

        tag_name = message.content[5:]
        tag_partial = tag_name.split()
        if tag_partial[0].strip() in [
            "create",
            "add",
            "alias",
            "make",
            "stats",
            "edit",
            "remove",
            "remove_id",
            "info",
            "raw",
            "list",
            "tags",
            "all",
            "purge",
            "search",
            "claim",
            "transfer",
            "box",
        ]:
            return
        m = await self.bot.wait_for(
            "message",
            check=lambda i: i.author.id == 80528701850124288 and i.channel.id == message.channel.id,
            timeout=2,
        )
        if m.embeds and m.embeds[0].type == "rich":
            return
        content = m.content
        if content.startswith("Tag not found."):
            return
        try:
            await self.bot.db.execute(
                "INSERT INTO tags (tag_name, tag_content, author_id, message_id, uses) VALUES ($1, $2, $3, $4, $5)",
                tag_name,
                content,
                80528701850124288,
                m.id,
                0,
            )
        except asyncpg.exceptions.UniqueViolationError:
            tags = await self.bot.db.fetchrow("SELECT author_id FROM tags WHERE tag_name = $1", tag_name)
            if tags["author_id"] == 80528701850124288:
                await self.bot.db.execute(
                    "UPDATE tags SET tag_content = $1 WHERE tag_name = $2",
                    content,
                    tag_name,
                )

    @commands.Cog.listener("on_message")
    async def on_message_for_normal_tag(self, message):
        if not message.content.startswith("?tag "):
            return

        tag_name = message.content[5:]
        tag_partial = tag_name.split()
        if tag_partial[0].strip() in [
            "create",
            "add",
            "alias",
            "make",
            "stats",
            "edit",
            "remove",
            "remove_id",
            "info",
            "raw",
            "list",
            "tags",
            "all",
            "purge",
            "search",
            "claim",
            "transfer",
            "box",
        ]:
            return
        m = await self.bot.wait_for(
            "message",
            check=lambda i: i.author.id == 80528701850124288 and i.channel.id == message.channel.id,
            timeout=2,
        )
        if m.embeds and m.embeds[0].type == "rich":
            return
        content = m.content
        if content.startswith("Tag not found."):
            return
        try:
            await self.bot.db.execute(
                "INSERT INTO tags (tag_name, tag_content, author_id, message_id, uses) VALUES ($1, $2, $3, $4, $5)",
                tag_name,
                content,
                80528701850124288,
                m.id,
                0,
            )
        except asyncpg.exceptions.UniqueViolationError:
            tags = await self.bot.db.fetchrow("SELECT author_id FROM tags WHERE tag_name = $1", tag_name)
            if tags["author_id"] == 80528701850124288:
                await self.bot.db.execute(
                    "UPDATE tags SET tag_content = $1 WHERE tag_name = $2",
                    content,
                    tag_name,
                )

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: AnimeContext, *, name):
        tags = await self.bot.db.fetchrow("SELECT * FROM tags WHERE tag_name = $1", name)
        if not tags:
            tags = await self.bot.db.fetch(
                "SELECT tag_name FROM tags WHERE tag_name % $1 ORDER BY similarity(tag_name, $1) DESC LIMIT 3",
                name,
            )
            if tags:
                tags = "\n".join(i["tag_name"] for i in tags)
                return await ctx.send(f"Tag not found\nDid you mean:\n{tags}")
            return await ctx.send(f"Tag not found")

        await ctx.send(tags["tag_content"])
        await self.bot.db.execute("UPDATE tags SET uses = uses + 1 WHERE tag_name = $1", name)
    
    @tag.command()
    async def export(self, ctx):
        tags = await self.bot.db.fetch(
            "SELECT * FROM tags"
        )
        json = {i["tag_name"]: {
                "tag_content": i["tag_content"],
                "author_id": i["author_id"],
                "message_id": i["message_id"],
                "uses": i["uses"],
                "aliases": i["aliases"],
            } for i in tags}
        await ctx.send(file=discord.File(BytesIO(ujson.dumps(json, escape_forward_slashes=False, indent=4).encode("utf-8")), "The_Anime_Bot_tags_export.json"))

    @tag.command()
    async def transfer(self, ctx: AnimeContext, name, member: discord.Member):
        tags = await self.bot.db.fetch(
            "SELECT * FROM tags WHERE tag_name = $1 AND author_id = $2",
            name,
            ctx.author.id,
        )
        if not tags:
            return await ctx.send("Tag not found or you don't own the tag")
        await self.bot.db.execute("UPDATE tags SET author_id = $2 WHERE tag_name = $1", name, member.id)
        await ctx.send(f"Successfully transferred tag `{discord.utils.escape_markdown(name)}` to {member.mention}")

    @tag.command()
    async def search(self, ctx, *, name):
        tags = await self.bot.db.fetch(
            "SELECT tag_name FROM tags WHERE tag_name % $1 ORDER BY similarity(tag_name, $1) DESC",
            name,
        )
        pages = menus.MenuPages(
            source=TagMenuSource(
                [discord.utils.escape_markdown(i["tag_name"]) for i in tags],
            ),
            delete_message_after=True,
        )
        await pages.start(ctx)

    @tag.command()
    async def forceclaim(self, ctx, *, name):
        if ctx.author.id != 590323594744168494:
            return await ctx.send("no")
        tags = await self.bot.db.fetchrow("SELECT * FROM tags WHERE tag_name = $1", name)
        if not tags:
            return await ctx.send("Tag not found")
        await self.bot.db.execute(
            "UPDATE tags SET author_id = $2 WHERE tag_name = $1",
            name,
            ctx.author.id,
        )
        await ctx.send(f"Force claimed tag `{discord.utils.escape_markdown(name)}`")

    @tag.command()
    async def info(self, ctx, *, name):
        tags = await self.bot.db.fetchrow("SELECT * FROM tags WHERE tag_name = $1", name)
        if not tags:
            return await ctx.send("Tag not found")
        embed = discord.Embed(color=self.bot.color, title=tags["tag_name"])
        user = await self.bot.getch(tags["author_id"])
        embed.set_author(name=str(user), icon_url=user.avatar_url)
        embed.add_field(name="Owner", value=f"<@{tags['author_id']}>")
        embed.add_field(name="Uses", value=tags["uses"])
        embed.set_footer(text=f"Message ID: {tags['message_id']}")
        await ctx.send(embed=embed)

    @tag.command(name="list")
    async def list_(self, ctx, member: Union[discord.Member, discord.User] = None):
        member = member or ctx.author
        tags = await self.bot.db.fetch(
            "SELECT tag_name FROM tags WHERE author_id = $1 ORDER BY tag_name",
            member.id,
        )
        pages = menus.MenuPages(
            source=TagMenuSource(
                [discord.utils.escape_markdown(i["tag_name"]) for i in tags],
                str(member),
            ),
            delete_message_after=True,
        )
        await pages.start(ctx)

    @tag.command()
    async def all(self, ctx):
        tags = await self.bot.db.fetch("SELECT tag_name FROM tags ORDER BY tag_name")
        pages = menus.MenuPages(
            source=TagMenuSource([discord.utils.escape_markdown(i["tag_name"]) for i in tags]),
            delete_message_after=True,
        )
        await pages.start(ctx)

    @tag.command()
    async def edit(self, ctx: AnimeContext, name, *, content):
        tags = await self.bot.db.fetch(
            "SELECT * FROM tags WHERE tag_name = $1 AND author_id = $2",
            name,
            ctx.author.id,
        )
        if not tags:
            return await ctx.send("Tag not found or you don't own the tag")
        await self.bot.db.execute(
            "UPDATE tags SET tag_content = $2 WHERE tag_name = $1",
            name,
            content,
        )
        await ctx.send(f"Edited tag `{discord.utils.escape_markdown(name)}`")

    @tag.command()
    async def remove(self, ctx: AnimeContext, *, name):
        tags = await self.bot.db.fetch(
            "SELECT * FROM tags WHERE tag_name = $1 AND author_id = $2",
            name,
            ctx.author.id,
        )
        if not tags:
            return await ctx.send("Tag not found or you don't own the tag")
        await self.bot.db.execute("DELETE FROM tags WHERE tag_name = $1", name)
        await ctx.send(f"Deleted tag `{discord.utils.escape_markdown(name)}`")

    @tag.command()
    async def make(self, ctx):
        await ctx.send("oh hi what the tag name is?")

        def check(msg):
            return msg.author == ctx.author and ctx.channel == msg.channel

        try:
            name = await self.bot.wait_for("message", timeout=60, check=check)
            name = name.content
        except asyncio.TimeoutError:
            return await ctx.send("smh u took too long run the command again if u want to remake")
        await ctx.send(f"ok {name} it will be what about content?")
        try:
            content = await self.bot.wait_for("message", timeout=60, check=check)
            content = content.content
        except asyncio.TimeoutError:
            return await ctx.send("smh u took too long run the command again if u want to remake")
        await ctx.invoke(self.add, name=name, content=content)

    @tag.command(aliases=["create"])
    async def add(self, ctx: AnimeContext, name, *, content):
        tags = await self.bot.db.fetch("SELECT * FROM tags")
        if len(name) > 200:
            return await ctx.send("no tag name too long")
        for i in tags:
            if name == i["tag_name"]:
                return await ctx.send("This tag already exist")
        await self.bot.db.execute(
            "INSERT INTO tags (tag_name, tag_content, author_id, message_id, uses) VALUES ($1, $2, $3, $4, $5)",
            name,
            content,
            ctx.author.id,
            ctx.message.id,
            0,
        )
        await ctx.send(f"Successfully added tag `{discord.utils.escape_markdown(name)}`")


def setup(bot):
    bot.add_cog(tag(bot))
