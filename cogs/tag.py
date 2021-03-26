import discord
from discord.ext import commands

class tag(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
       
#     @commands.Cog.listener()
#     async def on_message(self, message):
#         if message.content.startswith("?tag "):
#             tag_partial = message.content.split("?tag ")
#             if len(tag_partial) >= 3:
#                 return
#             m = await self.bot.wait_for("message", check = lambda i: i.author.id == 80528701850124288 and i.channel.id == message.channel.id, timeout=2)
#             content = m.content
#             await self.bot.db.execute("INSERT INTO tags (tag_name, tag_content, author_id, message_id, uses) VALUES ($1, $2, $3, $4, $5)", message.content.replace("?tag ", ""), content, 80528701850124288, m.id, 0)
            

    @commands.group(invoke_without_command=True)
    async def tag(self, ctx, *, name):
        tags = await self.bot.db.fetchrow("SELECT * FROM tags WHERE tag_name = $1", name)
        if not tags:
            return await ctx.send("Tag not found")
        await ctx.send(tags["tag_content"])
        await self.bot.db.execute("UPDATE tags SET uses = uses + 1 WHERE tag_name = $1", name)

    @tag.command()
    async def edit(self, ctx, name, *, content):
        tags = await self.bot.db.fetch("SELECT * FROM tags WHERE tag_name = $1 AND author_id = $2", name, ctx.author.id)
        if not tags:
            return await ctx.send("Tag not found or you don't own the tag")
        await self.bot.db.execute("UPDATE tags SET tag_content = $2 WHERE tag_name = $1", name, content)
        await ctx.send(f"Edited tag `{name}`")
    @tag.command()
    async def remove(self, ctx, *, name):
        tags = await self.bot.db.fetch("SELECT * FROM tags WHERE tag_name = $1 AND author_id = $2", name, ctx.author.id)
        if not tags:
            return await ctx.send("Tag not found or you don't own the tag")
        await self.bot.db.execute("DELETE FROM tags WHERE tag_name = $1", name)
        await ctx.send(f"Deleted tag `{name}`")
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
