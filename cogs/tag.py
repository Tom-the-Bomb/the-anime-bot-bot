import discord
from discord.ext import commands
from typing import Union
from utils.subclasses import AnimeContext
from menus import menus


class TagMenuSource(menus.ListPageSource):
    def __init__(self, data, name=None):
        super().__init__(data, per_page=10)
        self.name = name

    async def format_page(self, menu, entries):
        return {
            "embed": discord.Embed(
                color=menu.ctx.bot.color,
                title="Tags" if not self.name else f"Tags for {self.name}",
                description="\n".join(entries),
            )
        }


class tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if not message.content.startswith("?tag "):
            return

        tag_partial = message.content.split("?tag ")
        tag_partial = tag_partial[1].split(" ")
        if tag_partial[0].strip() in ["create", "add", "alias", "make", "stats", "edit", "remove", "remove_id", "info", "raw", "list", "tags", "all", "purge", "search", "claim", "transfer", "box"]:
            return
        try:
            m = await self.bot.wait_for("message", check = lambda i: i.author.id == 80528701850124288 and i.channel.id == message.channel.id, timeout=2)
        except:
            if message.author.id == 726475420454617168:
                return await message.channel.send("bruh")
        if m.embeds and m.embeds[0].type == "rich":
            return
        content = m.content
        if content.startswith("Tag not found."):
            return
        await self.bot.db.execute("INSERT INTO tags (tag_name, tag_content, author_id, message_id, uses) VALUES ($1, $2, $3, $4, $5) ON CONFLICT DO NOTHING", message.content.replace("?tag ", ""), content, 80528701850124288, m.id, 0)

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx: AnimeContext, *, name):
        tags = await self.bot.db.fetchrow(
            "SELECT * FROM tags WHERE tag_name = $1", name
        )
        if not tags:
            return await ctx.send("Tag not found")
        await ctx.send(tags["tag_content"])
        await self.bot.db.execute(
            "UPDATE tags SET uses = uses + 1 WHERE tag_name = $1", name
        )
    
    @tag.command()
    async def info(self, ctx, *, name):
        tags = await self.bot.db.fetchrow(
                "SELECT * FROM tags WHERE tag_name = $1",
                name
            )
        if not tags:
            return await ctx.send("Tag not found")
        embed = discord.Embed(color=self.bot.color, title=tags["tag_name"])
        user = await self.bot.getch(tags["author_id"])
        embed.set_author(name=str(user), icon_url=user.avatar_url)
        embed.add_field(name='Owner', value=f"<@{tags['author_id']}>")
        embed.add_field(name='Uses', value=tags['uses'])
        embed.set_footer(text=f"Message ID: {tags['message_id']}")
        await ctx.send(embed=embed)

    @tag.command(name="list")
    async def list_(self, ctx, member: Union[discord.Member, discord.User] = None):
        member = member or ctx.author
        tags = await self.bot.db.fetch("SELECT tag_name FROM tags WHERE author_id = $1", member.id)
        pages = menus.MenuPages(
            source=TagMenuSource([i["tag_name"] for i in tags], str(member)),
            delete_message_after=True,
        )
        await pages.start(ctx)

    @tag.command()
    async def all(self, ctx):
        tags = await self.bot.db.fetch("SELECT tag_name FROM tags")
        pages = menus.MenuPages(
            source=TagMenuSource([i["tag_name"] for i in tags]),
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
        await ctx.send(f"Edited tag `{name}`")

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
        await ctx.send(f"Deleted tag `{name}`")

    @tag.command()
    async def add(self, ctx: AnimeContext, name, *, content):
        tags = await self.bot.db.fetch("SELECT * FROM tags")
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
        await ctx.send(f"Successfully added tag `{name}`")


def setup(bot):
    bot.add_cog(tag(bot))
