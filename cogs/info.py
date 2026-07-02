import discord
import datetime
import platform
from discord.ext import commands
import psutil
import lavalink
from cogs.owner import vote_required


class Info(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.start_time = datetime.datetime.now()

    @commands.Cog.listener()
    async def on_ready(self):
        print("Info Is Ready")

    # ------------------- PING -------------------
    @commands.command(help="Shows the latency of the bot", usage="ping")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ping(self, ctx):
        latency = round(self.client.latency * 1000)
        
        # Determine emoji based on latency
        if latency < 25:
            emoji = "<:latency:1454709860485828679>"  # Lightning fast
        elif latency < 50:
            emoji = "<:mid_latency:1454709844010340406>"  # Good
        else:
            emoji = "<:low_latency:1454709890919563469>"  # Warning
        
        embed = discord.Embed(
            description=f"{emoji} My Latency is {latency} ms",
            colour=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ------------------- UPTIME -------------------
    @commands.command(aliases=['up'], help="Shows the uptime of the bot", usage="uptime")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def uptime(self, ctx):
        current_time = datetime.datetime.now()
        uptime = current_time - self.start_time
        hours, remainder = divmod(int(uptime.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        days, hours = divmod(hours, 24)
        uptime_str = f"{days} day(s), {hours} hour(s), {minutes} minute(s), {seconds} second(s)"
        embed = discord.Embed(description=f"<a:uptimer:1454709458604261437> Uptime: {uptime_str}", colour=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

    # ------------------- INVITE -------------------
    @commands.command(aliases=['inv'], help="Gives you the invite link of bot", usage="invite")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def invite(self, ctx):
        embed = discord.Embed(description="<:invitesss:1454727501590040578> [Invite me to get the best quality music.](https://discord.com/oauth2/authorize?client_id=1419347731545329744)", colour=0x2b2d31)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(
            label="Fault",
            url="https://discord.com/oauth2/authorize?client_id=1419347731545329744"
        ))
        await ctx.reply(embed=embed, mention_author=False, view=view)

    # ------------------- SUPPORT -------------------
    @commands.command(aliases=['sup'], help="Gives you the support server link", usage="support")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def support(self, ctx):
        embed = discord.Embed(description="<:Support:1454727451081965651> [Want help regarding the bot? Join our support.](https://discord.gg/TG26Tfn2eD)", colour=0x2b2d31)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Support", url="https://discord.gg/TG26Tfn2eD"))
        await ctx.reply(embed=embed, mention_author=False, view=view)

    # ------------------- VOTE -------------------
    @commands.command(help="Vote for the bot", usage="vote")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def vote(self, ctx):
        embed = discord.Embed(
            description="<:topgg:1454709401335369902> [Support Fault! Love using Fault? Help us grow by voting! Your vote helps us reach more servers and bring even better features.](https://top.gg/bot/1419347731545329744/vote)",
            colour=0x2b2d31
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Vote", url="https://top.gg/bot/1419347731545329744/vote"))
        await ctx.reply(embed=embed, mention_author=False, view=view)

            # ------------------- STATS -------------------
    @commands.command(aliases=['bi'], help="Shows the information of the bot", usage="stats")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def stats(self, ctx):
        # Calculate uptime
        current_time = datetime.datetime.now()
        uptime = current_time - self.start_time
        total_seconds = int(uptime.total_seconds())
        days, remainder = divmod(total_seconds, 86400)
        hours, remainder = divmod(remainder, 3600)
        minutes, seconds = divmod(remainder, 60)
        uptime_str = f"{days}d {hours}h {minutes}m {seconds}s"
        
        # Get actual statistics
        version = "v2.0"  # Fixed version as requested
        
        # Get guild count with comma formatting
        guild_count = len(self.client.guilds)
        guild_count_formatted = f"{guild_count:,}"
        
        # Calculate real user count and add 200,000 fake users
        real_user_count = sum(g.member_count for g in self.client.guilds if g.member_count)
        total_users = real_user_count + 200000  # Add 200,000 fake users
        total_users_formatted = f"{total_users:,}"
        
        # Get bot's memory usage (RSS - Resident Set Size)
        process = psutil.Process()
        memory_info = process.memory_info()
        memory_used_mb = memory_info.rss / 1024 / 1024  # Convert bytes to MB
        
        # Use a fixed total memory (like your hosting gives you 1024MB)
        total_memory_mb = 4096  # Your hosting gives you 1024MB
        
        # Format memory with commas
        memory_used_formatted = f"{memory_used_mb:,.0f}"
        total_memory_formatted = f"{total_memory_mb:,.0f}"
        
        # Get CPU usage
        cpu_usage = psutil.cpu_percent(interval=0.1)
        
        # Get shard info
        shard_id = ctx.guild.shard_id if hasattr(ctx.guild, 'shard_id') else 0
        shard_count = self.client.shard_count
        
        # Get latency
        latency = round(self.client.latency * 1000)
        
        # Format the description as requested
        description = (
            f"```py\n"
            f"Version :: {version}\n"
            f"Guilds  :: {guild_count_formatted}\n"
            f"Users   :: {total_users_formatted}\n"
            f"Memory  :: {memory_used_formatted} MB / {total_memory_formatted} MB\n"
            f"CPU Usage :: {cpu_usage}%\n"
            f"```\n"
            f"-# - Shard: **{shard_id + 1}/{shard_count}**\n"
            f"- Latency: **{latency}ms**\n"
            f"-# - Uptime: **{uptime_str}**"
        )
        
        embed = discord.Embed(
            title="Fault Statistics",
            description=description,
            color=0x2b2d31
        )
        
        embed.set_thumbnail(url=self.client.user.avatar.url)
        embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
        
        await ctx.reply(embed=embed, mention_author=False)

    # ======================================================
    #                   AVATAR COMMANDS
    # ======================================================

    @commands.command(aliases=["pfp", "av"], help="Shows user's avatar", usage="avatar [user/user_id]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def avatar(self, ctx, user_input=None):
        """Shows user's avatar - accepts member mention or user ID"""
        try:
            # If no input provided, show author's avatar
            if user_input is None:
                member = ctx.author
            else:
                # Try to parse as user ID
                if user_input.isdigit():
                    user_id = int(user_input)
                    try:
                        # Try to fetch user by ID (works globally)
                        user = await self.client.fetch_user(user_id)
                        member = user
                    except discord.NotFound:
                        embed = discord.Embed(
                            description="<:HadeCross:1454058806211514492> | User not found. Please provide a valid user ID.",
                            color=0x2b2d31
                        )
                        return await ctx.reply(embed=embed, mention_author=False)
                else:
                    # Try to parse as mention or username
                    try:
                        # Convert string to member object
                        converter = commands.MemberConverter()
                        member = await converter.convert(ctx, user_input)
                    except commands.MemberNotFound:
                        embed = discord.Embed(
                            description="<:HadeCross:1454058806211514492> | User not found in this server. Try using a user ID for users in other servers.",
                            color=0x2b2d31
                        )
                        return await ctx.reply(embed=embed, mention_author=False)
            
            embed = discord.Embed(color=0x2b2d31)
            embed.set_author(name=f"{member.name}'s Avatar")
            embed.set_image(url=member.display_avatar.url)
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"Avatar command error: {e}")
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | An error occurred while fetching the avatar.",
                color=0x2b2d31
            )
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(help="Shows user's banner", usage="banner [user/user_id]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def banner(self, ctx, user_input=None):
        """Shows user's banner - accepts member mention or user ID"""
        try:
            # If no input provided, show author's banner
            if user_input is None:
                member = ctx.author
                user = await self.client.fetch_user(member.id)
            else:
                # Try to parse as user ID
                if user_input.isdigit():
                    user_id = int(user_input)
                    try:
                        # Try to fetch user by ID (works globally)
                        user = await self.client.fetch_user(user_id)
                    except discord.NotFound:
                        embed = discord.Embed(
                            description="<:HadeCross:1454058806211514492> | User not found. Please provide a valid user ID.",
                            color=0x2b2d31
                        )
                        return await ctx.reply(embed=embed, mention_author=False)
                else:
                    # Try to parse as mention or username
                    try:
                        # Convert string to member object
                        converter = commands.MemberConverter()
                        member = await converter.convert(ctx, user_input)
                        user = await self.client.fetch_user(member.id)
                    except commands.MemberNotFound:
                        embed = discord.Embed(
                            description="<:HadeCross:1454058806211514492> | User not found in this server. Try using a user ID for users in other servers.",
                            color=0x2b2d31
                        )
                        return await ctx.reply(embed=embed, mention_author=False)
            
            banner = user.banner
            if banner is None:
                return await ctx.reply("<:HadeCross:1454058806211514492> | User has no banner.", mention_author=False)

            embed = discord.Embed(color=0x2b2d31)
            embed.set_author(name=f"{user.name}'s Banner")
            embed.set_image(url=banner.url)
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"Banner command error: {e}")
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | An error occurred while fetching the banner.",
                color=0x2b2d31
            )
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=["svav"], help="Shows server avatar", usage="serveravatar")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def serveravatar(self, ctx):
        if not ctx.guild.icon:
            return await ctx.reply("<:HadeCross:1454058806211514492> | This server has no icon.", mention_author=False)

        embed = discord.Embed(color=0x2b2d31)
        embed.set_author(name=f"{ctx.guild.name} Server Avatar")
        embed.set_image(url=ctx.guild.icon.url)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=["svbanner"], help="Shows server banner", usage="serverbanner")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def serverbanner(self, ctx):
        if not ctx.guild.banner:
            return await ctx.reply("<:HadeCross:1454058806211514492> | This server has no banner.", mention_author=False)

        embed = discord.Embed(color=0x2b2d31)
        embed.set_author(name=f"{ctx.guild.name} Server Banner")
        embed.set_image(url=ctx.guild.banner.url)
        await ctx.reply(embed=embed, mention_author=False)

    # ------------------- NODE COMMAND -------------------
    @commands.command(name="node", help="Shows Lavalink node statistics (Vote required or use vote bypass)", usage="node")
    @vote_required()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def node_stats(self, ctx):
        """Show Lavalink node statistics (Owner only)"""
        if not hasattr(self.client, 'lavalink') or not self.client.lavalink:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | Lavalink is not initialized.",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)
        
        nodes = self.client.lavalink.node_manager.nodes
        if not nodes:
            embed = discord.Embed(
                description="<a:downtime:1454709596114522214> No Lavalink nodes connected.",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)
        
        node_info = []
        total_players = 0
        total_playing = 0
        
        for i, node in enumerate(nodes, 1):
            try:
                # Check if node is available
                is_available = node.available if hasattr(node, 'available') else True
                
                stats = node.stats
                if stats:
                    players = stats.playing_players
                    total_players += stats.players
                    total_playing += players
                    cpu_usage = round(stats.lavalink_load * 100, 2)
                    memory_used = stats.memory_used / 1024 / 1024  # Convert to MB
                    memory_free = stats.memory_free / 1024 / 1024  # Convert to MB
                    memory_allocated = stats.memory_allocated / 1024 / 1024  # Convert to MB
                    uptime_seconds = stats.uptime / 1000
                    hours, remainder = divmod(int(uptime_seconds), 3600)
                    minutes, seconds = divmod(remainder, 60)
                    uptime_str = f"{hours}h {minutes}m {seconds}s"
                    
                    node_info.append(
                        f"**Node {i}** - `{node.name or 'Unnamed'}`\n"
                        f"• Players: {players}/{stats.players} playing\n"
                        f"• CPU: {cpu_usage}%\n"
                        f"• Memory: {memory_used:.1f}/{memory_allocated:.1f} MB ({memory_free:.1f} MB free)\n"
                        f"• Uptime: {uptime_str}\n"
                        f"• Connected: {'Yes | <a:uptimer:1454709458604261437>' if is_available else 'No | <a:downtime:1454709596114522214>'}"
                    )
                else:
                    node_info.append(
                        f"**Node {i}** - `{node.name or 'Unnamed'}`\n"
                        f"• Status: Connected (no stats available)\n"
                        f"• Connected: {'Yes | <a:uptimer:1454709458604261437>' if is_available else 'No | <a:downtime:1454709596114522214>'}"
                    )
            except Exception as e:
                print(f"Node stats error: {e}")
                node_info.append(f"**Node {i}** - Error fetching stats")
        
        description = "\n\n".join(node_info)
        if len(description) > 4096:
            description = description[:4093] + "..."
        
        embed = discord.Embed(
            title="Lavalink Node Statistics",
            description=description,
            color=0x2b2d31
        )
        embed.set_footer(text=f"Total Players: {total_playing}/{total_players} playing")
        
        await ctx.reply(embed=embed, mention_author=False)


async def setup(client):
    await client.add_cog(Info(client))