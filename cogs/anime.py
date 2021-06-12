import json
from io import BytesIO
from utils.subclasses import AnimeContext
import urllib
import bs4
import random
from utils.asyncstuff import asyncexe

import discord
from discord.ext import commands, menus


class AnimeMenuSource(menus.ListPageSource):
    def __init__(self, data: list):
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):
        return {"embed": entries[menu.current_page]}


class Anime(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def searchanime(
        self,
        ctx: AnimeContext,
        *,
        search: lambda x: urllib.parse.quote_plus(x),
    ):
        async with self.bot.session.get(f"https://crunchy-bot.live/api/anime/details?terms={search}") as resp:
            animes = await resp.json()
            embed_list = []
            for anime in animes:
                embed = discord.Embed(
                    color=self.bot.color,
                    title=anime["english"],
                    description=anime["description"],
                )
                embed.add_field(
                    name="Infos",
                    value=(
                        f"Japanese: {anime['japanese']}\n"
                        f"Type: {anime['type']}\n"
                        f"Episodes: {anime['episodes']}\n"
                        f"Studios: {anime['studios']}\n"
                        f"Genres: {anime['genres']}\n"
                        f"Ratings: {anime['rating']}"
                    ),
                )
                embed.add_field(
                    name="Rankings",
                    value=(
                        (
                            f"Ranked: {anime['ranked']}\n"
                            f"Popularity: {anime['popularity']}\n"
                            f"Members: {anime['members']}\n"
                            f"Favorites: {anime['favorites']}"
                        )
                    ),
                )
                characters = []
                for i in anime["characters_and_actor"]:
                    actor = i.get("voice_actor") or i.get("actor")
                    characters.append((f"Character: {i['character']} - Actor: " f"{actor}"))
                embed.add_field(
                    name="Characters and Actor",
                    value="\n".join(characters).replace("||", "\||"),
                    inline=False,
                )
                embed.set_image(url=anime["img_src"]) if anime.get("img_src") else ...
                embed_list.append(embed)
            pages = menus.MenuPages(source=AnimeMenuSource(embed_list), delete_message_after=True)
            await pages.start(ctx)

    @commands.command()
    async def weebpicture(self, ctx: AnimeContext):
        async with self.bot.session.get("https://neko.weeb.services/") as resp:
            buffer = BytesIO(await resp.read())
            await ctx.send(file=discord.File(fp=buffer, filename="anime.png"))

    @commands.command()
    async def animememes(self, ctx: AnimeContext):
        """
        Anime memes from reddit
        """
        await ctx.trigger_typing()
        async with self.bot.session.get("https://meme-api.herokuapp.com/gimme/Animemes") as resp:
            meme = await resp.json()
            if meme["nsfw"]:
                return True
            link = meme["postLink"]
            title = meme["title"]
            nsfw = meme["nsfw"]
            image = meme["preview"][-1]
        if nsfw:
            return
        embed = discord.Embed(color=self.bot.color)
        embed.set_author(name=title, url=link)
        embed.set_image(url=image)
        embed.set_footer(
            text=(f"requested by {ctx.author} response time:" f"{round(self.bot.latency * 1000)} ms"),
            icon_url=ctx.author.avatar_url,
        )
        await ctx.reply(embed=embed)

    @asyncexe()
    def animequote_(self, anime):
        soup = bs4.BeautifulSoup(anime)
        quote = soup.find(class_="quoteBig").getText()
        image = f"https://www.less-real.com{soup.find_all('img')[1]['src']}"
        embed = discord.Embed(color=self.bot.color, description=quote)
        embed.set_image(url=image)
        return embed

    @commands.command(aliases=["animequotes"], brief=" new new anime quote from the web ")
    async def animequote(self, ctx: AnimeContext):
        await ctx.trigger_typing()
        num = random.randint(1, 7830)
        async with self.bot.session.get(f"https://www.less-real.com/quotes/{num}") as resp:
            embed = await self.animequote_(await resp.text())
            await ctx.send(embed=embed)


def setup(bot):
    bot.add_cog(Anime(bot))
