import discord
from discord.ext import commands
import flags
import aiohttp
import asyncio
from twemoji_parser import emoji_to_url
import typing
import os
from utils.asyncstuff import asyncexe
import polaroid
from PIL import Image, ImageDraw
from io import BytesIO
from asyncdagpi import ImageFeatures
import typing


class pictures(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    async def polaroid_(self, image, method):
        async with self.bot.session.get(image) as resp:
            image1 = await resp.read()
        im = polaroid.Image(image1)
        method1 = getattr(im, method)
        method1()
        file = discord.File(BytesIO(im.save_bytes()), filename="polaroid.png")
        return file


    @staticmethod
    @asyncexe()
    def circle_(background_color, circle_color):
        frames = []
        mid = 100
        for i in range(500):
            img = Image.new("RGB", (200, 200), background_color)
            imgr = ImageDraw.Draw(img)
            imgr.ellipse((100-i*20, 100-i*20, 100+i*20,
                          100+i*20), fill=circle_color)
            fobj = BytesIO()
            img.save(fobj, "GIF")
            img = Image.open(fobj)
            frames.append(img)
        igif = BytesIO()
        frames[0].save(igif, format='GIF', append_images=frames[1:],
                       save_all=True, duration=3, loop=0)
        igif.seek(0)
        return igif

    @commands.command()
    async def aww(self, ctx):
        async with self.bot.session.get("https://api.ksoft.si/images/random-aww", headers = {"Authorization": os.getenv("ksoft")}) as resp:
            res = await resp.json()
            link = res.get("image_url")
            async with self.bot.session.get(link) as resp:
                buffer = BytesIO(await resp.read())
        await ctx.send(file=discord.File(buffer, "aww.png"))

    @commands.command()
    async def womancat(self, ctx, woman: typing.Optional[typing.Union[discord.Member,
                                                discord.PartialEmoji,
                                                discord.Emoji, str]], cat: typing.Optional[typing.Union[discord.Member,
                                                discord.PartialEmoji,
                                                discord.Emoji, str]]):
        if woman == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
        elif isinstance(woman, discord.PartialEmoji) or isinstance(
                woman, discord.Emoji):
            url = str(woman.url)
        elif isinstance(woman, discord.Member) or isinstance(
                woman, discord.User):
            url = str(woman.avatar_url_as(static_format="png"))
        else:
            woman = str(woman)
            if woman.startswith("http") or woman.startswith(
                    "https") or woman.startswith("www"):
                url = woman
            else:
                url = await emoji_to_url(woman)
        if cat == None:
            url1 = str(ctx.me.avatar_url_as(static_format="png"))
        elif isinstance(cat, discord.PartialEmoji) or isinstance(
                cat, discord.Emoji):
            url1 = str(cat.url)
        elif isinstance(woman, discord.Member) or isinstance(
                cat, discord.User):
            url1 = str(cat.avatar_url_as(static_format="png"))
        else:
            cat = str(cat)
            if cat.startswith("http") or cat.startswith(
                    "https") or cat.startswith("www"):
                url1 = cat
            else:
                url1 = await emoji_to_url(cat)
        pic = await self.bot.vacefron_api.woman_yelling_at_cat(woman=url, cat=url1)
        await ctx.send(file=discord.File(await pic.read(),
                                        filename=f"woman_yelling_at_cat.png"))

    @commands.command()
    async def circle(self, ctx, background_color="white", circle_color="blue"):
        igif = await self.circle_(background_color, circle_color)
        await ctx.send(file=discord.File(igif, "circle.gif"))

    @commands.command()
    async def npc(self,
                  ctx,
                  text1: str = "You gotta enter something",
                  text2: str = "yeye"):
        pic = await self.bot.vacefron_api.npc(text1, text2)
        await ctx.send(file=discord.File(await pic.read(),
                                         filename=f"npc_{text1}_{text2}.png"))

    @commands.command()
    async def amongus(self,
                      ctx,
                      name: str = "you",
                      color: str = "red",
                      imposter: bool = True):
        pic = await self.bot.vacefron_api.ejected(name, color, imposter)
        await ctx.send(file=discord.File(
            await pic.read(),
            filename=f"among_us_{name}_{color}_{imposter}.png"))

    @commands.command()
    async def randompicture(self, ctx, *, seed: str = None):
        if seed:
            async with self.bot.session.get(
                    f"https://picsum.photos/seed/{seed}/3840/2160") as resp:
                pic = BytesIO(await resp.read())
        else:
            async with self.bot.session.get(
                    "https://picsum.photos/3840/2160") as resp:
                pic = BytesIO(await resp.read())
        await ctx.send(file=discord.File(pic, filename="randompicture.png"))

    @commands.command()
    async def dym(self, ctx, up, bottom):
        """
    Google do you mean picture
    Usage: ovo dym \"anime bot is bad bot\" \"anime bot is good bot\"
    """
        embed = discord.Embed(color=0x00ff6a).set_image(
            url="attachment://alex.png")
        image = discord.File(
            await (await self.bot.alex.didyoumean(up, bottom)).read(),
            "alex.png")
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def gradiant(self, ctx):
        embed = discord.Embed(color=0x00ff6a).set_image(
            url="attachment://alex.png")
        image = discord.File(
            await (await self.bot.alex.colour_image_gradient()).read(),
            "alex.png")
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def amiajoke(
            self,
            ctx,
            thing: typing.Optional[typing.Union[discord.Member,
                                                discord.PartialEmoji,
                                                discord.Emoji, str]],
            level: float = 0.3):
        async with ctx.channel.typing():
            if level > 1:
                level = 1
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                thing = str(thing)
                if thing.startswith("http") or thing.startswith(
                        "https") or thing.startswith("www"):
                    url = thing
                else:
                    url = await emoji_to_url(thing)
        embed = discord.Embed(color=0x00ff6a).set_image(
            url="attachment://alex.png")
        image = discord.File(await (await self.bot.alex.amiajoke(url)).read(),
                             "alex.png")
        await ctx.send(embed=embed, file=image)

    @commands.group(invoke_without_command=True)
    async def supreme(self, ctx, *, text: str = "enter something here"):
        embed = discord.Embed(color=0x00ff6a).set_image(
            url="attachment://alex.png")
        image = discord.File(
            await (await self.bot.alex.supreme(text=text)).read(), "alex.png")
        await ctx.send(embed=embed, file=image)

    @supreme.command(name="dark")
    async def supreme_dark(self, ctx, *, text: str = "enter something here"):
        embed = discord.Embed(color=0x00ff6a).set_image(
            url="attachment://alex.png")
        image = discord.File(
            await (await self.bot.alex.supreme(text=text, dark=True)).read(), "alex.png")
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def archive(self, ctx, *, text):
        embed = discord.Embed(color=0x00ff6a).set_image(
            url="attachment://alex.png")
        image = discord.File(
            await (await self.bot.alex.achievement(text=text)).read(),
            "alex.png")
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def pixelate(
            self,
            ctx,
            thing: typing.Optional[typing.Union[discord.Member,
                                                discord.PartialEmoji,
                                                discord.Emoji, str]],
            level: float = 0.3):
        async with ctx.channel.typing():
            if level > 1:
                level = 1
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                thing = str(thing)
                if thing.startswith("http") or thing.startswith(
                        "https") or thing.startswith("www"):
                    url = thing
                else:
                    url = await emoji_to_url(thing)
            try:
                image = await self.bot.zaneapi.pixelate(url, level)
            except asyncio.TimeoutError:
                raise commands.CommandError("Zaneapi timeout")
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://pixelate.png")
            await ctx.send(file=discord.File(fp=image,
                                             filename="pixelate.png"),
                           embed=embed)

    @commands.command()
    async def swirl(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                thing = str(thing)
                if thing.startswith("http") or thing.startswith(
                        "https") or thing.startswith("www"):
                    url = thing
                else:
                    url = await emoji_to_url(thing)
            try:
                image = await self.bot.zaneapi.swirl(url)
            except asyncio.TimeoutError:
                raise commands.CommandError("Zaneapi timeout")
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://swirl.gif")
            await ctx.send(file=discord.File(fp=image, filename="swirl.gif"),
                           embed=embed)

    @commands.command()
    async def sobel(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            image = await self.bot.zaneapi.sobel(url)
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://sobel.png")
            await ctx.send(file=discord.File(fp=image, filename="sobel.png"),
                           embed=embed)

    @commands.command()
    async def palette(self,
                      ctx,
                      thing: typing.Union[discord.Member, discord.PartialEmoji,
                                          discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            image = await self.bot.zaneapi.palette(url)
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://palette.png")
            await ctx.send(file=discord.File(fp=image, filename="palette.png"),
                           embed=embed)

    @commands.command()
    async def sort(self,
                   ctx,
                   thing: typing.Union[discord.Member, discord.PartialEmoji,
                                       discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            image = await self.bot.zaneapi.sort(url)
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://sort.png")
            await ctx.send(file=discord.File(fp=image, filename="sort.png"),
                           embed=embed)

    @commands.command()
    async def cube(self,
                   ctx,
                   thing: typing.Union[discord.Member, discord.PartialEmoji,
                                       discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            try:
                image = await self.bot.zaneapi.cube(url)
            except asyncio.TimeoutError:
                raise commands.CommandError("Zaneapi timeout")
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://cube.png")
            await ctx.send(file=discord.File(fp=image, filename="cube.png"),
                           embed=embed)

    @commands.command()
    async def braille(self,
                      ctx,
                      thing: typing.Union[discord.Member, discord.PartialEmoji,
                                          discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            image = await self.bot.zaneapi.braille(url)
            await ctx.send(image)

    @commands.command(aliases=["dot"])
    async def dots(self,
                   ctx,
                   thing: typing.Union[discord.Member, discord.PartialEmoji,
                                       discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            image = await self.bot.zaneapi.dots(url)
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://dots.png")
            await ctx.send(file=discord.File(fp=image, filename="dots.png"),
                           embed=embed)

    @commands.command()
    async def threshold(self,
                        ctx,
                        thing: typing.Union[discord.Member,
                                            discord.PartialEmoji,
                                            discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            image = await self.bot.zaneapi.threshold(url)
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://threshold.png")
            await ctx.send(file=discord.File(fp=image,
                                             filename="threshold.png"),
                           embed=embed)

    @commands.command()
    async def spread(self,
                     ctx,
                     thing: typing.Union[discord.Member, discord.PartialEmoji,
                                         discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            image = await self.bot.zaneapi.spread(url)
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://spread.gif")
            await ctx.send(file=discord.File(fp=image, filename="spread.gif"),
                           embed=embed)

    @commands.command()
    async def jpeg(self,
                   ctx,
                   thing: typing.Union[discord.Member, discord.PartialEmoji,
                                       discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            image = await self.bot.zaneapi.jpeg(url)
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://jpeg.gif")
            await ctx.send(file=discord.File(fp=image, filename="jpeg.gif"),
                           embed=embed)

    @commands.command(aliases=["magik"])
    async def magic(self,
                    ctx,
                    thing: typing.Optional[typing.Union[discord.Member,
                                                        discord.PartialEmoji,
                                                        discord.Emoji, str]],
                    level: float = 0.6):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            image = await self.bot.zaneapi.magic(url, level)
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://magic.gif")
            await ctx.send(file=discord.File(fp=image, filename="magic.gif"),
                           embed=embed)

    @commands.command()
    async def floor(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                try:
                    url = await emoji_to_url(thing)
                except:
                    url = thing
            image = await self.bot.zaneapi.floor(url)
            embed = discord.Embed(color=0x00ff6a).set_image(
                url="attachment://floor.gif")
            await ctx.send(file=discord.File(fp=image, filename="floor.gif"),
                           embed=embed)

    # @commands.command()
    # async def rainbow(self, ctx):
    #   stat_ = await self.image(ctx, await ctx.author.avatar_url_as(format="png").read(), "apply_gradient")

    @commands.command()
    async def noise(self, ctx):
        stat_ = await self.image(
            ctx, await ctx.author.avatar_url_as(format="png").read(),
            "add_noise_rand")

    @commands.command()
    async def pokemon(self, ctx):
        await ctx.trigger_typing()
        wtp = await self.bot.dag.wtp()
        tried = 3
        if ctx.author.id == 590323594744168494:
            await ctx.author.send(wtp.name)
        embed = discord.Embed(color=0x2ecc71)
        ability = "".join(wtp.abilities)
        embed.set_author(name=f"{ctx.author} have {tried} try")
        embed.add_field(name="pokemon's ability", value=ability)
        embed.set_image(url=wtp.question)
        message = await ctx.send(embed=embed)

        def check(m):
            return m.author == ctx.author

        for x in range(3):
            msg = await self.bot.wait_for("message", check=check)
            tried -= 1
            embed = discord.Embed(color=0x2ecc71)
            ability = "".join(wtp.abilities)
            embed.set_author(name=f"{ctx.author} have {tried} try")
            embed.add_field(name="pokemon's ability", value=ability)
            embed.set_image(url=wtp.question)
            await message.edit(embed=embed)
            if msg.content.lower() == wtp.name.lower():
                embed = discord.Embed(color=0x2ecc71)
                embed.set_author(name=f"{ctx.author} won")
                embed.set_image(url=wtp.answer)
                await ctx.reply(embed=embed)
                await message.delete()
                tried = 3
                return
            if tried == 0:
                await message.delete()
                embed = discord.Embed(color=0x2ecc71)
                embed.set_author(name=f"{ctx.author} losed")
                embed.set_image(url=wtp.answer)
                await ctx.reply(embed=embed)
                tried = 3
                return

    @commands.command()
    async def captcha(self,
                      ctx,
                      thing: typing.Union[discord.Member, discord.PartialEmoji,
                                          discord.Emoji, str] = None,
                      *,
                      text="enter something here"):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(ctx.author.avatar_url_as(static_format="png"))
            else:
                url = thing
            text1 = text
        img = await self.bot.dag.image_process(ImageFeatures.captcha(),
                                               url,
                                               text=text1)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def solar(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.solar(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def rainbow(self,
                      ctx,
                      thing: typing.Union[discord.Member, discord.PartialEmoji,
                                          discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.rainbow(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def awareness(self,
                        ctx,
                        thing: typing.Union[discord.Member,
                                            discord.PartialEmoji,
                                            discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.magik(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def night(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.night(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def paint(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.paint(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def polaroid(self,
                       ctx,
                       thing: typing.Union[discord.Member,
                                           discord.PartialEmoji, discord.Emoji,
                                           str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.polaroid(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def sepia(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.sepia(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def poster(self,
                     ctx,
                     thing: typing.Union[discord.Member, discord.PartialEmoji,
                                         discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.poster(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def charcoal(self,
                       ctx,
                       thing: typing.Union[discord.Member,
                                           discord.PartialEmoji, discord.Emoji,
                                           str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.charcoal(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def ascii(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.ascii(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def deepfry(self,
                      ctx,
                      thing: typing.Union[discord.Member, discord.PartialEmoji,
                                          discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.deepfry(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def trash(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.trash(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def gay(self,
                  ctx,
                  thing: typing.Union[discord.Member, discord.PartialEmoji,
                                      discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.gay(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def shatter(self,
                      ctx,
                      thing: typing.Union[discord.Member, discord.PartialEmoji,
                                          discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.shatter(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def delete(self,
                     ctx,
                     thing: typing.Union[discord.Member, discord.PartialEmoji,
                                         discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.delete(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def fedora(self,
                     ctx,
                     thing: typing.Union[discord.Member, discord.PartialEmoji,
                                         discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.fedora(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def jail(self,
                   ctx,
                   thing: typing.Union[discord.Member, discord.PartialEmoji,
                                       discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.jail(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def sith(self,
                   ctx,
                   thing: typing.Union[discord.Member, discord.PartialEmoji,
                                       discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.sith(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def bad(self,
                  ctx,
                  thing: typing.Union[discord.Member, discord.PartialEmoji,
                                      discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.bad(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def obama(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.obama(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def hitler(self,
                     ctx,
                     thing: typing.Union[discord.Member, discord.PartialEmoji,
                                         discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.hitler(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command(aliases=["evil"])
    async def satan(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.satan(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def angel(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.angel(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def rgb(self,
                  ctx,
                  thing: typing.Union[discord.Member, discord.PartialEmoji,
                                      discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.rgb(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def blur(self,
                   ctx,
                   thing: typing.Union[discord.Member, discord.PartialEmoji,
                                       discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.blur(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def hog(self,
                  ctx,
                  thing: typing.Union[discord.Member, discord.PartialEmoji,
                                      discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.hog(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def triangle(self,
                       ctx,
                       thing: typing.Union[discord.Member,
                                           discord.PartialEmoji, discord.Emoji,
                                           str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.triangle(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def invert(self,
                     ctx,
                     thing: typing.Union[discord.Member, discord.PartialEmoji,
                                         discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.invert(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def wasted(self,
                     ctx,
                     thing: typing.Union[discord.Member, discord.PartialEmoji,
                                         discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.wasted(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def america(self,
                      ctx,
                      thing: typing.Union[discord.Member, discord.PartialEmoji,
                                          discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.america(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def triggered(self,
                        ctx,
                        thing: typing.Union[discord.Member,
                                            discord.PartialEmoji,
                                            discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.triggered(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def wanted(self,
                     ctx,
                     thing: typing.Union[discord.Member, discord.PartialEmoji,
                                         discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.wanted(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def colors(self,
                     ctx,
                     thing: typing.Union[discord.Member, discord.PartialEmoji,
                                         discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.colors(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def pixel(self,
                    ctx,
                    thing: typing.Union[discord.Member, discord.PartialEmoji,
                                        discord.Emoji, str] = None):
        async with ctx.channel.typing():
            if thing == None:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            elif isinstance(thing, discord.PartialEmoji) or isinstance(
                    thing, discord.Emoji):
                url = str(thing.url)
            elif isinstance(thing, discord.Member) or isinstance(
                    thing, discord.User):
                url = str(thing.avatar_url_as(static_format="png"))
            else:
                url = thing
        img = await self.bot.dag.image_process(ImageFeatures.pixel(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @staticmethod
    @asyncexe()
    def scared_(data):
        image = Image.open("3po4m7.jpg")
        pfp = Image.open(data)
        pfp.resize((106, 87))
        image.paste(pfp, (99, 29))
        image.save("profile.jpg")

    @commands.command()
    async def scared(self, ctx, author: discord.Member = None):
        await ctx.trigger_typing()
        if author == None:
            author = ctx.author
        asset = author.avatar_url_as(size=128)
        data = BytesIO(await asset.read())
        await self.scared_(data)
        embed = discord.Embed(color=0x2ecc71)
        embed.set_footer(
            text=f"requested by {ctx.author} response time : {round(self.bot.latency * 1000)} ms",
            icon_url=ctx.author.avatar_url)
        await ctx.reply(file=discord.File("profile.jpg"), embed=embed)


def setup(bot):
    bot.add_cog(pictures(bot))
