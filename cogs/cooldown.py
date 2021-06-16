from discord.ext import commands
from utils.subclasses import AnimeContext, GlobalCooldown

# class MaxGlobalConcurrencyReached(commands.CommandError):
#     def __init__(self):
#         super().__init__("There can only be one command running at a time")


class CoolDown(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # bot.add_check(self.global_concurrency, call_once=True)
        bot.add_check(self.global_cooldown, call_once=True)
        self.normal_cooldown = commands.CooldownMapping.from_cooldown(5, 1, commands.BucketType.user)

    @commands.Cog.listener()
    async def on_command(self, ctx: AnimeContext):
        if ctx.message.author.id in [590323594744168494, 711057339360477184]:
            ctx.command.reset_cooldown(ctx)

    # @commands.Cog.listener()
    # async def on_command(self, ctx: AnimeContext):
    #     if not ctx.message.id in self.bot.concurrency:
    #         self.bot.concurrency.append(ctx.author.id)

    # @commands.Cog.listener()
    # async def on_command_error(self, ctx: AnimeContext, error):
    #     self.bot.concurrency.remove(ctx.author.id)

    # @commands.Cog.listener()
    # async def on_command_completion(self, ctx: AnimeContext):
    #     self.bot.concurrency.remove(ctx.author.id)

    # async def global_concurrency(self, ctx: AnimeContext):
    #     if ctx.author.id in self.bot.concurrency:
    #         raise MaxGlobalConcurrencyReached()
    #     else:
    #         return True
    async def global_cooldown(self, ctx: AnimeContext):
        bucket = self.normal_cooldown.get_bucket(ctx.message)
        retry_after = bucket.update_rate_limit()
        if ctx.author.id == 590323594744168494 or not retry_after:
            return True
        raise GlobalCooldown(bucket, retry_after)


def setup(bot):
    bot.add_cog(CoolDown(bot))
