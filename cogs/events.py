import discord
from discord.ext import commands
import sqlite3
import datetime
import time
import asyncio


class Events(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.con = sqlite3.connect('databases/settings.db', check_same_thread=False)
        self.cur = self.con.cursor()
        self.start_time = datetime.datetime.now()
        self.cooldowns = {}
        self.log_channel_id = 1444717753276694588
        self.support_url = "https://discord.gg/TG26Tfn2eD"

    @commands.Cog.listener()
    async def on_ready(self):
        print("Events Is Ready")

    def create_welcome_embed(self, message, prefix="F"):
        """Create welcome embed for mention response"""
        embed = discord.Embed(
            title="<:Hi_Ducklett:1454520043038703718> Welcome To Fault",
            color=0x2b2d31,  # Default embed color
            timestamp=datetime.datetime.now()
        )
        
        # Set bot avatar as author icon
        embed.set_author(
            name="Fault Music Bot",
            icon_url=self.client.user.avatar.url if self.client.user.avatar else self.client.user.default_avatar.url
        )
        
        # Create description with proper formatting
        description = (
            f"Hey, {message.author.mention}!\n\n"
            f"My prefix for this server is **[`{prefix}`]({self.support_url})**\n"
            f"Type **[`{prefix}help`]({self.support_url})** for commands list\n\n"
            f"-# Fault is crafted to serve top-notch music with ease and elegance, "
            f"trusted by over **{len(self.client.guilds):,}** servers and continues to grow every day."
        )
        
        embed.description = description
        
        # Set server icon as thumbnail (not image)
        if message.guild.icon:
            embed.set_thumbnail(url=message.guild.icon.url)
        else:
            # Fallback to bot avatar if server has no icon
            embed.set_thumbnail(url=self.client.user.avatar.url if self.client.user.avatar else self.client.user.default_avatar.url)
        
        # Set footer with user info
        embed.set_footer(
            text=f"Requested by {message.author.name}",
            icon_url=message.author.avatar.url if message.author.avatar else message.author.default_avatar.url
        )
        
        return embed

    @commands.Cog.listener()
    async def on_guild_join(self, guild: discord.Guild):
        try:
            # Send log to channel
            log_channel = self.client.get_channel(self.log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="🟩 Joined A Guild",
                    description=(
                        f"**ID:** `{guild.id}`\n"
                        f"**Name:** {guild.name}\n"
                        f"**Owner:** {guild.owner.mention if guild.owner else 'Unknown'}\n"
                        f"**MemberCount:** {len(guild.members):,}\n"
                        f"**Created:** <t:{int(guild.created_at.timestamp())}:R>\n"
                        f"**Bot Count:** {sum(1 for m in guild.members if m.bot)}"
                    ),
                    color=discord.Color.green(),
                    timestamp=datetime.datetime.now()
                )
                if guild.icon:
                    embed.set_thumbnail(url=guild.icon.url)
                else:
                    embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
                
                await log_channel.send(embed=embed)
            else:
                print(f"Could not find log channel with ID: {self.log_channel_id}")
                
        except Exception as e:
            print(f"Guild join log error: {e}")

    @commands.Cog.listener()
    async def on_guild_remove(self, guild: discord.Guild):
        try:
            # Send log to channel
            log_channel = self.client.get_channel(self.log_channel_id)
            if log_channel:
                embed = discord.Embed(
                    title="🟥 Left A Guild",
                    description=(
                        f"**ID:** `{guild.id}`\n"
                        f"**Name:** {guild.name}\n"
                        f"**Owner:** {guild.owner.mention if guild.owner else 'Unknown'}\n"
                        f"**MemberCount:** {len(guild.members):,}\n"
                        f"**Created:** <t:{int(guild.created_at.timestamp())}:R>\n"
                    ),
                    color=discord.Color.red(),
                    timestamp=datetime.datetime.now()
                )
                if guild.icon:
                    embed.set_thumbnail(url=guild.icon.url)
                else:
                    embed.set_thumbnail(url="https://cdn.discordapp.com/embed/avatars/0.png")
                
                await log_channel.send(embed=embed)
            else:
                print(f"Could not find log channel with ID: {self.log_channel_id}")
                
        except Exception as e:
            print(f"Guild remove log error: {e}")

    def get_duration_string(self, joined_at):
        """Calculate how long the bot was in the guild"""
        if not joined_at:
            return "Unknown"
        
        duration = datetime.datetime.now(datetime.timezone.utc) - joined_at
        days = duration.days
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        parts = []
        if days > 0:
            parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
        if seconds > 0 or not parts:
            parts.append(f"{seconds}s")
        
        return " ".join(parts)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot or not message.guild:
            return

        if message.author.id in self.cooldowns:
            remaining_time = self.cooldowns[message.author.id] - time.time()
            if remaining_time > 0:
                return

        if message.content == f'<@{self.client.user.id}>' or message.content == f'<@!{self.client.user.id}>':
            try:
                self.cur.execute("SELECT prefix FROM Prefix WHERE guild_id = ?", (message.guild.id,))
                server_prefix = self.cur.fetchone()
                prefix = server_prefix[0] if server_prefix else "F"

                # Create the custom welcome embed
                embed = self.create_welcome_embed(message, prefix)
                
                # Create buttons
                view = discord.ui.View()
                view.add_item(discord.ui.Button(label="Invite", url="https://discord.com/oauth2/authorize?client_id=1419347731545329744"))
                view.add_item(discord.ui.Button(label="Support", url=self.support_url))

                await message.reply(embed=embed, view=view, mention_author=False)

                self.cooldowns[message.author.id] = time.time() + 5
                await asyncio.sleep(5)
                if message.author.id in self.cooldowns:
                    del self.cooldowns[message.author.id]
            except Exception as e:
                print(f"Mention response error: {e}")


async def setup(client):
    await client.add_cog(Events(client))