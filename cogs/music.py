import discord
from discord.ext import commands
from utils.subclasses import AnimeContext
import asyncio
import humanize
import datetime
from menus import menus
import wavelink

class QueueMenuSource(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=10)

    async def format_page(self, menu, entries):
        
        return {
            "embed": discord.Embed(
                color=menu.ctx.bot.color,
                title=f"Music queue",
                description="\n".join([f"[**{i.title}**]({i.uri})\n{i.author or 'no author'}" for i in entries]),
            )
        }



class Track(wavelink.Track):
    __slots__ = ("requester",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args)

        self.requester = kwargs.get("requester")


class Player(wavelink.Player):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.now_playing = None
        self.started = False
        self.is_waiting = True
        self.repeat = False
        self.ctx = None
        self.loop = False
        self.queue = []
        self.queue_position = 0

    def make_embed(self, track):
        embed = discord.Embed(
            color=0x00FF6A,
            title="Now playing",
            description=f"Now playing: **{track.title}**",
        )
        embed.set_thumbnail(url=track.thumb) if track.thumb else ...
        embed.add_field(name="Requester", value=track.requester)
        if track.is_stream:
            embed.add_field(
                name="Duration",
                value="Live Stream"
            )
        else:
            try:
                embed.add_field(
                    name="Duration",
                    value=humanize.precisedelta(
                        datetime.timedelta(milliseconds=track.length)
                    ),
                )
            except:
                embed.add_field(
                    name="Duration",
                    value="Duration too long to display."
                )
        embed.add_field(
            name="URL", value=track.uri
        ) if track.uri else ...
        embed.add_field(
            name="Author", value=track.author
        ) if track.author else ...
        footer = f"Youtube ID: {track.ytid or 'None'} Identifier: {track.identifier or 'None'}"
        embed.set_footer(text=footer)
        return embed

    async def start(self, ctx: AnimeContext, song):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not player.is_connected:
            await ctx.invoke(self.connect_)
        if isinstance(song, wavelink.TrackPlaylist):
            for track in song.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                self.queue.append(track)
            self.now_playing = Track(song.tracks[0].id, song.tracks[0].info, requester=ctx.author)
            playlist_name = song.data["playlistInfo"]["name"]
            await ctx.send(
                f"Added playlist `{playlist_name}` with `{len(song.tracks)}` songs to the queue. "
            )
            
        else:
            track = Track(song[0].id, song[0].info, requester=ctx.author)
            self.queue.append(track)
            self.now_playing = track
            await ctx.send(f"Added `{track}` to the queue.")

        await ctx.send(embed=self.make_embed(Track(self.now_playing.id, self.now_playing.info, requester=ctx.author)))
        self.queue_position += 1
        await self.play(self.now_playing)
        self.ctx = ctx
        self.started = True

    async def do_next(self):
        if self.repeat:
            self.queue_position -= 1

        try:
            song = self.queue[self.queue_position]
        except IndexError:
            if self.loop:
                self.queue_position = 0
                song = self.queue[self.queue_position]
            else:
                await asyncio.sleep(10)
                return await self.destroy()

        self.queue_position += 1

        await self.play(song)
        await self.ctx.send(embed=self.make_embed(song))


class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot=self.bot)

        self.bot.loop.create_task(self.start_nodes())

    def cog_unload(self):
        self.bot.loop.create_task(self.destroy_players())

    async def destroy_players(self):
        for i in self.bot.wavelink.players.values():
            await i.destroy()

    async def start_nodes(self):
        await self.bot.wait_until_ready()
        node = await self.bot.wavelink.initiate_node(
            host="127.0.0.1",
            port=2333,
            rest_uri="http://127.0.0.1:2333",
            password="youshallnotpass",
            identifier="MAIN",
            region="us_central",
        )

    @wavelink.WavelinkMixin.listener("on_track_stuck")
    @wavelink.WavelinkMixin.listener("on_track_end")
    @wavelink.WavelinkMixin.listener("on_track_exception")
    async def on_node_event(self, node, event):
        await event.player.do_next()

    async def cog_check(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not ctx.guild:
            raise commands.NoPrivateMessage
        if not ctx.author.voice:
            await ctx.send(
                "You must be in a voice channel to use this command."
            )
            return False
        if ctx.command.qualified_name in ["play", "join"]:
            return True
        if ctx.author.voice.channel.id != player.channel_id:
            await ctx.send(
                "You must be in the same voice channel as me to use this command."
            )
            return False
        if ctx.command.qualified_name != "play" and player.now_playing is None:
            await ctx.send(
                "Nothing is being played right now."
            )
            return False
        return True
                                       
    @commands.command()
    async def queue(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        pages = menus.MenuPages(
            source=QueueMenuSource(player.queue[player.queue_position:]), delete_message_after=True
        )
        await pages.start(ctx)

    @commands.command(aliases=["np", "currentsong"])
    async def now(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)

        await ctx.send(embed=player.make_embed(player.now_playing))

    @commands.command(aliases=["vol"])
    async def volume(self, ctx: AnimeContext, volume: int = 100):
        if volume < 0 or volume > 100:
            return await ctx.send("volume must be between 0 to 100")
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.set_volume(volume)
        await ctx.send(f"Volume is now {volume}")

    @commands.command()
    async def join(self, ctx: AnimeContext, vc: discord.VoiceChannel = None):
        if not vc:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
            else:
                return await ctx.send(
                    "you are not connected to any voice channel"
                )
        else:
            channel = vc
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.connect(channel.id)
        await ctx.send(f"Connected to {channel.name}")

    @commands.command()
    async def repeat(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if player.repeat:
            player.repeat = False
            return await ctx.send("Unrepeated")
        player.repeat = True
        await ctx.send("Repeating the current song")
                                       
    @commands.command()
    async def loop(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if player.loop:
            player.loop = False
            return await ctx.send("Unlooped")
        player.loop = True
        await ctx.send("looped")

    @commands.command()
    async def fastforward(self, ctx: AnimeContext, seconnds: int):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        seek_position = player.position + (seconds * 1000)
        await player.seek(seek_position)
        await ctx.send(
            f"Fast forwarded {seconds} Current position: {humanize.precisedelta(datetime.timedelta(milliseconds=10))}"
        )

    @commands.command(aliases=["dc", "disconnect", "stop"])
    async def leave(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.destroy()
        await ctx.send("disconnected")

    @commands.command()
    async def equalizer(self, ctx: AnimeContext, name: lambda x: x.lower()):
        equalizers = {
            "none": wavelink.Equalizer.flat(),
            "boost": wavelink.Equalizer.boost(),
            "metal": wavelink.Equalizer.metal(),
            "piano": wavelink.Equalizer.piano(),
        }
        if not name in equalizers.keys():
            return await ctx.send(
                """
                `none` - Resets the equalizer
                `boost` - Boost equalizer. This equalizer emphasizes punchy bass and crisp mid-high tones. Not suitable for tracks with deep/low bass.
                `metal` - Experimental metal/rock equalizer. Expect clipping on bassy songs.
                `piano` - Piano equalizer. Suitable for piano tracks, or tacks with an emphasis on female vocals. Could also be used as a bass cutoff.
                From https://wavelink.readthedocs.io/en/latest/wavelink.html#equalizer
            """
            )

        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.set_eq(equalizers.get(name))
        await player.seek(player.position + 1)
        await ctx.send(f"equalizer setted to {name}")

    @commands.command()
    async def play(self, ctx: AnimeContext, *, music):
        if self.bot.url_regex.fullmatch(music):
            tracks = await self.bot.wavelink.get_tracks(music)
        else:
            tracks = await self.bot.wavelink.get_tracks(f"ytsearch:{music}")

        if not tracks:
            return await ctx.send(
                "Could not find any songs with that query. maybe you made a typo?"
            )
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not player.is_connected:
            await ctx.invoke(self.join)
        if not player.started:
            return await player.start(ctx, tracks)
        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                player.queue.append(track)
            playlist_name = tracks.data["playlistInfo"]["name"]
            await ctx.send(
                f"Added playlist `{playlist_name}` with `{len(tracks.tracks)}` songs to the queue. "
            )
        else:
            track = Track(tracks[0].id, tracks[0].info, requester=ctx.author)
            player.queue.append(track)
            await ctx.send(f"Added `{track}` to the queue.")

    @commands.command(aliases=["resume"])
    async def unpause(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not player.is_paused:
            return await ctx.send("player not paused")
        await player.set_pause(False)
        await ctx.send("unpaused player")

    @commands.command()
    async def skip(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.stop()

    @commands.command()
    async def pause(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if player.is_paused:
            return await ctx.send("player already paused")
        await player.set_pause(True)
        await ctx.send("Paused player")


def setup(bot):
    bot.add_cog(Music(bot))
