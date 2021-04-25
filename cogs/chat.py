import discord
from discord.ext import commands
from utils.subclasses import AnimeContext
from io import BytesIO
from wordcloud import WordCloud
from matplotlib import pyplot as plt
from utils.asyncstuff import asyncexe
from collections import Counter


class chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @asyncexe()
    def wordcloud_(self, text):
        wordcloud = WordCloud().generate(text)
        image = wordcloud.to_image()
        b = BytesIO()
        image.save(b, "PNG")
        b.seek(0)
        return b
        
    @commands.command()
    async def wordcloud(self, ctx, limit: int=1000):
        limit = min(limit, 10000)
        text = ""
        async for message in ctx.channel.history(limit=limit):
            if message.content:
                text += message.content
        pic = await self.wordcloud_(text)
        await ctx.send(file=discord.File(pic, "wordcloud.png"))

    @staticmethod
    @asyncexe()
    def graph_(msg):
        author = []
        count = []
        for i, (n, v) in enumerate(msg.most_common()):
            author.append(n)
            count.append(v)
        plt.figure(figsize=(10, 7), facecolor="black")
        patches, texts = plt.pie(count, labels=author)
        plt.legend(loc="best", title="User names")
        plt.axis("equal")
        plt.tight_layout()
        plt.savefig("chatgraph.png")
        return

    @commands.command()
    async def chatgraph(self, ctx: AnimeContext, *, limit: int = 500):
        limit = min(limit, 10000)
        await ctx.send("Collecting might take long")
        msg: Counter = Counter()
        counter = 0
        async for message in ctx.channel.history(limit=limit):
            counter += 1
            if message.author.bot:
                continue
            msg[message.author.name] += 1
        await self.graph_(msg)
        await ctx.send(file=discord.File("chatgraph.png"))


def setup(bot):
    bot.add_cog(chat(bot))
