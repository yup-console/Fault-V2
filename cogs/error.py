from discord.ext import commands
import discord


class Error(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Error Handler Is Ready")

    @commands.Cog.listener()
    async def on_command_error(self, ctx, error):
        error = getattr(error, 'original', error)

        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | You are missing a required argument for the command **{ctx.command}**.",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if isinstance(error, commands.BotMissingPermissions):
            permissions = ', '.join(perm for perm in error.missing_permissions)
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | The bot needs **{permissions}** to execute this command.",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if isinstance(error, commands.CommandOnCooldown):
            embed = discord.Embed(
                description=f"<:Warning:1454059115021209624> | You're on cooldown. Try again in **{round(error.retry_after, 2)}** seconds.",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if isinstance(error, commands.UserNotFound):
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | The specified user was not found.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        if isinstance(error, commands.MemberNotFound):
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | The specified member was not found.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        if isinstance(error, commands.RoleNotFound):
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | The role **{error.argument}** was not found.",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if isinstance(error, commands.ChannelNotFound):
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | The channel **{error.argument}** was not found.",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if isinstance(error, commands.MaxConcurrencyReached):
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | **{ctx.author}**, **{error}**",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if isinstance(error, commands.CheckAnyFailure):
            for err in error.errors:
                if isinstance(err, commands.MissingPermissions):
                    embed = discord.Embed(
                        description=f"<:HadeCross:1454058806211514492> | You don't have enough permissions to run the command **{ctx.command.qualified_name}**",
                        color=0x2b2d31
                    )
                    return await ctx.reply(embed=embed, mention_author=False)

        if isinstance(error, commands.NoPrivateMessage):
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | This command cannot be used in private messages.",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if isinstance(error, commands.CheckFailure):
            return


async def setup(client):
    await client.add_cog(Error(client))
