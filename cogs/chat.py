import discord
from discord.ext import commands
from utils.subclasses import AnimeContext
import random
from io import BytesIO
from scipy.ndimage import gaussian_gradient_magnitude
import numpy as np
from PIL import Image
from wordcloud import WordCloud
from matplotlib import pyplot as plt
from utils.asyncstuff import asyncexe
from collections import Counter


class Chat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @asyncexe()
    def wordcloud_(self, text, icon):
        m = None
        #         if icon:
        #             mask = np.array(Image.open(icon))
        #             mask = mask[::3, ::3]
        #             m = mask.copy()
        #             m[m.sum(axis=2) == 0] = 255
        #             edges = np.mean([gaussian_gradient_magnitude(mask[:, :, i] / 255., 2) for i in range(3)], axis=0)
        #             m[edges > .08] = 255
        wordcloud = WordCloud(width=1000, height=500, max_words=300).generate(text)
        image = wordcloud.to_image()
        b = BytesIO()
        image.save(b, "PNG")
        b.seek(0)
        return b

    @commands.command()
    @commands.max_concurrency(1, commands.BucketType.channel)
    async def wordcloud(self, ctx, limit: int = 1000):
        limit = min(limit, 10000)
        counter = 0
        m = await ctx.send(
            embed=discord.Embed(
                color=self.bot.color,
                title="Collecting messages",
                description=f"{counter} / {limit}",
            )
        )
        async with ctx.typing():
            text = ""
            async for message in ctx.channel.history(limit=limit):
                counter += 1
                if message.content:
                    text += message.content
                if counter % 250 == 0:
                    await m.edit(
                        embed=discord.Embed(
                            color=self.bot.color,
                            title="Collecting messages",
                            description=f"{counter} / {limit}",
                        )
                    )
            icon = None
            if ctx.guild:
                icon = (
                    BytesIO(await ctx.guild.icon_url_as(format="png").read())
                    if ctx.guild.icon_url_as(format="png")
                    else None
                )
            pic = await self.wordcloud_(text, icon)
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
    @commands.max_concurrency(1, commands.BucketType.channel)
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
    bot.add_cog(Chat(bot))
