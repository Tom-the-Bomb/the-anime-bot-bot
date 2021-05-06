import discord
from discord.ext import commands
from urllib.parse import quote
import warnings
import ujson
import qrcode
from utils.subclasses import AnimeContext
from qrcode.image.pure import PymagingImage
import cv2
import numpy as np
from pyzbar.pyzbar import decode
import re
import ratelimiter
import config
import flags
import functools
import aiohttp
import asyncio
from twemoji_parser import emoji_to_url
import typing
import os
from utils.asyncstuff import asyncexe
import polaroid
from concurrent.futures import ThreadPoolExecutor
from typing import Tuple, List, Union
from collections import defaultdict
from random import randrange
from itertools import chain
from PIL import Image, ImageDraw, ImageFilter
from PIL import ImageEnhance
from PIL import ImageSequence
from PIL import ImageOps
from io import BytesIO
from asyncdagpi import ImageFeatures
import typing

warnings.simplefilter('error', Image.DecompressionBombWarning)
Image.MAX_IMAGE_PIXELS = 44739243

ree = re.compile(r"\?.+")
authorizationthing = config.ksoft

Image_Union = typing.Union[
            discord.Member,
            discord.User,
            discord.PartialEmoji,
            discord.Emoji,
            str,
        ]

class TransparentAnimatedGifConverter(object):
    _PALETTE_SLOTSET = set(range(256))

    def __init__(self, img_rgba: Image.Image, alpha_threshold: int = 0):
        self._img_rgba = img_rgba
        self._alpha_threshold = alpha_threshold

    def _process_pixels(self):
        """Set the transparent pixels to the color 0."""
        self._transparent_pixels = {idx for idx, alpha in enumerate(
                    self._img_rgba.getchannel(channel='A').getdata())
                if alpha <= self._alpha_threshold}

    def _set_parsed_palette(self):
        """Parse the RGB palette color `tuple`s from the palette."""
        palette = self._img_p.getpalette()
        self._img_p_used_palette_idxs = {
            idx
            for pal_idx, idx in enumerate(self._img_p_data)
            if pal_idx not in self._transparent_pixels
        }

        self._img_p_parsedpalette = {
            idx: tuple(palette[idx * 3 : idx * 3 + 3])
            for idx in self._img_p_used_palette_idxs
        }

    def _get_similar_color_idx(self):
        """Return a palette index with the closest similar color."""
        old_color = self._img_p_parsedpalette[0]
        dict_distance = defaultdict(list)
        for idx in range(1, 256):
            color_item = self._img_p_parsedpalette[idx]
            if color_item == old_color:
                return idx
            distance = sum((
                abs(old_color[0] - color_item[0]),  # Red
                abs(old_color[1] - color_item[1]),  # Green
                abs(old_color[2] - color_item[2])))  # Blue
            dict_distance[distance].append(idx)
        return dict_distance[sorted(dict_distance)[0]][0]

    def _remap_palette_idx_zero(self):
        """Since the first color is used in the palette, remap it."""
        free_slots = self._PALETTE_SLOTSET - self._img_p_used_palette_idxs
        new_idx = free_slots.pop() if free_slots else \
            self._get_similar_color_idx()
        self._img_p_used_palette_idxs.add(new_idx)
        self._palette_replaces['idx_from'].append(0)
        self._palette_replaces['idx_to'].append(new_idx)
        self._img_p_parsedpalette[new_idx] = self._img_p_parsedpalette[0]
        del(self._img_p_parsedpalette[0])

    def _get_unused_color(self) -> tuple:
        """ Return a color for the palette that does not collide with any other already in the palette."""
        used_colors = set(self._img_p_parsedpalette.values())
        while True:
            new_color = (randrange(256), randrange(256), randrange(256))
            if new_color not in used_colors:
                return new_color

    def _process_palette(self):
        """Adjust palette to have the zeroth color set as transparent. Basically, get another palette
        index for the zeroth color."""
        self._set_parsed_palette()
        if 0 in self._img_p_used_palette_idxs:
            self._remap_palette_idx_zero()
        self._img_p_parsedpalette[0] = self._get_unused_color()

    def _adjust_pixels(self):
        """Convert the pixels into their new values."""
        if self._palette_replaces['idx_from']:
            trans_table = bytearray.maketrans(
                bytes(self._palette_replaces['idx_from']),
                bytes(self._palette_replaces['idx_to']))
            self._img_p_data = self._img_p_data.translate(trans_table)
        for idx_pixel in self._transparent_pixels:
            self._img_p_data[idx_pixel] = 0
        self._img_p.frombytes(data=bytes(self._img_p_data))

    def _adjust_palette(self):
        """Modify the palette in the new `Image`."""
        unused_color = self._get_unused_color()
        final_palette = chain.from_iterable(
            self._img_p_parsedpalette.get(x, unused_color) for x in range(256))
        self._img_p.putpalette(data=final_palette)

    def process(self) -> Image.Image:
        """Return the processed mode `P` `Image`."""
        self._img_p = self._img_rgba.convert(mode='P')
        self._img_p_data = bytearray(self._img_p.tobytes())
        self._palette_replaces = dict(idx_from=list(), idx_to=list())
        self._process_pixels()
        self._process_palette()
        self._adjust_pixels()
        self._adjust_palette()
        self._img_p.info['transparency'] = 0
        self._img_p.info['background'] = 0
        return self._img_p


class pictures(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_cdn_ratelimiter = ratelimiter.RateLimiter(
            max_calls=1, period=6
        )
        self.cdn_ratelimiter = ratelimiter.RateLimiter(max_calls=3, period=7)
        self.ocr_ratelimiter = ratelimiter.RateLimiter(max_calls=2, period=10)

    async def get_gif_url(self, ctx: AnimeContext, thing, **kwargs):
        url = None
        avatar = kwargs.get("avatar", True)
        check = kwargs.get("check", True)
        if ctx.message.reference:
            message = ctx.message.reference.resolved
            if message.embeds and message.embeds[0].type == "image":
                url = message.embeds[0].thumbnail.url
            elif message.embeds and message.embeds[0].type == "rich":
                if message.embeds[0].image.url:
                    url = message.embeds[0].image.url
                elif message.embeds[0].thumbnail.url:
                    url = message.embeds[0].thumbnail.url
            elif (
                message.attachments
                and message.attachments[0].width
                and message.attachments[0].height
            ):
                url = message.attachments[0].url
        if (
            ctx.message.attachments
            and ctx.message.attachments[0].width
            and ctx.message.attachments[0].height
        ):
            url = ctx.message.attachments[0].url

        if thing is None and avatar and url is None:
            url = str(ctx.author.avatar_url_as(static_format="png"))
        elif isinstance(thing, (discord.PartialEmoji, discord.Emoji)):
            url = str(thing.url_as())
        elif isinstance(thing, (discord.Member, discord.User)):
            url = str(thing.avatar_url_as(static_format="png"))
        elif url is None:
            thing = str(thing).strip("<>")
            if self.bot.url_regex.match(thing):
                url = thing
            else:
                url = await emoji_to_url(thing)
                if url == thing:
                    raise commands.CommandError("Invalid url")
        if not avatar:
            return None
        if not url:
            raise commands.MissingRequiredArgument()
        if check:
            async with self.bot.session.get(url) as resp:
                if resp.status != 200:
                    raise commands.CommandError("Invalid Picture")
                if "image" not in resp.content_type:
                    raise commands.CommandError("Invalid Picture")
                b = await resp.content.read(50)
                if b.startswith(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'):
                    pass
                elif b[0:3] == b'\xff\xd8\xff' or b[6:10] in (b'JFIF', b'Exif'):
                    pass
                elif b.startswith((b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61')):
                    pass
                elif b.startswith(b'RIFF') and b[8:12] == b'WEBP':
                    pass
                else:
                    raise discord.InvalidArgument('Unsupported image type given')
        return url

    async def get_url(self, ctx: AnimeContext, thing, **kwargs):
        url = None
        avatar = kwargs.get("avatar", True)
        check = kwargs.get("check", True)
        if ctx.message.reference:
            message = ctx.message.reference.resolved
            if message.embeds and message.embeds[0].type == "image":
                url = message.embeds[0].thumbnail.url
            elif message.embeds and message.embeds[0].type == "rich":
                if message.embeds[0].image.url:
                    url = message.embeds[0].image.url
                elif message.embeds[0].thumbnail.url:
                    url = message.embeds[0].thumbnail.url
            elif (
                message.attachments
                and message.attachments[0].width
                and message.attachments[0].height
            ):
                url = message.attachments[0].url

        if (
            ctx.message.attachments
            and ctx.message.attachments[0].width
            and ctx.message.attachments[0].height
        ):
            url = ctx.message.attachments[0].url

        if thing is None and avatar and url is None:
            url = str(ctx.author.avatar_url_as(static_format="png"))
        elif isinstance(thing, (discord.PartialEmoji, discord.Emoji)):
            url = str(thing.url_as(format="png"))
        elif isinstance(thing, (discord.Member, discord.User)):
            url = str(thing.avatar_url_as(format="png"))
        elif url is None:
            thing = str(thing).strip("<>")
            if self.bot.url_regex.match(thing):
                url = thing
            else:
                url = await emoji_to_url(thing)
                if url == thing:
                    raise commands.CommandError("Invalid url")
        if not avatar:
            return None
        if not url:
            raise commands.MissingRequiredArgument()
        if check:
            async with self.bot.session.get(url) as resp:
                if resp.status != 200:
                    raise commands.CommandError("Invalid Picture")
                if "image" not in resp.content_type:
                    raise commands.CommandError("Invalid Picture")
                b = await resp.content.read(50)
                if b.startswith(b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'):
                    pass
                elif b[0:3] == b'\xff\xd8\xff' or b[6:10] in (b'JFIF', b'Exif'):
                    pass
                elif b.startswith((b'\x47\x49\x46\x38\x37\x61', b'\x47\x49\x46\x38\x39\x61')):
                    pass
                elif b.startswith(b'RIFF') and b[8:12] == b'WEBP':
                    pass
                else:
                    raise discord.InvalidArgument('Unsupported image type given')
        return url

    async def bot_cdn(self, url):
        async with self.bot_cdn_ratelimiter:
            async with self.bot.session.get(url) as resp:
                content = resp.content_type
                if (
                    "image" not in resp.content_type
                    and "webm" not in resp.content_type
                ):
                    return "Invalid image"
                async with self.bot.session.post(
                    "https://theanimebot.is-ne.at/upload",
                    data={"image": await resp.read(), "noembed": "True"},
                ) as resp:
                    if resp.status != 200:
                        return "something went wrong"
                    js = await resp.json()
                    return f"<{js.get('url')}>"

    async def cdn_(self, url):
        async with self.cdn_ratelimiter:
            async with self.bot.session.get(url) as resp:
                if "image" not in resp.content_type:
                    return "Invalid image"
                async with self.bot.session.post(
                    "https://idevision.net/api/cdn",
                    headers={
                        "Authorization": config.idevision,
                        "File-Name": ree.split(str(resp.url).split("/")[-1])[
                            0
                        ],
                    },
                    data=resp.content,
                ) as resp:
                    return (await resp.json())["url"]

    async def ocr_(self, url):
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


    def _create_animated_gif(self, images: List[Image.Image], durations: Union[int, List[int]]) -> Tuple[Image.Image, dict]:
        """If the image is a GIF, create an its thumbnail here."""
        save_kwargs = {}
        new_images: List[Image.Image] = []

        for frame in images:
            thumbnail = frame.copy()  # type: Image
            thumbnail_rgba = thumbnail.convert(mode='RGBA')
            thumbnail_rgba.thumbnail(size=frame.size, reducing_gap=3.0)
            converter = TransparentAnimatedGifConverter(img_rgba=thumbnail_rgba)
            thumbnail_p = converter.process()  # type: Image
            new_images.append(thumbnail_p)

        output_image = new_images[0]
        save_kwargs.update(
            format='GIF',
            save_all=True,
            optimize=False,
            append_images=new_images[1:],
            duration=durations,
            disposal=2,  # Other disposals don't work
            loop=0)
        return output_image, save_kwargs


    def save_transparent_gif(self, images: List[Image.Image], durations: Union[int, List[int]], save_file):
        root_frame, save_args = self._create_animated_gif(images, durations)
        root_frame.save(save_file, **save_args)

    def resize(self, image: Image) -> Image:
        if image.height > 500 or image.width > 500:
            resized = image.resize((480, 480), resample=Image.BICUBIC, reducing_gap=2)
            image.close()
            return resized
        return image
    
    def open_pil_image(self, buffer: BytesIO) -> Image:
        try:
            return Image.open(buffer, "RGBA")
        except:
            try:
                return Image.open(buffer, "RGB")
            except:
                return Image.open(buffer)

    def run_polaroid(self, image1, method, *args, **kwargs):
        # image1 = self.resize(BytesIO(image1))
        img = self.open_pil_image(BytesIO(image1))
        if (
            img.is_animated
            and img.n_frames < 200
        ):
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
                b.flush()
                del p_image
            final = BytesIO()
            self.save_transparent_gif(to_make_gif, img.info["duration"], final)
            for i in to_process:
                i.flush()
                del i
            for i in to_make_gif:
                i.close()
                del i
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
        del im
        i.close()
        del i
        image1.flush()
        del image1
        return discord.File(b, filename=f"{method}.png")

    async def polaroid_(self, image, method, *args, **kwargs):
        async with self.bot.session.get(image) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        f = functools.partial(
            self.run_polaroid, image1, method, *args, **kwargs
        )
        result = await self.bot.loop.run_in_executor(e, f)
        e.shutdown()
        return result

    @staticmethod
    def circle__(background_color, circle_color):
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
                fobj.flush()
                del fobj
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
            del i
        return igif

    def process_gif(self, image, function, *args):
        img = self.open_pil_image(BytesIO(image))
        if (
            img.is_animated
            and img.n_frames < 200
        ):
            to_make_gif = []
            for im in ImageSequence.Iterator(img):
                im_ = self.resize(im)
                im_ = im_.convert("RGBA")
                im_final = function(im_, *args)
                to_make_gif.append(im_final)
            final = BytesIO()
            self.save_transparent_gif(to_make_gif, img.info["duration"], final)
            for i in to_make_gif:
                i.close()
                del i
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
        
    def spin__(self, image, speed):
        im = self.open_pil_image(BytesIO(image))
        im = self.resize(im)
        im = im.convert("RGBA")
        to_make_gif = [im.rotate(degree, resample=Image.BICUBIC, expand=0) for degree in range(0, 360, 10)]
        final = BytesIO()
        self.save_transparent_gif(to_make_gif, speed, final)
        final.seek(0)
        return final, "gif"
        
    async def spin_(self, url, speed):
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        f = functools.partial(self.spin__, image1, speed)
        result, format_ = await self.bot.loop.run_in_executor(e, f)
        e.shutdown()
        result = discord.File(result, f"The_Anime_Bot_spin.{format_}")
        return result

    async def mirror_(self, url):
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        f = functools.partial(self.process_gif, image1, ImageOps.mirror)
        result, format_ = await self.bot.loop.run_in_executor(e, f)
        e.shutdown()
        result = discord.File(result, f"The_Anime_Bot_mirror.{format_}")
        return result

    async def flip_(self, url):
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        f = functools.partial(self.process_gif, image1, ImageOps.flip)
        result, format_ = await self.bot.loop.run_in_executor(e, f)
        e.shutdown()
        result = discord.File(result, f"The_Anime_Bot_flip.{format_}")
        return result

    async def grayscale_(self, url):
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        f = functools.partial(self.process_gif, image1, ImageOps.grayscale)
        result, format_ = await self.bot.loop.run_in_executor(e, f)
        e.shutdown()
        result = discord.File(result, f"The_Anime_Bot_grayscale.{format_}")
        return result

    async def posterize_(self, url):
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        f = functools.partial(self.process_gif, image1, ImageOps.posterize, 3)
        result, format_ = await self.bot.loop.run_in_executor(e, f)
        e.shutdown()
        result = discord.File(result, f"The_Anime_Bot_posterize.{format_}")
        return result

    async def solarize_(self, url):
        async with self.bot.session.get(url) as resp:
            image1 = await resp.read()
        e = ThreadPoolExecutor(max_workers=5)
        result, format_ = await self.bot.loop.run_in_executor(
            e, self.process_gif, image1, ImageOps.solarize
        )
        e.shutdown()
        result = discord.File(result, f"The_Anime_Bot_solarize.{format_}")
        return result

    async def circle_(self, background_color, circle_color):
        e = ThreadPoolExecutor(max_workers=5)
        result = await self.bot.loop.run_in_executor(
            e, self.circle__, background_color, circle_color
        )
        e.shutdown()
        return result

    @asyncexe()
    def qr_enc(self, thing):
        q = qrcode.make(thing, image_factory=PymagingImage)
        pic = BytesIO()
        q.save(pic)
        pic.seek(0)
        return pic

    @asyncexe()
    def qr_dec(self, bytes_):
        with Image.open(bytes_) as img:
            return decode(img)[0].data.decode("utf-8")
       
    def process_latex(self, buffer):
        with Image.open(buffer) as img:
            img_ = img.convert("RGBA")
            im__ = img_.filter(ImageFilter.SMOOTH_MORE)
            _im_ = im__.filter(ImageFilter.DETAIL)
            enhancer = ImageEnhance.Sharpness(_im_)
            im_ = enhancer.enhance(2)
            im__.close()
            img_.close()
            _im_.close()
            b = BytesIO()
            im_.save(b, "PNG",  dpi=(1000, 1000))
            b.seek(0)
            im_.close()
            return b
    
    @asyncexe()
    def facereg_(self, image):
        np_array = np.asarray(bytearray(image.read()), dtype=np.uint8)
        img = cv2.imdecode(np_array, cv2.IMREAD_COLOR)
        gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        haar_face_cascade = cv2.CascadeClassifier("/usr/local/lib/python3.9/site-packages/cv2/data/haarcascade_frontalface_alt_tree.xml")
        faces = haar_face_cascade.detectMultiScale(gray_img, scaleFactor=1.0008, minNeighbors=6)
        for (x, y, w, h) in faces:
            cv2.rectangle(img, (x, y), (x+w, y+h), (0, 255, 0), 2)
        is_success, im_buf_arr = cv2.imencode(".png", img)
        return discord.File(BytesIO(im_buf_arr), "The_Anime_Bot_Face_Reg.png")

    @commands.command()
    async def facereg(self, ctx, thing: Image_Union = None):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            async with self.bot.session.get(url) as resp:
                b = BytesIO(await resp.read())
            await ctx.reply(file=await self.facereg_(b))
    
    @commands.command()
    async def latex(self, ctx, *, text):
        async with self.bot.session.get(f"https://latex.codecogs.com/png.latex?%5Cdpi%7B300%7D%20%5Chuge%20{quote(text)}") as resp:
            await ctx.send(embed=discord.Embed(title="LaTeX", color=self.bot.color).set_image(url="attachment://The_Anime_Bot_latex.png"), file=discord.File(BytesIO(await resp.read()), "The_Anime_Bot_latex.png"))
            
    @commands.command()
    async def spin(
        self,
        ctx,
        thing: Image_Union = None
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            await ctx.reply(file=await self.spin_(url, 64))

    @commands.group(invoke_without_command=True)
    async def qr(self, ctx, *, thing):
        try:
            pic = await self.qr_enc(thing)
        except:
            return await ctx.send("Too big big")
        await ctx.send(file=discord.File(pic, "qrcode.png"))

    @qr.command(name="decode")
    async def qr_decode(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        url = await self.get_url(ctx, thing)
        async with self.bot.session.get(url) as resp:
            bytes_ = BytesIO(await resp.read())
            try:
                data = await self.qr_dec(bytes_)
            except:
                return await ctx.send("Can't regonize qrcode")
            embed = discord.Embed(color=self.bot.color, description=data)
            await ctx.send(embed=embed)

    @commands.command()
    async def caption(
        self,
        ctx: AnimeContext,
        thing: Image_Union = None,
    ):
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
            await ctx.send(
                embed=embed, file=discord.File(bytes_, "caption.png")
            )

    @commands.command()
    async def botcdn(
        self,
        ctx: AnimeContext,
        thing: Image_Union = None,
    ):
        url = await self.get_gif_url(ctx, thing)
        await ctx.send(f"{await self.bot_cdn(url)}")

    @commands.command()
    async def cdn(
        self,
        ctx: AnimeContext,
        thing: Image_Union = None,
    ):
        url = await self.get_gif_url(ctx, thing)
        await ctx.send(f"<{await self.cdn_(url)}>")

    @commands.command()
    async def ocr(
        self,
        ctx: AnimeContext,
        thing: Image_Union = None,
    ):
        url = await self.get_url(ctx, thing)
        await ctx.send(f"```\n{await self.ocr_(url)}\n```")

    @commands.command()
    async def aww(self, ctx):
        async with self.bot.session.get(
            "https://api.ksoft.si/images/random-aww",
            headers={"Authorization": authorizationthing},
        ) as resp:
            res = await resp.json()
            link = res.get("image_url")
            async with self.bot.session.get(link) as resp:
                buffer = BytesIO(await resp.read())
        await ctx.send(file=discord.File(buffer, "aww.png"))

    @commands.command()
    async def womancat(
        self,
        ctx: AnimeContext,
        woman: typing.Optional[
            Image_Union
        ],
        cat: typing.Optional[
            Image_Union
            ]
    ):
        url = await self.get_url(ctx, woman)
        url1 = await self.get_url(ctx, cat)
        pic = await self.bot.vacefron_api.woman_yelling_at_cat(
            woman=url, cat=url1
        )
        await ctx.send(
            file=discord.File(
                await pic.read(), filename=f"woman_yelling_at_cat.png"
            )
        )

    @commands.command()
    async def circle(
        self, ctx: AnimeContext, background_color="white", circle_color="blue"
    ):
        igif = await self.circle_(background_color, circle_color)
        await ctx.send(file=discord.File(igif, "circle.gif"))

    @commands.command()
    async def npc(
        self,
        ctx,
        text1: str = "You gotta enter something",
        text2: str = "yeye",
    ):
        pic = await self.bot.vacefron_api.npc(text1, text2)
        await ctx.send(
            file=discord.File(
                await pic.read(), filename=f"npc_{text1}_{text2}.png"
            )
        )

    @commands.command()
    async def amongus(
        self, ctx, name: str = "you", color: str = "red", imposter: bool = True
    ):
        pic = await self.bot.vacefron_api.ejected(name, color, imposter)
        await ctx.send(
            file=discord.File(
                await pic.read(),
                filename=f"among_us_{name}_{color}_{imposter}.png",
            )
        )

    @commands.command()
    async def randompicture(self, ctx: AnimeContext, *, seed: str = None):
        if seed:
            async with self.bot.session.get(
                f"https://picsum.photos/seed/{seed}/3840/2160"
            ) as resp:
                pic = BytesIO(await resp.read())
        else:
            async with self.bot.session.get(
                "https://picsum.photos/3840/2160"
            ) as resp:
                pic = BytesIO(await resp.read())
        await ctx.send(file=discord.File(pic, filename="randompicture.png"))

    @commands.command()
    async def dym(self, ctx: AnimeContext, up, bottom):
        """
        Google do you mean picture
        Usage: ovo dym \"anime bot is bad bot\" \"anime bot is good bot\"
        """
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.didyoumean(up, bottom)).read(),
            "alex.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def gradiant(self, ctx):
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.colour_image_gradient()).read(),
            "alex.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def amiajoke(
        self,
        ctx,
        thing: typing.Optional[
            Image_Union
            ],
        level: float = 0.3,
    ):
        async with ctx.channel.typing():
            level = min(level, 1)
            url = await self.get_url(ctx, thing)
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.amiajoke(url)).read(), "alex.png"
        )
        await ctx.send(embed=embed, file=image)

    @commands.group(invoke_without_command=True)
    async def supreme(
        self, ctx: AnimeContext, *, text: str = "enter something here"
    ):
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.supreme(text=text)).read(), "alex.png"
        )
        await ctx.send(embed=embed, file=image)

    @supreme.command(name="dark")
    async def supreme_dark(
        self, ctx: AnimeContext, *, text: str = "enter something here"
    ):
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.supreme(text=text, dark=True)).read(),
            "alex.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def archive(self, ctx: AnimeContext, *, text):
        embed = discord.Embed(color=0x00FF6A).set_image(
            url="attachment://alex.png"
        )
        image = discord.File(
            await (await self.bot.alex.achievement(text=text)).read(),
            "alex.png",
        )
        await ctx.send(embed=embed, file=image)

    @commands.command()
    async def pixelate(
        self,
        ctx,
        thing: typing.Optional[
            Image_Union
            ],
        level: float = 0.3,
    ):
        async with ctx.channel.typing():
            level = min(level, 1)
            url = await self.get_url(ctx, thing)
            try:
                image = await self.bot.zaneapi.pixelate(url, level)
            except asyncio.TimeoutError:
                raise commands.CommandError("Zaneapi timeout")
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://pixelate.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="pixelate.png"),
                embed=embed,
            )

    @commands.command()
    async def swirl(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            try:
                image = await self.bot.zaneapi.swirl(url)
            except asyncio.TimeoutError:
                raise commands.CommandError("Zaneapi timeout")
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://swirl.gif"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="swirl.gif"), embed=embed
            )

    @commands.command()
    async def sobel(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.sobel(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://sobel.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="sobel.png"), embed=embed
            )

    @commands.command()
    async def palette(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.palette(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://palette.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="palette.png"),
                embed=embed,
            )

    @commands.command()
    async def sort(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.sort(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://sort.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="sort.png"), embed=embed
            )

    @commands.command()
    async def cube(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            try:
                image = await self.bot.zaneapi.cube(url)
            except asyncio.TimeoutError:
                raise commands.CommandError("Zaneapi timeout")
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://cube.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="cube.png"), embed=embed
            )

    @commands.command()
    async def braille(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.braille(url)
            await ctx.send(image)

    @commands.command(aliases=["dot"])
    async def dots(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.dots(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://dots.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="dots.png"), embed=embed
            )

    @commands.command()
    async def threshold(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.threshold(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://threshold.png"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="threshold.png"),
                embed=embed,
            )

    @commands.command()
    async def spread(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.spread(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://spread.gif"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="spread.gif"), embed=embed
            )

    @commands.command()
    async def jpeg(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.jpeg(url)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://jpeg.gif"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="jpeg.gif"), embed=embed
            )

    @commands.command(aliases=["magik"])
    async def magic(
        self,
        ctx,
        thing: typing.Optional[
            Image_Union
            ],
        level: float = 0.6,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.magic(url, level)
            embed = discord.Embed(color=0x00FF6A).set_image(
                url="attachment://magic.gif"
            )
            await ctx.send(
                file=discord.File(fp=image, filename="magic.gif"), embed=embed
            )

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
    #     async with ctx.channel.typing():
    #         if not thing:
    #             url = await self.get_url(ctx, thing)
    #             image = await self.bot.zaneapi.floor(url)
    #             embed = discord.Embed(color=0x00FF6A).set_image(
    #                 url="attachment://floor.gif"
    #             )
    #             return await ctx.send(
    #                 file=discord.File(fp=image, filename="floor.gif"),
    #                 embed=embed,
    #             )

    #         if len(thing) > 10:
    #             return await ctx.send("the max is 10")
    #         for i in thing:
    #             url = await self.get_url(ctx, i)
    #             image = await self.bot.zaneapi.floor(url)
    #             embed = discord.Embed(color=0x00FF6A).set_image(
    #                 url="attachment://floor.gif"
    #             )
    #             await ctx.send(
    #                 file=discord.File(fp=image, filename="floor.gif"),
    #                 embed=embed,
    #             )

    @commands.command()
    async def noise(self, ctx):
        stat_ = await self.image(
            ctx,
            await ctx.author.avatar_url_as(format="png").read(),
            "add_noise_rand",
        )

    @commands.command(aliases=["wtp"])
    async def pokemon(self, ctx):
        await ctx.trigger_typing()
        wtp = await self.bot.dag.wtp()
        tried = 3
        if ctx.author.id == 590323594744168494:
            await ctx.author.send(wtp.name)
        embed = discord.Embed(color=0x2ECC71)
        ability = "".join(wtp.abilities)
        embed.set_author(name=f"{ctx.author} has {tried} tries")
        embed.add_field(name="pokemon's ability", value=ability)
        embed.set_image(url=wtp.question)
        message = await ctx.send(embed=embed)

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
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            text1 = text
        img = await self.bot.dag.image_process(
            ImageFeatures.captcha(), url, text=text1
        )
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def solarize(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
            file = await self.solarize_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def invert(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
        await ctx.reply(file=await self.polaroid_(url, "invert"))

    @commands.command()
    async def oil(
        self,
        ctx,
        thing: typing.Optional[
            Image_Union
            ],
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
        await ctx.reply(file=await self.polaroid_(url, "oil", 3, 10))

    @commands.command()
    async def rainbow(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
        await ctx.reply(file=await self.polaroid_(url, "apply_gradient"))

    @commands.command()
    async def awareness(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.paint(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def polaroid(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.polaroid(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def sepia(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.sepia(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)

    @commands.command()
    async def posterize(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
            file = await self.posterize_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def mirror(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
            file = await self.mirror_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def flip(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
            file = await self.flip_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def grayscale(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_gif_url(ctx, thing)
            file = await self.grayscale_(url)
            await ctx.reply(file=file)

    @commands.command()
    async def ascii(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
        img = await self.bot.dag.image_process(ImageFeatures.pixel(), url)
        file = discord.File(fp=img.image, filename=f"pixel.{img.format}")
        await ctx.reply(file=file)


def setup(bot):
    bot.add_cog(pictures(bot))
