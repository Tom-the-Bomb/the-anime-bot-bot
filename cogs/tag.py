import discord
from discord.ext import commands

class tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx, *, name):
        tags = await self.bot.db.fetchrow("SELECT * FROM tags WHERE tag_name = $1", name)
        if not tags:
            return await ctx.send("Tag not found")
        await ctx.send(tags["tag_content"])
        await self.bot.db.execute("UPDATE tags SET uses = uses + 1 WHERE tag_name = $1", name)
        
    @tag.command()
    async def remove(self, ctx, *, name):
        tags = await self.bot.db.fetch("SELECT * FROM tags WHERE tag_name = $1", name)
        if not tags:
            return await ctx.send("Tag not found")
        await self.bot.db.execute("DELETE FROM tags WHERE tag_name = $1", name)
        await ctx.send(f"Deleted tag {name}")
    @tag.command()
    async def add(self, ctx, name, *, content):
        tags = await self.bot.db.fetch("SELECT * FROM tags")
        for i in tags:
            if name == i["tag_name"]:
                return await ctx.send("This tag already exist")
        await self.bot.db.execute("INSERT INTO tags (tag_name, tag_content, author_id, message_id, uses) VALUES ($1, $2, $3, $4, $5)", name, content, ctx.author.id, ctx.message.id, 0)
        await ctx.send(f"Successfully added tag `{name}`")





def setup(bot):
    bot.add_cog(tag(bot))
