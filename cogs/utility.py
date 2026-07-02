import discord
from discord.ext import commands
import sqlite3


class Utility(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.con = sqlite3.connect('databases/settings.db', check_same_thread=False)
        self.cur = self.con.cursor()
        self.color = 0x2b2d31
        self._init_tables()

    def _init_tables(self):
        """Initialize database tables"""
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS ignored_channels (
                guild_id INTEGER,
                channel_id INTEGER,
                PRIMARY KEY (guild_id, channel_id)
            )
        ''')
        
        # REMOVED bypass_users table
        
        self.cur.execute('''
            CREATE TABLE IF NOT EXISTS Prefix (
                guild_id INTEGER PRIMARY KEY,
                prefix TEXT DEFAULT 'F'
            )
        ''')
        self.con.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        print("Utility Is Ready")

    # PREFIX COMMAND
    @commands.command(aliases=['prefix'], help="Changes the prefix of the bot", usage="setprefix <new_prefix>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.check_any(commands.is_owner(), commands.has_permissions(administrator=True))
    @commands.guild_only()
    async def setprefix(self, ctx, prefix=None):
        if prefix is None:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | Please provide a prefix to update.", color=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        if len(prefix) > 2:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | Prefix cannot be greater than 2 characters.", color=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute("UPDATE Prefix SET prefix = ? WHERE guild_id = ?", (prefix, ctx.guild.id))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Successfully set the prefix to `{prefix}`", color=self.color)
        await ctx.reply(embed=embed, mention_author=False)

    # IGNORE COMMANDS GROUP
    @commands.group(description="Ignore Commands", aliases=['ig'], invoke_without_command=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
    @commands.guild_only()
    async def ignore(self, ctx):
        embed = discord.Embed(
            description="<:HadeCross:1454058806211514492> | Use `ignore add`, `ignore remove`, `ignore reset`, or `ignore list`",
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @ignore.command(name="add")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
    @commands.guild_only()
    async def ignore_add(self, ctx, channel: discord.TextChannel):
        self.cur.execute('SELECT COUNT(*) FROM ignored_channels WHERE guild_id = ?', (ctx.guild.id,))
        ignored_count = self.cur.fetchone()[0]
        limit = 3

        if ignored_count >= limit:
            embed = discord.Embed(description=f"<:HadeCross:1454058806211514492> | You cannot ignore more than `{limit}` channels.", color=self.color)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute('SELECT * FROM ignored_channels WHERE guild_id = ? AND channel_id = ?', (ctx.guild.id, channel.id))
        if self.cur.fetchone():
            embed = discord.Embed(description=f"<:HadeCross:1454058806211514492> | **{channel.name}** is already present in my ignore list.", color=self.color)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute('INSERT INTO ignored_channels (guild_id, channel_id) VALUES (?, ?)', (ctx.guild.id, channel.id))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | I will now ignore all messages in **{channel.name}**", color=self.color)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @ignore.command(name="remove")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
    @commands.guild_only()
    async def ignore_remove(self, ctx, channel: discord.TextChannel):
        self.cur.execute('SELECT * FROM ignored_channels WHERE guild_id = ? AND channel_id = ?', (ctx.guild.id, channel.id))
        if not self.cur.fetchone():
            embed = discord.Embed(description=f"<:HadeCross:1454058806211514492> | **{channel.name}** is not present in my ignore list.", color=self.color)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute('DELETE FROM ignored_channels WHERE guild_id = ? AND channel_id = ?', (ctx.guild.id, channel.id))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | I will no longer ignore messages in **{channel.name}**", color=self.color)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @ignore.command(name="reset")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
    @commands.guild_only()
    async def ignore_reset(self, ctx):
        self.cur.execute('SELECT * FROM ignored_channels WHERE guild_id = ?', (ctx.guild.id,))
        if not self.cur.fetchall():
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | There are no channels in the ignore list for this guild.", color=self.color)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute('DELETE FROM ignored_channels WHERE guild_id = ?', (ctx.guild.id,))
        self.con.commit()
        embed = discord.Embed(description="<:HadeTick:1454058805473050636> | All channels have been removed from the ignore list.", color=self.color)
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
        await ctx.reply(embed=embed, mention_author=False)

    @ignore.command(name="list")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.check_any(commands.has_permissions(administrator=True), commands.is_owner())
    @commands.guild_only()
    async def ignore_list(self, ctx):
        self.cur.execute('SELECT channel_id FROM ignored_channels WHERE guild_id = ?', (ctx.guild.id,))
        ignored_channels = self.cur.fetchall()
        
        if not ignored_channels:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | There are no channels in the ignore list for this guild.", color=self.color)
            embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
            embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
            return await ctx.reply(embed=embed, mention_author=False)
        
        channel_list = []
        for channel_id in ignored_channels:
            channel = ctx.guild.get_channel(channel_id[0])
            if channel:
                channel_list.append(f"{channel.mention} (`{channel.id}`)")
            else:
                channel_list.append(f"Unknown Channel (`{channel_id[0]}`)")
        
        embed = discord.Embed(
            title="Ignored Channels",
            description="\n".join(channel_list),
            color=self.color
        )
        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_footer(text=f"Total: {len(ignored_channels)}/3 channels ignored")
        await ctx.reply(embed=embed, mention_author=False)

    # PURGE COMMANDS WITH ALIASES
    @commands.command(name="purge", aliases=['clean'], help="Purge messages from channel", usage="purge <amount>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.check_any(commands.is_owner(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def purge(self, ctx, amount: int):
        if amount < 1 or amount > 100:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | Amount must be between 1 and 100.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False, delete_after=5)

        deleted = await ctx.channel.purge(limit=amount + 1)  # +1 for the command message
        
        embed = discord.Embed(
            description=f"<:HadeTick:1454058805473050636> | Successfully purged `{len(deleted) - 1}` messages.",
            color=self.color
        )
        message = await ctx.send(embed=embed, delete_after=5)

    @commands.command(name="purgebots", aliases=['pb'], help="Purge bot messages from channel", usage="purgebots <amount>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.check_any(commands.is_owner(), commands.has_permissions(manage_messages=True))
    @commands.bot_has_permissions(manage_messages=True)
    @commands.guild_only()
    async def purgebots(self, ctx, amount: int = 100):
        if amount < 1 or amount > 100:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | Amount must be between 1 and 100.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False, delete_after=5)

        def is_bot_message(m):
            return m.author.bot

        deleted = await ctx.channel.purge(limit=amount, check=is_bot_message)
        
        embed = discord.Embed(
            description=f"<:HadeTick:1454058805473050636> | Successfully purged `{len(deleted)}` bot messages.",
            color=self.color
        )
        message = await ctx.send(embed=embed, delete_after=5)

    # REPORT COMMAND
    @commands.command(help="You can send your issue to HQ server", usage="report <Your Issue>")
    @commands.cooldown(1, 600, commands.BucketType.user)
    @commands.guild_only()
    async def report(self, ctx, *, issue=None):
        if not issue:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | You are missing a required argument for the command report.",
                color=self.color
            )
            return await ctx.send(embed=embed)

        embed = discord.Embed(title='New Issue Report', description=f'**Issue:** {issue}', color=self.color)
        embed.add_field(name='User', value=f'{ctx.author.name}#{ctx.author.discriminator} (ID: {ctx.author.id})', inline=False)
        embed.add_field(name='Server', value=f'{ctx.guild.name} (ID: {ctx.guild.id})', inline=False)

        try:
            invite = await ctx.channel.create_invite(max_age=86400)
            embed.add_field(name='Channel', value=f'{ctx.channel.name} (ID: {ctx.channel.id})', inline=False)
            embed.add_field(name='Server Invite', value=f'https://discord.gg/{invite.code}', inline=False)
        except discord.errors.Forbidden:
            embed.add_field(name='Channel', value=f'{ctx.channel.name} (ID: {ctx.channel.id})', inline=False)
            embed.add_field(name='Server Invite', value='None', inline=False)

        log_channel = self.client.get_channel(1444717752722919498)
        if log_channel:
            await log_channel.send(embed=embed)

        embed2 = discord.Embed(
            description="<:HadeTick:1454058805473050636> | Your issue has been reported. You can join the support server for further assistance.",
            colour=self.color
        )
        embed2.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed2.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
        view = discord.ui.View()
        view.add_item(discord.ui.Button(label="Support", url="https://discord.gg/TG26Tfn2eD"))
        await ctx.reply(embed=embed2, mention_author=False, view=view)


async def setup(client):
    await client.add_cog(Utility(client))