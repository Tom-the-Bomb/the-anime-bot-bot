import collections
import colorsys

import discord
from colordict import ColorDict
from colormath.color_conversions import convert_color
from colormath.color_objects import XYZColor, sRGBColor
from discord.ext import commands
from glitch_this import ImageGlitcher
from scipy.spatial import KDTree
from webcolors import CSS3_HEX_TO_NAMES, hex_to_rgb

colors = ColorDict()
import asyncio
import functools
import os
import re
import time
import typing
import warnings
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from copy import copy
from io import BytesIO
from itertools import chain
from random import randrange
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote

import aiohttp
import config
import cv2
import imutils
import numpy as np
import polaroid
import pytesseract
import qrcode
import ratelimiter
import ujson
from asyncdagpi import ImageFeatures
from PIL import (Image, ImageColor, ImageDraw, ImageEnhance, ImageFilter,
                 ImageOps, ImageSequence)
from pyzbar.pyzbar import decode
from qrcode.image.pure import PymagingImage
from twemoji_parser import emoji_to_url
from utils.asyncstuff import asyncexe
from utils.subclasses import AnimeContext, InvalidImage
from wand.image import Image as WandImage
from wand.resource import limits

RGB_SCALE = 255
CMYK_SCALE = 100

limits["width"] = 1000
limits["height"] = 1000
limits["thread"] = 10

warnings.simplefilter("error", Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS = 1000 * 1000

ree = re.compile(r"\?.+")
authorizationthing = config.ksoft

Image_Union = Union[
    discord.Member,
    discord.User,
    discord.PartialEmoji,
    discord.Emoji,
    str,
]


class ColorConverter(commands.Converter):
    async def convert(self, ctx, argument):
        converter = commands.ColourConverter()
        try:
            color = await converter.convert(ctx, argument)
            color = color.to_rgb()
        except commands.BadColourArgument:
            if argument.isdigit() and int(argument) <= 16777215:
                try:
                    argument = int(argument)
                    blue = argument & 255
                    green = (argument >> 8) & 255
                    red = (argument >> 16) & 255
                    return red, green, blue
                except ValueError:
                    pass
            try:
                color = colors[argument]
            except KeyError:
                try:
                    color = ImageColor.getrgb(argument)
                except ValueError:
                    raise commands.BadArgument
        return tuple((int(i) for i in color))


class Processing:
    __slots__ = ("ctx", "start", "m")

    def __init__(self, ctx: AnimeContext):
        self.ctx = ctx
        self.start = None
        self.m = None

    async def __aenter__(self, *args: List[Any], **kwargs):
        self.start = time.perf_counter()
        self.m = await asyncio.wait_for(
            self.ctx.reply("<a:loading:849756871597490196> Image Processing."), timeout=3.0
        )
        return self

    async def __aexit__(self, *args, **kwargs):
        try:
            await self.m.delete()
            await asyncio.wait_for(
                self.ctx.reply(
                    f" <:check_mark:849758044833447949> Image Process complete, took {round(time.perf_counter() - self.start, 3)} seconds"
                ),
                timeout=3.0,
            )
        except discord.HTTPException:
            return


class Images(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_cdn_ratelimiter = ratelimiter.RateLimiter(max_calls=1, period=6)
        self.cdn_ratelimiter = ratelimiter.RateLimiter(max_calls=3, period=7)
        self.ocr_ratelimiter = ratelimiter.RateLimiter(max_calls=2, period=10)

    async def get_url(self, ctx: AnimeContext, thing: Optional[str], **kwargs: Dict[str, Any]) -> str:
        url = None
        avatar = kwargs.get("avatar", True)
        check = kwargs.get("check", True)
        checktype = kwargs.get("checktype", True)
        gif = kwargs.get("gif", False)
        if ctx.message.reference:
            message = ctx.message.reference.resolved
            if message.embeds and message.embeds[0].type == "image":
                url = message.embeds[0].thumbnail.url
            elif message.embeds and message.embeds[0].type == "rich":
                if message.embeds[0].image.url:
                    url = message.embeds[0].image.url
                elif message.embeds[0].thumbnail.url:
                    url = message.embeds[0].thumbnail.url
            elif message.attachments and message.attachments[0].width and message.attachments[0].height:
                url = message.attachments[0].url
            if message.stickers:
                sticker = message.stickers[0]
                if sticker.format != discord.StickerType.lottie:
                    url = str(sticker.image_url_as())
                else:
                    raise InvalidImage("Lottie Stickers are not accepted.")

        if ctx.message.attachments and ctx.message.attachments[0].width and ctx.message.attachments[0].height:
            url = ctx.message.attachments[0].url
        if ctx.message.stickers:
            sticker = ctx.message.stickers[0]
            if sticker.format != discord.StickerType.lottie:
                url = str(sticker.image_url_as())
            else:
                raise InvalidImage("Lottie Stickers are not accepted.")
        if thing is None and avatar and url is None:
            if gif:
                url = str(ctx.author.avatar_url_as(static_format="png", size=512))
            else:
                url = str(ctx.author.avatar_url_as(format="png", size=512))
        elif isinstance(thing, (discord.PartialEmoji, discord.Emoji)):
            if gif:
                url = str(thing.url_as(static_format="png"))
            else:
                url = str(thing.url_as(format="png"))
        elif isinstance(thing, (discord.Member, discord.User)):
            if gif:
                url = str(thing.avatar_url_as(static_format="png", size=512))
            else:
                url = str(thing.avatar_url_as(format="png", size=512))
        elif url is None:
            thing = str(thing).strip("<>")
            if self.bot.url_regex.match(thing):
                url = thing
            else:
                url = await emoji_to_url(thing)
                if url == thing:
                    raise InvalidImage("Invalid url")
        if not avatar:
            return None
        if not url:
            raise commands.BadArgument(message="Unable to retrieve any information, this is extremely rare.")
        if check:
            async with self.bot.session.get(url) as resp:
                if resp.status != 200:
                    raise InvalidImage("Unable to fetch the image.")
                if "image" not in resp.content_type:
                    raise InvalidImage("Not a valid image file, could be a DOS attack.")
                if checktype:
                    b = await resp.content.read(50)
                    if b.startswith(b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A") or b.startswith(b"\x89PNG"):
                        pass
                    elif b[0:3] == b"\xff\xd8\xff" or b[6:10] in (b"JFIF", b"Exif"):
                        pass
                    elif b.startswith((b"\x47\x49\x46\x38\x37\x61", b"\x47\x49\x46\x38\x39\x61")):
                        pass
                    elif b[:2] in (b"MM", b"II"):
                        pass
                    elif len(b) >= 3 and b[0] == ord(b"P") and b[1] in b"25" and b[2] in b" \t\n\r":
                        pass
                    elif b.startswith(b"BM"):
                        pass
                    elif not b.startswith(b"RIFF") or b[8:12] != b"WEBP":
                        raise InvalidImage("Unsupported image type given")
                    if resp.headers.get("Content-Length") and int(resp.headers.get("Content-Length")) > 10000000:
                        raise InvalidImage("Image Larger then 10 MB")
        return url

    def get_gif_url(self, ctx: AnimeContext, thing: Optional[str], **kwargs: Dict[str, Any]) -> str:
        return self.get_url(ctx, thing, gif=True, **kwargs)

    async def bot_cdn(self, url: str) -> str:
        async with self.bot_cdn_ratelimiter:
            async with self.bot.session.get(url) as resp:
                content = resp.content_type
                if "image" not in resp.content_type and "webm" not in resp.content_type:
                    return "Invalid image"
                async with self.bot.session.post(
                    "https://theanimebot.is-ne.at/upload",
                    data={"image": await resp.read(), "noembed": "True"},
                ) as resp:
                    if resp.status != 200:
                        return "something went wrong"
                    js = await resp.json()
                    return f"<{js.get('url')}>"

    async def cdn_(self, url) -> str:
        async with self.cdn_ratelimiter:
            async with self.bot.session.get(url) as resp:
                if "image" not in resp.content_type:
                    return "Invalid image"
                async with self.bot.session.post(
                    "https://idevision.net/api/cdn",
                    headers={
                        "Authorization": config.idevision,
                        "File-Name": ree.split(str(resp.url).split("/")[-1])[0],
                    },
                    data=resp.content,
                ) as resp:
                    return (await resp.json())["url"]

    async def ocr__(self, url: str) -> str:
        async with self.ocr_ratelimiter:
            async with self.bot.session.get(url) as resp:
                if "image" not in resp.content_type:
                    return "Invalid image"
                async with self.bot.session.get(
                    f"https://idevision.net/api/public/ocr?filetype={resp.content_type[1]}",
                    headers={"Authorization": config.idevision},
                    data=resp.content,
                ) as resp:
                    return (await resp.json())["data"]

    @staticmethod
    def detect(c):
        shape = "unidentified"
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.04 * peri, True)
        if len(approx) == 3:
            return "triangle"
        if len(approx) == 4:
            (x, y, w, h) = cv2.boundingRect(approx)
            ar = w / float(h)
            return "square" if ar >= 0.95 and ar <= 1.05 else "rectangle"
        if len(approx) == 5:
            return "pentagon"
        return "circle"
    
    @staticmethod
    def save_transparent_gif(images: List[Image.Image], durations: Union[int, List[int]], save_file):
        # root_frame, save_args = self._create_animated_gif(images, durations)
        # root_frame.save(save_file, **save_args)
        # root_frame.close()
        # for i in images:
        #     i.close()
        images[0].save(
            save_file, format="GIF", append_images=images[1:], durations=durations, disposal=2, loop=0, save_all=True
        )

    @staticmethod
    def resize(image: Image) -> Image:
        if image.height <= 500 and image.width <= 500:
            return image
        # I robbed from preselany I can't do math ok
        siz = 500
        w, h = image.size
        if w > h:
            the_key = w / siz
            size = (siz, int(h / the_key))
        elif h > w:
            the_key = h / siz
            size = (int(w / the_key), siz)
        else:
            size = (siz, siz)
            # image.close()
        return image.resize(size, resample=Image.NEAREST, reducing_gap=1)

    @staticmethod
    def open_pil_image(buffer: BytesIO) -> Image:
        try:
            return Image.open(buffer, "RGBA")
        except (TypeError, ValueError):
            try:
                return Image.open(buffer, "RGB")
            except (TypeError, ValueError):
                return Image.open(buffer)

    @asyncexe()
    def run_polaroid(self, image1: bytes, method: str, *args: List[Any], **kwargs: Dict[str, Any]) -> discord.File:
        # image1 = self.resize(BytesIO(image1))
        img = self.open_pil_image(BytesIO(image1))
        if img.is_animated and img.n_frames < 200:
            to_process = []
            to_make_gif = []
            for im in ImageSequence.Iterator(img):
                b = BytesIO()
                im_ = self.resize(im)
                im_.save(b, "PNG")
                b.seek(0)
                to_process.append(b)
            for i in to_process:
                p_image = polaroid.Image(i.read())
                method1 = getattr(p_image, method)
                method1(*args, **kwargs)
                b = BytesIO(p_image.save_bytes("png"))
                to_make_gif.append(Image.open(b).convert("RGBA"))
                b.close()
            final = BytesIO()
            self.save_transparent_gif(to_make_gif, img.info.get("duration", 10), final)
            for i in to_process:
                i.close()
            for i in to_make_gif:
                i.close()
            final.seek(0)
            img.close()
            return discord.File(final, filename=f"{method}.gif")

        i = img
        image1_ = self.resize(i)
        image1 = BytesIO()
        image1_.save(image1, "PNG")
        image1.seek(0)
        im = polaroid.Image(image1.read())
        method1 = getattr(im, method)
        method1(*args, **kwargs)
        b = BytesIO(im.save_bytes("png"))
        i.close()
        image1.close()
        return discord.File(b, filename=f"{method}.png")

    async def polaroid_(self, image, method, *args: list[Any], **kwargs: Dict[str, Any]):
        async with self.bot.session.get(image) as resp:
            image1 = await resp.read()
        result = await self.run_polaroid(image1, method, *args, **kwargs)
        return result

    @staticmethod
    @asyncexe()
    def circle__(background_color: str, circle_color: str) -> BytesIO:
        frames = []
        mid = 100
        for i in range(500):
            with Image.new("RGB", (200, 200), background_color) as img:
                imgr = ImageDraw.Draw(img)
                imgr.ellipse(
                    (100 - i * 20, 100 - i * 20, 100 + i * 20, 100 + i * 20),
                    fill=circle_color,
                )
                fobj = BytesIO()
                img.save(fobj, "GIF")
                img = Image.open(fobj)
                frames.append(img)
                fobj.close()
        igif = BytesIO()
        frames[0].save(
            igif,
            format="GIF",
            append_images=frames[1:],
            save_all=True,
            duration=3,
            loop=0,
        )
        igif.seek(0)
        for i in frames:
            i.close()
        return igif

    @asyncexe()
    def process_gif(self, image, function, *args: list[Any]) -> Tuple[BytesIO, str]:
        img = self.open_pil_image(BytesIO(image))
        if img.is_animated and img.n_frames < 200:
            to_make_gif = []
            for im in ImageSequence.Iterator(img):
                im_ = self.resize(im)
                im_ = im_.convert("RGBA")
                im_final = function(im_, *args)
                to_make_gif.append(im_final)
            final = BytesIO()
            self.save_transparent_gif(to_make_gif, img.info.get("duration", 10), final)
            to_make_gif[0].save(final, format="GIF", append_images=to_make_gif[1:], disposal=2, loop=0, save_all=True)
            for i in to_make_gif:
                i.close()
            final.seek(0)
            img.close()
            return final, "gif"
        img_ = img
        format_ = img_.format
        img_ = self.resize(img_)
        img_ = img_.convert("RGBA")
        img = function(img_, *args)
        b = BytesIO()
        img.save(b, "PNG")
        b.seek(0)
        img_.close()
        img.close()
        return b, "png"
    
    @asyncexe()
    def spin__(self, image: bytes, speed: int) -> Tuple[BytesIO, str]:
        im_ = self.open_pil_image(BytesIO(image))
        im__ = self.resize(im_)
        im___ = im__.convert("RGBA")
        to_make_gif = [im___.rotate(degree, resample=Image.BICUBIC, expand=0) for degree in range(0, 360, 10)]
        final = BytesIO()
        self.save_transparent_gif(to_make_gif, speed, final)
        final.seek(0)
        im_.close()
        im__.close()
        im___.close()
        for i in to_make_gif:
            i.close()
        return final, "gif"

    async def spin_(self, url: str, speed: int) -> discord.File:
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        result, format = await self.spin__(image1, speed)
        result = discord.File(result, f"The_Anime_Bot_spin.{format_}")
        return result

    @staticmethod
    def invert__(image: Image) -> Image:
        r, g, b, a = image.split()
        rgb_image = Image.merge("RGB", (r, g, b))
        inverted_image = ImageOps.invert(rgb_image)
        r2, g2, b2 = inverted_image.split()
        return Image.merge("RGBA", (r2, g2, b2, a))

    async def invert_(self, url: str) -> discord.File:
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        result, format_ = await self.process_gif(image1, self.invert__)
        result = discord.File(result, f"The_Anime_Bot_invert.{format_}")
        return result

    async def mirror_(self, url: str) -> discord.File:
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        result, format_ = await self.process_gif(image1, ImageOps.mirror)
        result = discord.File(result, f"The_Anime_Bot_mirror.{format_}")
        return result

    async def flip_(self, url: str) -> discord.File:
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        result, format_ = await self.process_gif(image1, ImageOps.flip)
        result = discord.File(result, f"The_Anime_Bot_flip.{format_}")
        return result

    async def grayscale_(self, url: str) -> discord.File:
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        result, format_ = await self.process_gif(image1, ImageOps.grayscale)
        result = discord.File(result, f"The_Anime_Bot_grayscale.{format_}")
        return result

    async def posterize_(self, url: str) -> discord.File:
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        result, format_ = await self.process_gif(image1, ImageOps.posterize, 3)
        result = discord.File(result, f"The_Anime_Bot_posterize.{format_}")
        return result

    async def solarize_(self, url: str) -> discord.File:
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        result, format_ = await self.process_gif(image1, ImageOps.solarize)
        result = discord.File(result, f"The_Anime_Bot_solarize.{format_}")
        return result

    async def circle_(self, background_color: str, circle_color: str):
        result = await self.circle__(background_color, circle_color)
        return result

    @staticmethod
    @asyncexe()
    def floor_(b: BytesIO) -> BytesIO:
        with WandImage(file=b) as img_:
            with WandImage(img_.sequence[0]) as img:
                # I robbed resize from preselany I can't do math ok
                siz = 500
                w, h = img.size
                if w > h:
                    the_key = w / siz
                    size = (siz, int(h / the_key))
                elif h > w:
                    the_key = h / siz
                    size = (int(w / the_key), siz)
                else:
                    size = (siz, siz)
                img.resize(size[0], size[1])
                img.virtual_pixel = "tile"
                arguments = (
                    0,
                    0,
                    img.width * 0.3,
                    img.height * 0.5,
                    img.width,
                    0,
                    img.width * 0.8,
                    img.height * 0.5,
                    0,
                    img.height,
                    img.width * 0.1,
                    img.height,
                    img.width,
                    img.height,
                    img.width * 0.9,
                    img.height,
                )
                img.distort("perspective", arguments)
                final = BytesIO()
                img.save(file=final)
                final.seek(0)
                return final

    @staticmethod
    @asyncexe()
    def qr_enc(thing: str) -> BytesIO:
        q = qrcode.make(thing, image_factory=PymagingImage)
        pic = BytesIO()
        q.save(pic)
        pic.seek(0)
        return pic

    @staticmethod
    @asyncexe()
    def qr_dec(bytes_: BytesIO) -> str:
        with Image.open(bytes_) as img:
            return decode(img)[0].data.decode("utf-8")

    @staticmethod
    @asyncexe()
    def convertimage_(image: BytesIO, format: str, f: Optional[str]) -> Tuple[BytesIO, str]:
        with WandImage(file=image, format=f) as img:
            if img.height > 500 or img.width > 500:
                # I robbed resize from preselany I can't do math ok
                siz = 500
                w, h = img.size
                if w > h:
                    the_key = w / siz
                    size = (siz, int(h / the_key))
                elif h > w:
                    the_key = h / siz
                    size = (int(w / the_key), siz)
                else:
                    size = (siz, siz)
                img.resize(size[0], size[1])
            with img.convert(format) as img:
                b = BytesIO()
                img.save(file=b)
                b.seek(0)
                return b, img.format
    
    @commands.command()
    async def changemymind(self, ctx, *, thing: str):
        """
        Change my mind
        """
        async with Processing(ctx):
            async with self.bot.session.get("https://nekobot.xyz/api/imagegen", params={"type": "changemymind", "text": thing}, timeout=aiohttp.ClientTimeout()) as resp:
                j = await resp.json()
                async with self.bot.session.get(j["message"]) as resp:
                    b = BytesIO(await resp.read())
                    await ctx.send(file=discord.File(b, "The_Anime_Bot_Change_My_Mind.png"))

    @commands.command()
    async def stickbug(self, ctx, thing: Optional[Image_Union]):
        """
        Get stickbugged
        """
        async with Processing(ctx):
            url = await self.get_url(ctx, thing, checktype=True)
            async with self.bot.session.get("https://nekobot.xyz/api/imagegen", params={"type": "stickbug", "url": url}, timeout=aiohttp.ClientTimeout()) as resp:
                j = await resp.json()
                async with self.bot.session.get(j["message"]) as resp:
                    b = BytesIO(await resp.read())
                    await ctx.send(file=discord.File(b, "stickbug.mp4"))


    @commands.command(aliases=["converti"])
    async def convertimage(
        self, ctx: AnimeContext, thing: Optional[Image_Union], format: lambda x: str(x).upper() = "PNG"
    ) -> None:
        """
        Convert image type.
        Note:
        You can't convert image to svg as that is a vector image.
        """
        if format == "SVG":
            return await ctx.send("You can't convert image to svg as that is a vector image.")
        async with Processing(ctx):
            url = await self.get_url(ctx, thing, checktype=False)
            async with self.bot.session.get(url) as resp:
                b = BytesIO(await resp.read())
                f = None
                h = b.read(10)
                if h.startswith(b"<svg") or h.startswith(b"<?xml"):
                    f = "svg"
                b.seek(0)
                b, f = await self.convertimage_(b, format, f)
                await ctx.reply(file=discord.File(b, f"The_Anime_Bot_image_format_convert.{f.lower()}"))

    @commands.command()
    async def code(self, ctx: AnimeContext, *, code: str) -> None:
        """
        Generate a cool image to display code.
        """
        if code.startswith("`"):
            last = collections.deque(maxlen=3)
            backticks = 0
            in_language = False
            in_code = False
            language = []
            code_ = []

            for char in code:
                if char == "`" and not in_code and not in_language:
                    backticks += 1
                if last and last[-1] == "`" and char != "`" or in_code and "".join(last) != "`" * backticks:
                    in_code = True
                    code_.append(char)
                if char == "\n":
                    in_language = False
                    in_code = True
                elif "".join(last) == "`" * 3 and char != "`":
                    in_language = True
                    language.append(char)
                elif in_language:
                    language.append(char)

                last.append(char)

            if not code_ and not language:
                code_[:] = last
            code = "".join(code_[len(language) : -backticks])

        url = config.secret_code_api
        bobo = {
            "paddingVertical": "56px",
            "paddingHorizontal": "56px",
            "backgroundImage": None,
            "backgroundImageSelection": None,
            "backgroundMode": "color",
            "backgroundColor": "rgba(26,127,220,0.62)",
            "dropShadow": True,
            "dropShadowOffsetY": "20px",
            "dropShadowBlurRadius": "68px",
            "theme": "vscode",
            "windowTheme": "none",
            "language": "auto",
            "fontFamily": "Hack",
            "fontSize": "14px",
            "lineHeight": "133%",
            "windowControls": True,
            "widthAdjustment": True,
            "lineNumbers": False,
            "firstLineNumber": 1,
            "exportSize": "2x",
            "watermark": False,
            "squaredImage": False,
            "hiddenCharacters": False,
            "name": "",
            "width": 680,
            "code": code,
        }
        async with Processing(ctx):
            async with self.bot.session.post(url, json=bobo) as resp:
                await ctx.reply(file=discord.File(BytesIO(await resp.read()), "The_Anime_Bot_code.png"))

    @staticmethod
    @asyncexe()
    def shape_detection(image: BytesIO) -> discord.File:
        with Image.open(image) as img:
            buffer = BytesIO()
            img_ = img.convert("RGB")
            img_.save(buffer, "PNG")
            img_.close()
            buffer.seek(0)
        np_array = np.asarray(bytearray(buffer.read()), dtype=np.uint8)
        image = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        resized = imutils.resize(image, width=300)
        ratio = image.shape[0] / float(resized.shape[0])
        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(gray, (5, 5), 0)
        thresh = cv2.threshold(blurred, 60, 255, cv2.THRESH_BINARY)[1]
        cnts = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        for c in cnts:
            M = cv2.moments(c)
            cX = int((M["m10"] / (M["m00"] + 1e-7)) * ratio)
            cY = int((M["m01"] / (M["m00"] + 1e-7)) * ratio)
            shape = self.detect(c)
            c = c.astype("float")
            c *= ratio
            c = c.astype("int")
            cv2.drawContours(image, [c], -1, (0, 255, 0), 2)
            cv2.putText(image, shape, (cX, cY), cv2.FONT_HERSHEY_DUPLEX, 0.5, (255, 0, 0), 2)
        is_success, im_buf_arr = cv2.imencode(".png", image)
        b = BytesIO(im_buf_arr)
        return discord.File(b, "The_Anime_Bot_shape_detection.png")

    @commands.command()
    async def shapedetection(self, ctx: AnimeContext, thing: Image_Union = None) -> None:
        """
        Detect shapes in a image and label them.
        """
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            async with self.bot.session.get(url) as resp:
                b = BytesIO(await resp.read())
            await ctx.reply(file=await self.shape_detection(b))

    @staticmethod
    @asyncexe()
    def facereg_(image: BytesIO) -> discord.File:
        with Image.open(image) as img:
            buffer = BytesIO()
            img_ = img.convert("RGB")
            img_.save(buffer, "PNG")
            img_.close()
            buffer.seek(0)
        np_array = np.asarray(bytearray(buffer.read()), dtype=np.uint8)
        img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        haar_face_cascade = cv2.CascadeClassifier(
            "/usr/local/lib/python3.9/site-packages/cv2/data/haarcascade_frontalface_alt.xml"
        )
        eye_cascade = cv2.CascadeClassifier(
            "/usr/local/lib/python3.9/site-packages/cv2/data/haarcascade_eye_tree_eyeglasses.xml"
        )
        smile_cascade = cv2.CascadeClassifier("/usr/local/lib/python3.9/site-packages/cv2/data/haarcascade_smile.xml")
        faces = haar_face_cascade.detectMultiScale(gray_img, scaleFactor=1.1, minNeighbors=5)
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            roi_gray = gray_img[y : y + h, x : x + w]
            roi_color = img[y : y + h, x : x + w]
            eyes = eye_cascade.detectMultiScale(roi_gray)
            smiles = smile_cascade.detectMultiScale(roi_gray, scaleFactor=1.1, minNeighbors=30)
            for (ex, ey, ew, eh) in eyes:
                cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (255, 0, 0), 2)
            for (ex, ey, ew, eh) in smiles:
                cv2.rectangle(roi_color, (ex, ey), (ex + ew, ey + eh), (0, 0, 255), 2)
                break
        is_success, im_buf_arr = cv2.imencode(".png", img)
        b = BytesIO(im_buf_arr)
        return discord.File(b, "The_Anime_Bot_Face_Reg.png")

    @staticmethod
    @asyncexe()
    def make_color_image(color: str) -> BytesIO:
        with Image.new("RGB", (200, 200), color) as img:
            b = BytesIO()
            img.save(b, "PNG")
            b.seek(0)
            return b

    @staticmethod
    def rgb_to_hsv(
        r: Union[int, float], g: Union[int, float], b: Union[int, float]
    ) -> Tuple[float, float, float]:
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        mx = max(r, g, b)
        mn = min(r, g, b)
        df = mx - mn
        if mx == mn:
            h = 0
        elif mx == r:
            h = (60 * ((g - b) / df) + 360) % 360
        elif mx == g:
            h = (60 * ((b - r) / df) + 120) % 360
        elif mx == b:
            h = (60 * ((r - g) / df) + 240) % 360
        s = 0 if mx == 0 else (df / mx) * 100
        v = mx * 100
        return h, s, v

    @staticmethod
    def rgb_to_xy_bri(
        r: Union[int, float], g: Union[int, float], b: Union[int, float]
    ) -> Tuple[float, float, float]:
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        o = (
            (0.412453 * r + 0.35758 * g + 0.180423 * b),
            (0.212671 * r + 0.71516 * g + 0.072169 * b),
            (0.019334 * r + 0.119193 * g + 0.950227 * b),
        )
        return tuple((round(i * 100) for i in o))

    @staticmethod
    def rgb_to_hsl(r: Union[int, float], g: Union[int, float], b: Union[int, float]) -> str:
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        mx = max(r, g, b)
        mn = min(r, g, b)
        df = mx - mn
        if mx == mn:
            h = 0
        elif mx == r:
            h = (60 * ((g - b) / df) + 360) % 360
        elif mx == g:
            h = (60 * ((b - r) / df) + 120) % 360
        elif mx == b:
            h = (60 * ((r - g) / df) + 240) % 360
        s = 0 if mx == 0 else (df / mx) * 100
        lightness = ((mx + mn) / 2) * 100
        return f"({round(h)}, {round(s)}%, {round(lightness)}%)"

    @staticmethod
    def rgb_to_cmyk(rgb_tuple: Tuple[int, int, int]) -> Tuple[float, float, float]:
        r, g, b = rgb_tuple[0], rgb_tuple[1], rgb_tuple[2]
        if (r, g, b) == (0, 0, 0):

            return 0, 0, 0, CMYK_SCALE

        c = 1 - r / RGB_SCALE
        m = 1 - g / RGB_SCALE
        y = 1 - b / RGB_SCALE

        min_cmy = min(c, m, y)
        c = (c - min_cmy) / (1 - min_cmy)
        m = (m - min_cmy) / (1 - min_cmy)
        y = (y - min_cmy) / (1 - min_cmy)
        k = min_cmy

        return c * CMYK_SCALE, m * CMYK_SCALE, y * CMYK_SCALE, k * CMYK_SCALE

    @staticmethod
    @asyncexe()
    def convert_rgb_to_names(rgb_tuple: Tuple[int, int, int]) -> str:
        css3_db = CSS3_HEX_TO_NAMES
        names = []
        rgb_values = []
        for color_hex, color_name in css3_db.items():
            names.append(color_name)
            rgb_values.append(hex_to_rgb(color_hex))

        kdt_db = KDTree(rgb_values)
        distance, index = kdt_db.query(rgb_tuple)
        return names[index]

    @commands.command()
    async def colorinfo(self, ctx: AnimeContext, *, color: ColorConverter) -> None:
        """
        Returns a color's info. It accepts a lot different input. Like rgb(255, 255, 255) white #ffffff 0xffffff etc
        """
        img = await self.make_color_image(color)
        name = await self.convert_rgb_to_names(color)
        embed = discord.Embed(color=discord.Color.from_rgb(*color), title=name)
        embed.add_field(name="RGB", value=color)
        embed.add_field(name="CMYK", value=tuple((round(i) for i in self.rgb_to_cmyk(color))))
        embed.add_field(
            name="HSV",
            value=f"({round(self.rgb_to_hsv(*color)[0])}, {round(self.rgb_to_hsv(*color)[1])}%, {round(self.rgb_to_hsv(*color)[2])}%)",
        )
        embed.add_field(name="HEX", value=f"#{'%02x%02x%02x' % color} | 0x{'%02x%02x%02x' % color}")
        embed.add_field(name="HSL", value=self.rgb_to_hsl(*color))
        embed.add_field(name="XYZ", value=tuple((round(i) for i in self.rgb_to_xy_bri(*color))))
        embed.set_thumbnail(url=f"attachment://The_Anime_Bot_color_{name}.png")
        await ctx.send(embed=embed, file=discord.File(img, f"The_Anime_Bot_color_{name}.png"))

    @commands.command()
    async def floor(self, ctx: AnimeContext, thing: Image_Union = None) -> None:
        """
        Returns floor effect of a image.
        """
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            async with self.bot.session.get(url) as resp:
                b = BytesIO(await resp.read())
            await ctx.reply(file=discord.File(await self.floor_(b), "The_Anime_Bot_floor.png"))

    @commands.command()
    async def facerec(self, ctx: AnimeContext, thing: Image_Union = None) -> None:
        """
        Recognize faces, eyes, and smiles/mouths in a image and label them.
        """
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            async with self.bot.session.get(url) as resp:
                b = BytesIO(await resp.read())
            await ctx.reply(file=await self.facereg_(b))

    @commands.command()
    async def latex(self, ctx: AnimeContext, *, text: str) -> None:
        """
        Returns a LaTeX image of your text.
        """
        async with self.bot.session.get(
            f"https://latex.codecogs.com/png.latex?%5Cdpi%7B300%7D%20%5Cbg_black%20%5Chuge%20{quote(text)}"
        ) as resp:
            await ctx.reply(
                embed=discord.Embed(title="LaTeX", color=self.bot.color).set_image(
                    url="attachment://The_Anime_Bot_latex.png"
                ),
                file=discord.File(BytesIO(await resp.read()), "The_Anime_Bot_latex.png"),
            )

    @commands.command()
    async def spin(self, ctx, thing: Image_Union = None) -> None:
        """
        Spin a image.
        """
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            await ctx.reply(file=await self.spin_(url, 64))

    @commands.group(invoke_without_command=True)
    async def qr(self, ctx, *, thing):
        """
        Produce a qr code.
        """
        async with Processing(ctx):
            try:
                pic = await self.qr_enc(thing)
            except Exception:
                return await ctx.reply("Too big big")
            await ctx.reply(file=discord.File(pic, "qrcode.png"))

    @qr.command(name="decode")
    async def qr_decode(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        """
        Decode a qr code.
        """
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            async with self.bot.session.get(url) as resp:
                bytes_ = BytesIO(await resp.read())
                try:
                    data = await self.qr_dec(bytes_)
                except Exception:
                    return await ctx.reply("Can't regonize qrcode")
                embed = discord.Embed(color=self.bot.color, description=data)
                await ctx.reply(embed=embed)

    @commands.command()
    async def caption(
        self,
        ctx: AnimeContext,
        thing: Image_Union = None,
    ):
        """
        Caption a image.
        """
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            data = {"Content": url, "Type": "CaptionRequest"}
            async with self.bot.session.post(
                "https://captionbot.azurewebsites.net/api/messages",
                headers={"Content-Type": "application/json; charset=utf-8"},
                data=ujson.dumps(data),
            ) as resp:
                text = await resp.text()
                embed = discord.Embed(color=self.bot.color, title=text)
                embed.set_image(url="attachment://caption.png")
                async with self.bot.session.get(url) as resp:
                    bytes_ = BytesIO(await resp.read())
                await ctx.reply(embed=embed, file=discord.File(bytes_, "caption.png"))

    @commands.command()
    async def botcdn(
        self,
        ctx: AnimeContext,
        thing: Image_Union = None,
    ):
        """
        Upload a image to the bot's cdn.
        """
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            await ctx.reply(f"{await self.bot_cdn(url)}")

    @commands.command()
    async def cdn(
        self,
        ctx: AnimeContext,
        thing: Image_Union = None,
    ):
        """
        Upload a image to idevision cdn.
        """
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            await ctx.reply(f"<{await self.cdn_(url)}>")

    @staticmethod
    @asyncexe()
    def ocr_(image):
        with Image.open(image) as img:
            buffer = BytesIO()
            if "A" in img.getbands():
                background = Image.new("RGB", img.size, (255, 255, 255))
                background.paste(img, (0, 0), img.getchannel("A"))
                img = background
            img.save(buffer, "PNG")
            buffer.seek(0)
        np_array = np.asarray(bytearray(buffer.read()), dtype=np.uint8)
        img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        norm_img = np.zeros((img.shape[0], img.shape[1]))
        img = cv2.normalize(img, norm_img, 0, 255, cv2.NORM_MINMAX)
        img = cv2.threshold(img, 100, 255, cv2.THRESH_BINARY)[1]
        img = cv2.GaussianBlur(img, (1, 1), 0)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        ocr_config = r'--tessdata-dir "/home/cryptex/ocr_data"'
        return pytesseract.image_to_string(img, config=ocr_config)

    @commands.command()
    async def ocr(
        self,
        ctx: AnimeContext,
        thing: Image_Union = None,
    ):
        """
        Recognize text in a image.
        Note:
        It works better with white background.
        """
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            async with self.bot.session.get(url) as resp:
                image = BytesIO(await resp.read())
            await ctx.reply(f"```\n{await self.ocr_(image)}\n```") if len(
                f"```\n{await self.ocr_(image)}\n```"
            ) <= 2000 else await ctx.reply(await ctx.paste(f"```\n{await self.ocr_(image)}\n```"))

    @commands.command()
    async def aww(self, ctx):
        """
        Return a cute image.
        """
        async with Processing(ctx):
            async with self.bot.session.get(
                "https://api.ksoft.si/images/random-aww",
                headers={"Authorization": authorizationthing},
            ) as resp:
                res = await resp.json()
                link = res.get("image_url")
                async with self.bot.session.get(link) as resp:
                    buffer = BytesIO(await resp.read())
            await ctx.reply(file=discord.File(buffer, "aww.png"))

    @commands.command()
    async def womancat(
        self,
        ctx: AnimeContext,
        woman: typing.Optional[Image_Union],
        cat: typing.Optional[Image_Union],
    ):
        """
        The woman point at cat meme.
        """
        async with Processing(ctx):
            url = await self.get_url(ctx, woman)
            url1 = await self.get_url(ctx, cat)
            pic = await self.bot.vacefron_api.woman_yelling_at_cat(woman=url, cat=url1)
            await ctx.reply(file=discord.File(await pic.read(), filename="woman_yelling_at_cat.png"))

    @commands.command()
    async def circle(self, ctx: AnimeContext, background_color="white", circle_color="blue"):
        """
        Make a circle.
        """
        async with Processing(ctx):
            igif = await self.circle_(background_color, circle_color)
            await ctx.reply(file=discord.File(igif, "circle.gif"))

    @commands.command()
    async def npc(
        self,
        ctx,
        text1: str = "You gotta enter something",
        text2: str = "yeye",
    ):
        """
        Return the npc meme.
        """
        async with Processing(ctx):
            pic = await self.bot.vacefron_api.npc(text1, text2)
            await ctx.reply(file=discord.File(await pic.read(), filename=f"npc_{text1}_{text2}.png"))

    @commands.command()
    async def amongus(self, ctx, name: str = "you", color: str = "red", imposter: bool = True):
        """
        Return the sussy imposter got ejected amongus image.
        """
        async with Processing(ctx):
            pic = await self.bot.vacefron_api.ejected(name, color, imposter)
            await ctx.reply(
                file=discord.File(
                    await pic.read(),
                    filename=f"among_us_{name}_{color}_{imposter}.png",
                )
            )

    @commands.command()
    async def randompicture(self, ctx: AnimeContext, *, seed: str = None):
        async with Processing(ctx):
            if seed:
                async with self.bot.session.get(f"https://picsum.photos/seed/{seed}/3840/2160") as resp:
                    pic = BytesIO(await resp.read())
            else:
                async with self.bot.session.get("https://picsum.photos/3840/2160") as resp:
                    pic = BytesIO(await resp.read())
            await ctx.reply(file=discord.File(pic, filename="randompicture.png"))

    @commands.command()
    async def dym(self, ctx: AnimeContext, up, bottom):
        """
        Google do you mean picture
        Usage: ovo dym \"anime bot is bad bot\" \"anime bot is good bot\"
        """
        async with Processing(ctx):
            embed = discord.Embed(color=self.bot.color).set_image(url="attachment://alex.png")
            image = discord.File(
                await (await self.bot.alex.didyoumean(up, bottom)).read(),
                "alex.png",
            )
            await ctx.reply(embed=embed, file=image)

    @commands.command()
    async def gradiant(self, ctx):
        async with Processing(ctx):
            embed = discord.Embed(color=self.bot.color).set_image(url="attachment://alex.png")
            image = discord.File(
                await (await self.bot.alex.colour_image_gradient()).read(),
                "alex.png",
            )
            await ctx.reply(embed=embed, file=image)

    @commands.command()
    async def amiajoke(
        self,
        ctx,
        thing: typing.Optional[Image_Union],
        level: float = 0.3,
    ):
        async with Processing(ctx):
            level = min(level, 1)
            url = await self.get_url(ctx, thing)
            embed = discord.Embed(color=self.bot.color).set_image(url="attachment://alex.png")
            image = discord.File(await (await self.bot.alex.amiajoke(url)).read(), "alex.png")
            await ctx.reply(embed=embed, file=image)

    @commands.group(invoke_without_command=True)
    async def supreme(self, ctx: AnimeContext, *, text: str = "enter something here"):
        async with Processing(ctx):
            embed = discord.Embed(color=self.bot.color).set_image(url="attachment://alex.png")
            image = discord.File(await (await self.bot.alex.supreme(text=text)).read(), "alex.png")
            await ctx.reply(embed=embed, file=image)

    @supreme.command(name="dark")
    async def supreme_dark(self, ctx: AnimeContext, *, text: str = "enter something here"):
        async with Processing(ctx):
            embed = discord.Embed(color=self.bot.color).set_image(url="attachment://alex.png")
            image = discord.File(
                await (await self.bot.alex.supreme(text=text, dark=True)).read(),
                "alex.png",
            )
            await ctx.reply(embed=embed, file=image)

    @commands.command()
    async def archive(self, ctx: AnimeContext, *, text):
        async with Processing(ctx):
            embed = discord.Embed(color=self.bot.color).set_image(url="attachment://alex.png")
            image = discord.File(
                await (await self.bot.alex.achievement(text=text)).read(),
                "alex.png",
            )
            await ctx.reply(embed=embed, file=image)

    # @commands.command()
    # async def pixelate(
    #     self,
    #     ctx,
    #     thing: typing.Optional[Image_Union],
    #     level: float = 0.3,
    # ):
    #     async with Processing(ctx):
    #         level = min(level, 1)
    #         url = await self.get_url(ctx, thing)
    #         try:
    #             image = await self.bot.zaneapi.pixelate(url, level)
    #         except asyncio.TimeoutError:
    #             raise commands.CommandError("Zaneapi timeout")
    #         embed = discord.Embed(color=self.bot.color).set_image(url="attachment://pixelate.png")
    #         await ctx.reply(
    #             file=discord.File(fp=image, filename="pixelate.png"),
    #             embed=embed,
    #         )

    # @commands.command()
    # async def swirl(
    #     self,
    #     ctx,
    #     thing: Image_Union = None,
    # ):
    #     async with Processing(ctx):
    #         url = await self.get_url(ctx, thing)
    #         try:
    #             image = await self.bot.zaneapi.swirl(url)
    #         except asyncio.TimeoutError:
    #             raise commands.CommandError("Zaneapi timeout")
    #         embed = discord.Embed(color=self.bot.color).set_image(url="attachment://swirl.gif")
    #         await ctx.reply(file=discord.File(fp=image, filename="swirl.gif"), embed=embed)

    # @commands.command()
    # async def sobel(
    #     self,
    #     ctx,
    #     thing: Image_Union = None,
    # ):
    #     async with Processing(ctx):
    #         url = await self.get_url(ctx, thing)
    #         image = await self.bot.zaneapi.sobel(url)
    #         embed = discord.Embed(color=self.bot.color).set_image(url="attachment://sobel.png")
    #         await ctx.reply(file=discord.File(fp=image, filename="sobel.png"), embed=embed)

    # @commands.command()
    # async def palette(
    #     self,
    #     ctx,
    #     thing: Image_Union = None,
    # ):
    #     async with Processing(ctx):
    #         url = await self.get_url(ctx, thing)
    #         image = await self.bot.zaneapi.palette(url)
    #         embed = discord.Embed(color=self.bot.color).set_image(url="attachment://palette.png")
    #         await ctx.reply(
    #             file=discord.File(fp=image, filename="palette.png"),
    #             embed=embed,
    #         )

    # @commands.command()
    # async def sort(
    #     self,
    #     ctx,
    #     thing: Image_Union = None,
    # ):
    #     async with Processing(ctx):
    #         url = await self.get_url(ctx, thing)
    #         image = await self.bot.zaneapi.sort(url)
    #         embed = discord.Embed(color=self.bot.color).set_image(url="attachment://sort.png")
    #         await ctx.reply(file=discord.File(fp=image, filename="sort.png"), embed=embed)

    # @commands.command()
    # async def cube(
    #     self,
    #     ctx,
    #     thing: Image_Union = None,
    # ):
    #     async with Processing(ctx):
    #         url = await self.get_url(ctx, thing)
    #         try:
    #             image = await self.bot.zaneapi.cube(url)
    #         except asyncio.TimeoutError:
    #             raise commands.CommandError("Zaneapi timeout")
    #         embed = discord.Embed(color=self.bot.color).set_image(url="attachment://cube.png")
    #         await ctx.reply(file=discord.File(fp=image, filename="cube.png"), embed=embed)

    # @commands.command()
    # async def braille(
    #     self,
    #     ctx,
    #     thing: Image_Union = None,
    # ):
    #     async with Processing(ctx):
    #         url = await self.get_url(ctx, thing)
    #         image = await self.bot.zaneapi.braille(url)
    #         await ctx.reply(image)

    # @commands.command(aliases=["dot"])
    # async def dots(
    #     self,
    #     ctx,
    #     thing: Image_Union = None,
    # ):
    #     async with Processing(ctx):
    #         url = await self.get_url(ctx, thing)
    #         image = await self.bot.zaneapi.dots(url)
    #         embed = discord.Embed(color=self.bot.color).set_image(url="attachment://dots.png")
    #         await ctx.reply(file=discord.File(fp=image, filename="dots.png"), embed=embed)

    # @commands.command()
    # async def threshold(
    #     self,
    #     ctx,
    #     thing: Image_Union = None,
    # ):
    #     async with Processing(ctx):
    #         url = await self.get_url(ctx, thing)
    #         image = await self.bot.zaneapi.threshold(url)
    #         embed = discord.Embed(color=self.bot.color).set_image(url="attachment://threshold.png")
    #         await ctx.reply(
    #             file=discord.File(fp=image, filename="threshold.png"),
    #             embed=embed,
    #         )

    # @commands.command()
    # async def spread(
    #     self,
    #     ctx,
    #     thing: Image_Union = None,
    # ):
    #     async with Processing(ctx):
    #         url = await self.get_url(ctx, thing)
    #         image = await self.bot.zaneapi.spread(url)
    #         embed = discord.Embed(color=self.bot.color).set_image(url="attachment://spread.gif")
    #         await ctx.reply(file=discord.File(fp=image, filename="spread.gif"), embed=embed)

    # @commands.command()
    # async def jpeg(
    #     self,
    #     ctx,
    #     thing: Image_Union = None,
    # ):
    #     async with Processing(ctx):
    #         url = await self.get_url(ctx, thing)
    #         image = await self.bot.zaneapi.jpeg(url)
    #         embed = discord.Embed(color=self.bot.color).set_image(url="attachment://jpeg.gif")
    #         await ctx.reply(file=discord.File(fp=image, filename="jpeg.gif"), embed=embed)

    @staticmethod
    @asyncexe()
    def magic_(image: BytesIO, intensity: float):
        with WandImage(file=image) as img:
            with WandImage(img.sequence[0]) as img:
                if img.height > 500 or img.width > 500:
                    # I robbed resize from preselany I can't do math ok
                    siz = 500
                    w, h = img.size
                    if w > h:
                        the_key = w / siz
                        size = (siz, int(h / the_key))
                    elif h > w:
                        the_key = h / siz
                        size = (int(w / the_key), siz)
                    else:
                        size = (siz, siz)
                    img.resize(size[0], size[1])
                img.liquid_rescale(
                    width=round(img.width * 0.5),
                    height=round(img.height * 0.5),
                    delta_x=round(intensity * 0.5),
                    rigidity=0,
                )
                b = BytesIO()
                img.save(b)
                b.seek(0)
                return b

    @commands.command(aliases=["magik"])
    async def magic(
        self,
        ctx,
        thing: typing.Optional[Image_Union],
        intensity: float = 0.6,
    ):
        if intensity > 10:
            return await ctx.send("intensity lower then 10")
        if intensity <= 0:
            return await ctx.send("It can't be lower or equal to 0")
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            async with self.bot.session.get(url) as resp:
                image = BytesIO(await resp.read())
            await ctx.send(file=discord.File(await self.magic_(image, intensity), "The_Anime_Bot_magic.png"))

    # @commands.command()
    # @commands.max_concurrency(1, commands.BucketType.user)
    # async def floor(
    #     self,
    #     ctx,
    #     thing: commands.Greedy[
    #         Image_Union
    #         ]
    #     ] = None,
    # ):
    #     async with Processing(ctx):
    #         if not thing:
    #             url = await self.get_url(ctx, thing)
    #             image = await self.bot.zaneapi.floor(url)
    #             embed = discord.Embed(color=self.bot.color).set_image(
    #                 url="attachment://floor.gif"
    #             )
    #             return await ctx.reply(
    #                 file=discord.File(fp=image, filename="floor.gif"),
    #                 embed=embed,
    #             )

    #         if len(thing) > 10:
    #             return await ctx.reply("the max is 10")
    #         for i in thing:
    #             url = await self.get_url(ctx, i)
    #             image = await self.bot.zaneapi.floor(url)
    #             embed = discord.Embed(color=self.bot.color).set_image(
    #                 url="attachment://floor.gif"
    #             )
    #             await ctx.reply(
    #                 file=discord.File(fp=image, filename="floor.gif"),
    #                 embed=embed,
    #             )

    # @commands.command()
    # async def noise(self, ctx):
    #     stat_ = await self.image(
    #         ctx,
    #         await ctx.author.avatar_url_as(format="png").read(),
    #         "add_noise_rand",
    #     )

    @commands.command(aliases=["wtp"])
    async def pokemon(self, ctx):
        await ctx.trigger_typing()
        wtp = await self.bot.dag.wtp()
        tried = 3
        if ctx.author.id == 590323594744168494:
            await ctx.author.reply(wtp.name)
        embed = discord.Embed(color=0x2ECC71)
        ability = "".join(wtp.abilities)
        embed.set_author(name=f"{ctx.author} has {tried} tries")
        embed.add_field(name="pokemon's ability", value=ability)
        embed.set_image(url=wtp.question)
        message = await ctx.reply(embed=embed)

        def check(m):
            return m.author == ctx.author

        for x in range(3):
            msg = await self.bot.wait_for("message", check=check)
            tried -= 1
            embed = discord.Embed(color=0x2ECC71)
            ability = "".join(wtp.abilities)
            embed.set_author(name=f"{ctx.author} has {tried} tries")
            embed.add_field(name="Pokemon's Ability", value=ability)
            embed.set_image(url=wtp.question)
            await message.edit(embed=embed)
            if msg.content.lower() == wtp.name.lower():
                embed = discord.Embed(color=0x2ECC71)
                embed.set_author(name=f"{ctx.author} won")
                embed.set_image(url=wtp.answer)
                await ctx.reply(embed=embed)
                await message.delete()
                tried = 3
                return
            if tried == 0:
                await message.delete()
                embed = discord.Embed(color=0x2ECC71)
                embed.set_author(name=f"{ctx.author} lost")
                embed.set_image(url=wtp.answer)
                await ctx.reply(embed=embed)
                tried = 3
                return

    @commands.command()
    async def captcha(
        self,
        ctx,
        thing: Image_Union = None,
        *,
        text="enter something here",
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            text1 = text
            img = await self.bot.dag.image_process(ImageFeatures.captcha(), url, text=text1)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def solarize(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            file = await self.solarize_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def invert(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            await ctx.reply(file=await self.invert_(url))

    @commands.command()
    async def oil(
        self,
        ctx,
        thing: typing.Optional[Image_Union],
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            await ctx.reply(file=await self.polaroid_(url, "oil", 3, 10))

    @asyncexe()
    def glitch_(self, image: Image, intensity: float):
        glitcher = ImageGlitcher()
        with Image.open(image) as img:
            to_make_gif = []
            if img.is_animated and img.n_frames < 200:
                for im in ImageSequence.Iterator(img):
                    b = BytesIO()
                    im.save(b, "PNG")
                    b.seek(0)
                    with Image.open(b) as img_:
                        to_make_gif.append(glitcher.glitch_image(img_, intensity, color_offset=True))
                final = BytesIO()
                self.save_transparent_gif(to_make_gif, img.info.get("duration", 10), final)
            else:
                for _ in range(10):
                    to_make_gif.append(glitcher.glitch_image(img, intensity, color_offset=True))
                final = BytesIO()
                self.save_transparent_gif(to_make_gif, 69, final)

            final.seek(0)
            return discord.File(final, "The_Anime_Bot_glitch.gif")

    @commands.command()
    async def glitch(self, ctx, thing: typing.Optional[Image_Union] = None, intensity: float = 5.0):
        if intensity > 10:
            return await ctx.send("Intensity must be under 10")
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            async with self.bot.session.get(url) as resp:
                image = BytesIO(await resp.read())
            await ctx.reply(file=await self.glitch_(image, intensity))

    @commands.command()
    async def rainbow(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            await ctx.reply(file=await self.polaroid_(url, "apply_gradient"))

    @commands.command()
    async def awareness(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.magik(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def night(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.night(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def paint(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.paint(), url)
        file = discord.File(fp=img.image, filename=f"The_Anime_Bot_paint.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def polaroid(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.polaroid(), url)
            file = discord.File(fp=img.image, filename=f"The_Anime_Bot_polaroid.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def sepia(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.sepia(), url)
            file = discord.File(fp=img.image, filename=f"The_Anime_Bot_sepia.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def posterize(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            file = await self.posterize_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def mirror(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            file = await self.mirror_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def flip(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            file = await self.flip_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def grayscale(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_gif_url(ctx, thing)
            file = await self.grayscale_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def ascii(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.ascii(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def deepfry(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.deepfry(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def trash(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.trash(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def gay(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.gay(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def shatter(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.shatter(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def delete(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.delete(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def fedora(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.fedora(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def jail(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.jail(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def sith(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.sith(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def bad(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.bad(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def obama(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.obama(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def hitler(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.hitler(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command(aliases=["evil"])
    async def satan(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.satan(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def angel(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.angel(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def rgb(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.rgb(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def blur(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.blur(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def hog(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.hog(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def triangle(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.triangle(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def wasted(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.wasted(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def america(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.america(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def triggered(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.triggered(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def wanted(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.wanted(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def colors(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.colors(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)

    @commands.command()
    async def pixel(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with Processing(ctx):
            url = await self.get_url(ctx, thing)
            img = await self.bot.dag.image_process(ImageFeatures.pixel(), url)
            file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
            await ctx.reply(file=file)


def setup(bot):
    bot.add_cog(Images(bot))
