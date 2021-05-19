import discord
from discord.ext import commands
from colormath.color_objects import sRGBColor, XYZColor
from colormath.color_conversions import convert_color
import colorsys
from scipy.spatial import KDTree
from webcolors import (
    CSS3_HEX_TO_NAMES,
    hex_to_rgb,
)
from colordict import ColorDict

colors = ColorDict()
from wand.resource import limits
from wand.image import Image as WandImage
from copy import copy
import pytesseract
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
from PIL import ImageColor
from PIL import Image, ImageDraw, ImageFilter
from PIL import ImageEnhance
from PIL import ImageSequence
from PIL import ImageOps
from io import BytesIO
from asyncdagpi import ImageFeatures
import typing

RGB_SCALE = 255
CMYK_SCALE = 100

limits["width"] = 1000
limits["height"] = 1000
limits["thread"] = 10

warnings.simplefilter("error", Image.DecompressionBombWarning)
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


class ColorConverter(commands.Converter):
    async def convert(self, ctx, argument):
        converter = commands.ColourConverter()
        try:
            color = await converter.convert(ctx, argument)
            color = color.to_rgb()
        except commands.BadColourArgument:
            try:
                color = colors[argument]
            except KeyError:
                try:
                    color = ImageColor.getrgb(argument)
                except ValueError:
                    raise commands.BadArgument
        return tuple((int(i) for i in color))


class TransparentAnimatedGifConverter(object):
    _PALETTE_SLOTSET = set(range(256))

    def __init__(self, img_rgba: Image.Image, alpha_threshold: int = 0):
        self._img_rgba = img_rgba
        self._alpha_threshold = alpha_threshold

    def _process_pixels(self):
        """Set the transparent pixels to the color 0."""
        self._transparent_pixels = {
            idx
            for idx, alpha in enumerate(self._img_rgba.getchannel(channel="A").getdata())
            if alpha <= self._alpha_threshold
        }

    def _set_parsed_palette(self):
        """Parse the RGB palette color `tuple`s from the palette."""
        palette = self._img_p.getpalette()
        self._img_p_used_palette_idxs = {
            idx for pal_idx, idx in enumerate(self._img_p_data) if pal_idx not in self._transparent_pixels
        }

        self._img_p_parsedpalette = {
            idx: tuple(palette[idx * 3 : idx * 3 + 3]) for idx in self._img_p_used_palette_idxs
        }

    def _get_similar_color_idx(self):
        """Return a palette index with the closest similar color."""
        old_color = self._img_p_parsedpalette[0]
        dict_distance = defaultdict(list)
        for idx in range(1, 256):
            color_item = self._img_p_parsedpalette[idx]
            if color_item == old_color:
                return idx
            distance = sum(
                (
                    abs(old_color[0] - color_item[0]),  # Red
                    abs(old_color[1] - color_item[1]),  # Green
                    abs(old_color[2] - color_item[2]),
                )
            )  # Blue
            dict_distance[distance].append(idx)
        return dict_distance[sorted(dict_distance)[0]][0]

    def _remap_palette_idx_zero(self):
        """Since the first color is used in the palette, remap it."""
        free_slots = self._PALETTE_SLOTSET - self._img_p_used_palette_idxs
        new_idx = free_slots.pop() if free_slots else self._get_similar_color_idx()
        self._img_p_used_palette_idxs.add(new_idx)
        self._palette_replaces["idx_from"].append(0)
        self._palette_replaces["idx_to"].append(new_idx)
        self._img_p_parsedpalette[new_idx] = self._img_p_parsedpalette[0]
        del self._img_p_parsedpalette[0]

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
        if self._palette_replaces["idx_from"]:
            trans_table = bytearray.maketrans(
                bytes(self._palette_replaces["idx_from"]),
                bytes(self._palette_replaces["idx_to"]),
            )
            self._img_p_data = self._img_p_data.translate(trans_table)
        for idx_pixel in self._transparent_pixels:
            self._img_p_data[idx_pixel] = 0
        self._img_p.frombytes(data=bytes(self._img_p_data))

    def _adjust_palette(self):
        """Modify the palette in the new `Image`."""
        unused_color = self._get_unused_color()
        final_palette = chain.from_iterable(self._img_p_parsedpalette.get(x, unused_color) for x in range(256))
        self._img_p.putpalette(data=final_palette)

    def process(self) -> Image.Image:
        """Return the processed mode `P` `Image`."""
        self._img_p = self._img_rgba.convert(mode="P")
        self._img_p_data = bytearray(self._img_p.tobytes())
        self._palette_replaces = dict(idx_from=list(), idx_to=list())
        self._process_pixels()
        self._process_palette()
        self._adjust_pixels()
        self._adjust_palette()
        self._img_p.info["transparency"] = 0
        self._img_p.info["background"] = 0
        return self._img_p


class pictures(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.bot_cdn_ratelimiter = ratelimiter.RateLimiter(max_calls=1, period=6)
        self.cdn_ratelimiter = ratelimiter.RateLimiter(max_calls=3, period=7)
        self.ocr_ratelimiter = ratelimiter.RateLimiter(max_calls=2, period=10)


    async def get_url(self, ctx: AnimeContext, thing, **kwargs):
        url = None
        avatar = kwargs.get("avatar", True)
        check = kwargs.get("check", True)
        is_gif = kwargs.get("gif", False)
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

        if ctx.message.attachments and ctx.message.attachments[0].width and ctx.message.attachments[0].height:
            url = ctx.message.attachments[0].url
        if ctx.message.stickers:
            sticker = ctx.message.stickers[0]
            if sticker.format != discord.StickerType.lottie:
                url = str(sticker.image_url_as())
        if thing is None and avatar and url is None:
            if gif:
                url = str(ctx.author.avatar_url_as(static_format="png"))
            else:
                url = str(ctx.author.avatar_url_as(format="png"))
        elif isinstance(thing, (discord.PartialEmoji, discord.Emoji)):
            if gif:
                url = str(thing.url_as(static_format="png"))
            else:
                url = str(thing.url_as(format="png"))
        elif isinstance(thing, (discord.Member, discord.User)):
            if gif:
                url = str(thing.avatar_url_as(static_format="png"))
            else:
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
                if b.startswith(b"\x89\x50\x4E\x47\x0D\x0A\x1A\x0A"):
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
                    raise discord.InvalidArgument("Unsupported image type given")
                if resp.headers.get("Content-Length") and int(resp.headers.get("Content-Length")) > 10000000:
                    raise discord.InvalidArgument("Image Larger then 10 MB")
        return url

    def get_gif_url(self, ctx: AnimeContext, thing, **kwargs):
        return self.get_url(ctx, thing, gif=True, **kwargs)

    async def bot_cdn(self, url):
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

    async def cdn_(self, url):
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

    def _create_animated_gif(
        self, images: List[Image.Image], durations: Union[int, List[int]]
    ) -> Tuple[Image.Image, dict]:
        """If the image is a GIF, create an its thumbnail here."""
        save_kwargs = {}
        new_images: List[Image.Image] = []

        for frame in images:
            thumbnail = frame.copy()  # type: Image
            thumbnail_rgba = thumbnail.convert(mode="RGBA")
            thumbnail_rgba.thumbnail(size=frame.size, reducing_gap=3.0)
            converter = TransparentAnimatedGifConverter(img_rgba=thumbnail_rgba)
            thumbnail_p = converter.process()  # type: Image
            new_images.append(thumbnail_p)

        output_image = new_images[0]
        save_kwargs.update(
            format="GIF",
            save_all=True,
            optimize=False,
            append_images=new_images[1:],
            duration=durations,
            disposal=2,  # Other disposals don't work
            loop=0,
        )
        return output_image, save_kwargs

    def save_transparent_gif(self, images: List[Image.Image], durations: Union[int, List[int]], save_file):
        root_frame, save_args = self._create_animated_gif(images, durations)
        root_frame.save(save_file, **save_args)
        root_frame.close()
        for i in images:
            i.close()

    def resize(self, image: Image) -> Image:
        if image.height > 500 or image.width > 500:
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
            resized = image.resize(size, resample=Image.NEAREST, reducing_gap=1)
            # image.close()
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
        f = functools.partial(self.run_polaroid, image1, method, *args, **kwargs)
        result = await self.bot.loop.run_in_executor(None, f)
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
        if img.is_animated and img.n_frames < 200:
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
        result, format_ = await self.bot.loop.run_in_executor(e, self.process_gif, image1, ImageOps.solarize)
        e.shutdown()
        result = discord.File(result, f"The_Anime_Bot_solarize.{format_}")
        return result

    async def circle_(self, background_color, circle_color):
        e = ThreadPoolExecutor(max_workers=5)
        result = await self.bot.loop.run_in_executor(e, self.circle__, background_color, circle_color)
        e.shutdown()
        return result

    @asyncexe()
    def floor_(self, b):
        with WandImage(file=b) as img_:
            with WandImage(img_.sequence[0]) as img:
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
            im_.save(b, "PNG", dpi=(1000, 1000))
            b.seek(0)
            im_.close()
            return b

    @asyncexe()
    def facereg_(self, image):
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
        del np_array
        del img
        del gray_img
        del haar_face_cascade
        del eye_cascade
        del smile_cascade
        del faces
        b = BytesIO(im_buf_arr)
        del im_buf_arr
        return discord.File(b, "The_Anime_Bot_Face_Reg.png")

    @asyncexe()
    def make_color_image(self, color):
        with Image.new("RGB", (200, 200), color) as img:
            b = BytesIO()
            img.save(b, "PNG")
            b.seek(0)
            return b

    def rgb_to_hsv(self, r, g, b):
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

    def rgb_to_xy_bri(self, r, g, b):
        r, g, b = r / 255.0, g / 255.0, b / 255.0
        o = (
            (0.412453 * r + 0.35758 * g + 0.180423 * b),
            (0.212671 * r + 0.71516 * g + 0.072169 * b),
            (0.019334 * r + 0.119193 * g + 0.950227 * b),
        )
        return tuple((round(i * 100) for i in o))

    def rgb_to_hsl(self, r, g, b):
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
        l = ((mx + mn) / 2) * 100
        return f"({round(h)}, {round(s)}%, {round(l)}%)"

    def rgb_to_cmyk(self, rgb_tuple):
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

    @asyncexe()
    def convert_rgb_to_names(self, rgb_tuple):
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
    async def colorinfo(self, ctx, *, color: ColorConverter):
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
    async def floor(self, ctx, thing: Image_Union = None):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            async with self.bot.session.get(url) as resp:
                b = BytesIO(await resp.read())
            await ctx.reply(file=discord.File(await self.floor_(b), "The_Anime_Bot_floor.png"))

    @commands.command()
    async def facereg(self, ctx, thing: Image_Union = None):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            async with self.bot.session.get(url) as resp:
                b = BytesIO(await resp.read())
            await ctx.reply(file=await self.facereg_(b))

    @commands.command()
    async def latex(self, ctx, *, text):
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
    async def spin(self, ctx, thing: Image_Union = None):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            await ctx.reply(file=await self.spin_(url, 64))

    @commands.group(invoke_without_command=True)
    async def qr(self, ctx, *, thing):
        try:
            pic = await self.qr_enc(thing)
        except:
            return await ctx.reply("Too big big")
        await ctx.reply(file=discord.File(pic, "qrcode.png"))

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
                return await ctx.reply("Can't regonize qrcode")
            embed = discord.Embed(color=self.bot.color, description=data)
            await ctx.reply(embed=embed)

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
            await ctx.reply(embed=embed, file=discord.File(bytes_, "caption.png"))

    @commands.command()
    async def botcdn(
        self,
        ctx: AnimeContext,
        thing: Image_Union = None,
    ):
        url = await self.get_gif_url(ctx, thing)
        await ctx.reply(f"{await self.bot_cdn(url)}")

    @commands.command()
    async def cdn(
        self,
        ctx: AnimeContext,
        thing: Image_Union = None,
    ):
        url = await self.get_gif_url(ctx, thing)
        await ctx.reply(f"<{await self.cdn_(url)}>")

    @asyncexe()
    def ocr_(self, image):
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
        url = await self.get_url(ctx, thing)
        async with self.bot.session.get(url) as resp:
            image = BytesIO(await resp.read())
        await ctx.reply(f"```\n{await self.ocr_(image)}\n```") if len(
            f"```\n{await self.ocr_(image)}\n```"
        ) <= 2000 else await ctx.reply(await ctx.paste(f"```\n{await self.ocr_(image)}\n```"))

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
        await ctx.reply(file=discord.File(buffer, "aww.png"))

    @commands.command()
    async def womancat(
        self,
        ctx: AnimeContext,
        woman: typing.Optional[Image_Union],
        cat: typing.Optional[Image_Union],
    ):
        url = await self.get_url(ctx, woman)
        url1 = await self.get_url(ctx, cat)
        pic = await self.bot.vacefron_api.woman_yelling_at_cat(woman=url, cat=url1)
        await ctx.reply(file=discord.File(await pic.read(), filename=f"woman_yelling_at_cat.png"))

    @commands.command()
    async def circle(self, ctx: AnimeContext, background_color="white", circle_color="blue"):
        igif = await self.circle_(background_color, circle_color)
        await ctx.reply(file=discord.File(igif, "circle.gif"))

    @commands.command()
    async def npc(
        self,
        ctx,
        text1: str = "You gotta enter something",
        text2: str = "yeye",
    ):
        pic = await self.bot.vacefron_api.npc(text1, text2)
        await ctx.reply(file=discord.File(await pic.read(), filename=f"npc_{text1}_{text2}.png"))

    @commands.command()
    async def amongus(self, ctx, name: str = "you", color: str = "red", imposter: bool = True):
        pic = await self.bot.vacefron_api.ejected(name, color, imposter)
        await ctx.reply(
            file=discord.File(
                await pic.read(),
                filename=f"among_us_{name}_{color}_{imposter}.png",
            )
        )

    @commands.command()
    async def randompicture(self, ctx: AnimeContext, *, seed: str = None):
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
        embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://alex.png")
        image = discord.File(
            await (await self.bot.alex.didyoumean(up, bottom)).read(),
            "alex.png",
        )
        await ctx.reply(embed=embed, file=image)

    @commands.command()
    async def gradiant(self, ctx):
        embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://alex.png")
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
        async with ctx.channel.typing():
            level = min(level, 1)
            url = await self.get_url(ctx, thing)
        embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://alex.png")
        image = discord.File(await (await self.bot.alex.amiajoke(url)).read(), "alex.png")
        await ctx.reply(embed=embed, file=image)

    @commands.group(invoke_without_command=True)
    async def supreme(self, ctx: AnimeContext, *, text: str = "enter something here"):
        embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://alex.png")
        image = discord.File(await (await self.bot.alex.supreme(text=text)).read(), "alex.png")
        await ctx.reply(embed=embed, file=image)

    @supreme.command(name="dark")
    async def supreme_dark(self, ctx: AnimeContext, *, text: str = "enter something here"):
        embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://alex.png")
        image = discord.File(
            await (await self.bot.alex.supreme(text=text, dark=True)).read(),
            "alex.png",
        )
        await ctx.reply(embed=embed, file=image)

    @commands.command()
    async def archive(self, ctx: AnimeContext, *, text):
        embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://alex.png")
        image = discord.File(
            await (await self.bot.alex.achievement(text=text)).read(),
            "alex.png",
        )
        await ctx.reply(embed=embed, file=image)

    @commands.command()
    async def pixelate(
        self,
        ctx,
        thing: typing.Optional[Image_Union],
        level: float = 0.3,
    ):
        async with ctx.channel.typing():
            level = min(level, 1)
            url = await self.get_url(ctx, thing)
            try:
                image = await self.bot.zaneapi.pixelate(url, level)
            except asyncio.TimeoutError:
                raise commands.CommandError("Zaneapi timeout")
            embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://pixelate.png")
            await ctx.reply(
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
            embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://swirl.gif")
            await ctx.reply(file=discord.File(fp=image, filename="swirl.gif"), embed=embed)

    @commands.command()
    async def sobel(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.sobel(url)
            embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://sobel.png")
            await ctx.reply(file=discord.File(fp=image, filename="sobel.png"), embed=embed)

    @commands.command()
    async def palette(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.palette(url)
            embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://palette.png")
            await ctx.reply(
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
            embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://sort.png")
            await ctx.reply(file=discord.File(fp=image, filename="sort.png"), embed=embed)

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
            embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://cube.png")
            await ctx.reply(file=discord.File(fp=image, filename="cube.png"), embed=embed)

    @commands.command()
    async def braille(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.braille(url)
            await ctx.reply(image)

    @commands.command(aliases=["dot"])
    async def dots(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.dots(url)
            embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://dots.png")
            await ctx.reply(file=discord.File(fp=image, filename="dots.png"), embed=embed)

    @commands.command()
    async def threshold(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.threshold(url)
            embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://threshold.png")
            await ctx.reply(
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
            embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://spread.gif")
            await ctx.reply(file=discord.File(fp=image, filename="spread.gif"), embed=embed)

    @commands.command()
    async def jpeg(
        self,
        ctx,
        thing: Image_Union = None,
    ):
        async with ctx.channel.typing():
            url = await self.get_url(ctx, thing)
            image = await self.bot.zaneapi.jpeg(url)
            embed = discord.Embed(color=0x00FF6A).set_image(url="attachment://jpeg.gif")
            await ctx.reply(file=discord.File(fp=image, filename="jpeg.gif"), embed=embed)
    
    @asyncexe()
    def magic_(self, image: BytesIO, intensity: float):
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
                img.liquid_rescale(width=round(img.width * 0.5), height=round(img.height * 0.5), delta_x=round(intensity * 0.5), rigidity=0)
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
        async with ctx.channel.typing():
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
    #     async with ctx.channel.typing():
    #         if not thing:
    #             url = await self.get_url(ctx, thing)
    #             image = await self.bot.zaneapi.floor(url)
    #             embed = discord.Embed(color=0x00FF6A).set_image(
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
    #             embed = discord.Embed(color=0x00FF6A).set_image(
    #                 url="attachment://floor.gif"
    #             )
    #             await ctx.reply(
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
        async with ctx.channel.typing():
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
        thing: typing.Optional[Image_Union],
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
        async with ctx.channel.typing():
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
        async with ctx.channel.typing():
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
