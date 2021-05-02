import discord
from datetime import datetime

class embedbase:
  async def embed(self, ctx):
    embed = discord.Embed(color=ctx.bot.color, timestamp=datetime.utcnow())
    embed.set_footer(text=f"requested by {ctx.author}", icon_url=ctx.author.avatar_url)
    return embed