import discord
from discord.ext import commands
import asyncio
import humanize
import datetime
import wavelink

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
        self.loop = False
        self.queue = []
        self.queue_position = 0
    
    def make_embed(self, track):
        embed = discord.Embed(color=0x00ff6a, title="Now playing", description=f"now playing: **{track.title}**")
        embed.set_thumbnail(url=track.thumb) if track.thumb else ...
        embed.add_field(name="requester", value=track.requester)
        embed.add_field(name='Duration', value=humanize.precisedelta(datetime.timedelta(milliseconds=int(track.length))))
        embed.add_field(name="youtube link", value=track.uri) if track.uri else ...
        embed.add_field(name="author", value=track.author) if track.author else ...
        return embed


    async def start(self, ctx, song):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not player.is_connected:
            await ctx.invoke(self.connect_)
        if isinstance(song, wavelink.TrackPlaylist):
            for track in song.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                self.queue.append(track)
            self.now_playing = song.tracks[0]
        else:
            track = Track(song[0].id, song[0].info, requester=ctx.author)
            self.queue.append(track)
            self.now_playing = track

        await ctx.send(embed=self.make_embed(track))
        self.queue_position += 1
        await self.play(self.now_playing)
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
        await ctx.send(embed=self.make_embed(song))

        await self.play(song)


class Music(commands.Cog, wavelink.WavelinkMixin):
    def __init__(self, bot):
        self.bot = bot
        if not hasattr(bot, "wavelink"):
            self.bot.wavelink = wavelink.Client(bot=self.bot)

        self.bot.loop.create_task(self.start_nodes())

    def cog_unload(self):
        for i in self.bot.wavelink.players.values():
            await i.destory()

    async def start_nodes(self):
        await self.bot.wait_until_ready()
        await self.bot.wavelink.initiate_node(host="0.0.0.0",
                                              port=2333,
                                              rest_uri="http://0.0.0.0:2333",
                                              password="youshallnotpass",
                                              identifier="MAIN",
                                              region="us_central")
    async def on_node_event(self, event):
        if isinstance(event, (wavelink.TrackEnd, wavelink.on_track_stuck, wavelink.TrackException)):
            await event.player.do_next()

    async def cog_check(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not ctx.guild:
            raise commands.NoPrivateMessage
        if not player.is_connected:
            return True
        if not ctx.author.voice:
            await ctx.send("You must be in a voice channel to use this command.")
            return False
        if ctx.author.voice.channel.id != player.channel_id:
            await ctx.send("You must be in the same voice channel as me to use this command.")
            return False
        return True

    @commands.command()
    async def join(self, ctx, vc: discord.VoiceChannel = None):
        if not vc:
            if ctx.author.voice:
                channel = ctx.author.voice.channel
            else:
                return await ctx.send("you are not connected to any voice channel")
        else:
            channel = vc
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.connect(channel.id)
        await ctx.send(f"Connected to {channel.name}")

    @commands.command()
    async def loop(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if player.loop:
            player.loop = False
            return await ctx.send("unlooped")
        player.loop = True
        await ctx.send("looped")

    @commands.command()
    async def fastforward(self, ctx, seconnds:int):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        seek_position = player.position + (seconds * 1000)
        await player.seek(seek_position)
        await ctx.send(f"Fast forwarded {seconds} Current position: {humanize.precisedelta(datetime.timedelta(milliseconds=10))}")


    @commands.command()
    async def leave(self, ctx):
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.destory()
        await ctx.send("disconnected")

    @commands.command()
    async def equalizer(self, ctx, name:lambda x: x.lower()):
        equalizers = {
            "none": wavelink.Equalizer.flat(),
            "boost": wavelink.Equalizer.boost(),
            "metal": wavelink.Equalizer.metal(),
            "piano": wavelink.Equalizer.piano()
        }
        if not name in equalizers.keys():
            return await ctx.send("""
                `none` - Resets the equalizer
                `boost` - Boost equalizer. This equalizer emphasizes punchy bass and crisp mid-high tones. Not suitable for tracks with deep/low bass.
                `metal` - Experimental metal/rock equalizer. Expect clipping on bassy songs.
                `piano` - Piano equalizer. Suitable for piano tracks, or tacks with an emphasis on female vocals. Could also be used as a bass cutoff.
                From https://wavelink.readthedocs.io/en/latest/wavelink.html#equalizer
            """)

        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        await player.set_eq(equalizers.get(name))
        await player.seek(1)
        await ctx.send(f"equalizer setted to {name}")

    @commands.command()
    async def play(self, ctx, *, music):
        tracks = await self.bot.wavelink.get_tracks(f'ytsearch:{music}')

        if not tracks:
            return await ctx.send('Could not find any songs with that query. maybe you made a typo?')
        player = self.bot.wavelink.get_player(ctx.guild.id, cls=Player)
        if not player.is_connected:
            await ctx.invoke(self.join)
        if not player.started:
            return await player.start(ctx, tracks)
        if isinstance(tracks, wavelink.TrackPlaylist):
            for track in tracks.tracks:
                track = Track(track.id, track.info, requester=ctx.author)
                player.queue.append(track)
            playlist_name = tracks.data['playlistInfo']['name']
            await ctx.send(f"Added playlist `{playlist_name}` with `{len(tracks.tracks)}` songs to the queue. ")
        else:
            track = Track(tracks[0].id, tracks[0].info, requester=ctx.author)
            player.queue.append(track)
            await ctx.send(f"Added `{track}` to the queue.")

    @commands.command()
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