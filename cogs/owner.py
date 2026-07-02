import discord
from discord.ext import commands
import sqlite3
import tarfile
import os
import io
from datetime import datetime
import aiohttp
from Fault import TOPGG_TOKEN


def extraowner():
    async def predicate(ctx: commands.Context):
        with sqlite3.connect('databases/owner.db') as con:
            cur = con.cursor()
            cur.execute("SELECT user_id FROM Owner")
            ids_ = cur.fetchall()
            return ctx.author.id in [i[0] for i in ids_]
    return commands.check(predicate)


def main_owner_only():
    """Check if the user is the main owner (Console)"""
    async def predicate(ctx: commands.Context):
        MAIN_OWNER_ID = 901487880067776524  # ! Console🥀
        return ctx.author.id == MAIN_OWNER_ID
    return commands.check(predicate)


def vote_required():
    async def predicate(ctx: commands.Context):
        with sqlite3.connect('databases/owner.db') as con:
            cur = con.cursor()
            # Check if user is in vote bypass list
            cur.execute("SELECT user_id FROM vote_bypass WHERE user_id = ?", (ctx.author.id,))
            if cur.fetchone():
                return True
            
            # Check if user is owner
            if ctx.author.id == ctx.bot.owner_id:
                return True
            
            # Check if user has voted on TopGG
            try:
                async with aiohttp.ClientSession() as session:
                    headers = {"Authorization": TOPGG_TOKEN}
                    async with session.get(
                        f"https://top.gg/api/bots/{ctx.bot.user.id}/check?userId={ctx.author.id}",
                        headers=headers
                    ) as resp:
                        data = await resp.json()
                        if data.get("voted", 0) == 1:
                            return True
            except:
                pass
            
            # User hasn't voted - send message with vote link
            embed = discord.Embed(
                description="<:Warning:1454059115021209624> | This command requires you to vote for Fault on Top.gg!\n\n[Vote here to unlock this command](https://top.gg/bot/1419347731545329744/vote)",
                color=0x2b2d31
            )
            await ctx.reply(embed=embed, mention_author=False)
            return False
    
    return commands.check(predicate)


class Owner(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.con = sqlite3.connect('databases/owner.db', check_same_thread=False)
        self.cur = self.con.cursor()
        self.log_channel_id = 1445053769049051258
        self._init_vote_bypass_table()

    def _init_vote_bypass_table(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS vote_bypass (
                user_id INTEGER PRIMARY KEY
            )
        """)
        self.con.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        print("Owner Is Ready")

    # ---------------- LOG HELPER ----------------
    async def send_log(self, title: str, ctx, user: discord.User):
        try:
            channel = await self.client.fetch_channel(self.log_channel_id)
            embed = discord.Embed(
                title=title,
                description=(
                    f"Action By: {ctx.author} ({ctx.author.id})\n"
                    f"User: {user} ({user.id})"
                ),
                color=0x2b2d31,
                timestamp=datetime.utcnow()
            )
            await channel.send(embed=embed)
        except Exception as e:
            print(f"Log channel error: {e}")

    # ---------------- OWNER ----------------
    @commands.group(hidden=True, invoke_without_command=True)
    @commands.check_any(commands.is_owner(), extraowner())
    async def owner(self, ctx):
        embed = discord.Embed(description="<:HadeCross:1454058806211514492> | Use `owner add` or `owner remove` or `owner list`", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

    @owner.command(name="add")
    @main_owner_only()  # ONLY MAIN OWNER CAN USE THIS
    async def owner_add(self, ctx, user: discord.User):
        self.cur.execute("SELECT user_id FROM Owner WHERE user_id = ?", (user.id,))
        if self.cur.fetchone():
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | That user is already in owner list.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute("INSERT INTO Owner(user_id) VALUES(?)", (user.id,))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Successfully added **{user}** to owner list.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

    @owner.command(name="remove")
    @main_owner_only()  # ONLY MAIN OWNER CAN USE THIS
    async def owner_remove(self, ctx, user: discord.User):
        self.cur.execute("SELECT user_id FROM Owner WHERE user_id = ?", (user.id,))
        if not self.cur.fetchone():
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | That user is not in owner list.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute("DELETE FROM Owner WHERE user_id = ?", (user.id,))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Successfully removed **{user}** from owner list.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

    @owner.command(name="list")
    @commands.check_any(commands.is_owner(), extraowner())
    async def owner_list(self, ctx):
        self.cur.execute("SELECT user_id FROM Owner")
        owners = self.cur.fetchall()
        
        if not owners:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | No additional owners found.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)
        
        owner_list = []
        for owner_id in owners:
            try:
                user = await self.client.fetch_user(owner_id[0])
                owner_list.append(f"{user} ({user.id})")
            except:
                owner_list.append(f"Unknown User ({owner_id[0]})")
        
        embed = discord.Embed(
            title="Owner List",
            description="\n".join(owner_list),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ---------------- NO PREFIX ----------------
    @commands.group(aliases=['np'], invoke_without_command=True, hidden=True)
    @commands.check_any(commands.is_owner(), extraowner())
    async def noprefix(self, ctx):
        embed = discord.Embed(description="<:HadeCross:1454058806211514492> | Use `np add` or `np remove` or `np remove`", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

    @noprefix.command(name="add")
    @commands.check_any(commands.is_owner(), extraowner())
    async def noprefix_add(self, ctx, user: discord.User):
        self.cur.execute("SELECT users FROM Np WHERE users = ?", (str(user.id),))
        if self.cur.fetchone():
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | That user is already in no prefix.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute("INSERT INTO Np(users) VALUES(?)", (str(user.id),))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Successfully added **{user}** to no prefix.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

        await self.send_log("No Prefix Added", ctx, user)

    @noprefix.command(name="remove")
    @commands.check_any(commands.is_owner(), extraowner())
    async def noprefix_remove(self, ctx, user: discord.User):
        self.cur.execute("SELECT users FROM Np WHERE users = ?", (str(user.id),))
        if not self.cur.fetchone():
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | That user isn't in no prefix.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute("DELETE FROM Np WHERE users = ?", (str(user.id),))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Successfully removed **{user}** from no prefix.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

        await self.send_log("No Prefix Removed", ctx, user)

    @noprefix.command(name="list")
    @commands.check_any(commands.is_owner(), extraowner())
    async def noprefix_list(self, ctx):
        self.cur.execute("SELECT users FROM Np")
        np_users = self.cur.fetchall()
        
        if not np_users:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | No users have no prefix access.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)
        
        user_list = []
        for user_id in np_users:
            try:
                user = await self.client.fetch_user(int(user_id[0]))
                user_list.append(f"{user} ({user.id})")
            except:
                user_list.append(f"Unknown User ({user_id[0]})")
        
        embed = discord.Embed(
            title="No Prefix Users",
            description="\n".join(user_list),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ---------------- BLACKLIST ----------------
    @commands.group(invoke_without_command=True, hidden=True)
    @commands.is_owner()
    async def bl(self, ctx):
        embed = discord.Embed(description="<:HadeCross:1454058806211514492> | Use `bl add` or `bl remove` or `bl list`", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

    @bl.command(name="add")
    @commands.is_owner()
    async def bl_add(self, ctx, user: discord.User):
        self.cur.execute("SELECT * FROM blacklist WHERE user_id = ?", (user.id,))
        if self.cur.fetchone():
            embed = discord.Embed(description=f"<:HadeCross:1454058806211514492> | {user} is already blacklisted.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute("INSERT INTO blacklist (user_id) VALUES (?)", (user.id,))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Blacklisted **{user}**.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

        await self.send_log("Blacklist Added", ctx, user)

    @bl.command(name="remove")
    @commands.is_owner()
    async def bl_remove(self, ctx, user: discord.User):
        self.cur.execute("SELECT * FROM blacklist WHERE user_id = ?", (user.id,))
        if not self.cur.fetchone():
            embed = discord.Embed(description=f"<:HadeCross:1454058806211514492> | {user} is not blacklisted.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute("DELETE FROM blacklist WHERE user_id = ?", (user.id,))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Removed **{user}** from blacklist.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

        await self.send_log("Blacklist Removed", ctx, user)

    @bl.command(name="list")
    @commands.is_owner()
    async def bl_list(self, ctx):
        self.cur.execute("SELECT user_id FROM blacklist")
        blacklisted = self.cur.fetchall()
        
        if not blacklisted:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | No users are blacklisted.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)
        
        blacklist = []
        for user_id in blacklisted:
            try:
                user = await self.client.fetch_user(user_id[0])
                blacklist.append(f"{user} ({user.id})")
            except:
                blacklist.append(f"Unknown User ({user_id[0]})")
        
        embed = discord.Embed(
            title="Blacklisted Users",
            description="\n".join(blacklist),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ---------------- VOTE BYPASS ----------------
    @commands.group(invoke_without_command=True, hidden=True)
    @commands.check_any(commands.is_owner(), extraowner())
    async def vb(self, ctx):
        embed = discord.Embed(description="<:HadeCross:1454058806211514492> | Use `vb add` or `vb remove` or `vb list`", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

    @vb.command(name="add")
    @commands.check_any(commands.is_owner(), extraowner())
    async def vb_add(self, ctx, user: discord.User):
        self.cur.execute("SELECT user_id FROM vote_bypass WHERE user_id = ?", (user.id,))
        if self.cur.fetchone():
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | That user is already in vote bypass list.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute("INSERT INTO vote_bypass(user_id) VALUES(?)", (user.id,))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Successfully added **{user}** to vote bypass list.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

        await self.send_log("Vote Bypass Added", ctx, user)

    @vb.command(name="remove")
    @commands.check_any(commands.is_owner(), extraowner())
    async def vb_remove(self, ctx, user: discord.User):
        self.cur.execute("SELECT user_id FROM vote_bypass WHERE user_id = ?", (user.id,))
        if not self.cur.fetchone():
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | That user is not in vote bypass list.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        self.cur.execute("DELETE FROM vote_bypass WHERE user_id = ?", (user.id,))
        self.con.commit()
        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Successfully removed **{user}** from vote bypass list.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

        await self.send_log("Vote Bypass Removed", ctx, user)

    @vb.command(name="list")
    @commands.check_any(commands.is_owner(), extraowner())
    async def vb_list(self, ctx):
        self.cur.execute("SELECT user_id FROM vote_bypass")
        vb_users = self.cur.fetchall()
        
        if not vb_users:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | No users have vote bypass access.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)
        
        user_list = []
        for user_id in vb_users:
            try:
                user = await self.client.fetch_user(user_id[0])
                user_list.append(f"{user} ({user.id})")
            except:
                user_list.append(f"Unknown User ({user_id[0]})")
        
        embed = discord.Embed(
            title="Vote Bypass Users",
            description="\n".join(user_list),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)

    # ---------------- GUILD LEAVE ----------------
    @commands.command(hidden=True)
    @main_owner_only()  # ONLY MAIN OWNER CAN USE THIS
    async def gleave(self, ctx, guild: discord.Guild):
        await guild.leave()
        embed = discord.Embed(description="<:HadeTick:1454058805473050636> | Successfully left the server.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

    # ---------------- GUILD LIST ----------------
    @commands.command(name="glist", hidden=True)
    @commands.check_any(commands.is_owner(), extraowner())
    async def guild_list(self, ctx):
        guilds = sorted(self.client.guilds, key=lambda g: g.member_count, reverse=True)
        
        if not guilds:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | Bot is not in any servers.", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)
        
        total_guilds = len(guilds)
        total_members = sum(g.member_count for g in guilds)
        pages = []
        
        # Split guilds into pages of 25
        for i in range(0, total_guilds, 25):
            page_guilds = guilds[i:i + 25]
            description_parts = []
            
            for idx, guild in enumerate(page_guilds, start=i+1):
                description_parts.append(f"**{idx}.** **{guild.name}**\nID: `{guild.id}` | Members: {guild.member_count}")
            
            description = "\n\n".join(description_parts)
            pages.append(description)
        
        current_page = 0
        total_pages = len(pages)
        
        embed = discord.Embed(
            title=f"Server List ({total_guilds} servers, {total_members} total members)",
            description=pages[current_page],
            color=0x2b2d31
        )
        embed.set_footer(text=f"Page {current_page + 1}/{total_pages}")
        
        message = await ctx.reply(embed=embed, mention_author=False)
        
        if total_pages > 1:
            await message.add_reaction("◀️")
            await message.add_reaction("▶️")
            
            def check(reaction, user):
                return user == ctx.author and str(reaction.emoji) in ["◀️", "▶️"] and reaction.message.id == message.id
            
            while True:
                try:
                    reaction, user = await self.client.wait_for("reaction_add", timeout=60.0, check=check)
                    
                    if str(reaction.emoji) == "▶️" and current_page < total_pages - 1:
                        current_page += 1
                    elif str(reaction.emoji) == "◀️" and current_page > 0:
                        current_page -= 1
                    
                    embed.description = pages[current_page]
                    embed.set_footer(text=f"Page {current_page + 1}/{total_pages}")
                    await message.edit(embed=embed)
                    
                    try:
                        await message.remove_reaction(reaction, user)
                    except:
                        pass
                        
                except TimeoutError:
                    break

    # ---------------- GUILD INVITE ----------------
    @commands.command(name="guildinvite", aliases=["ginv"], hidden=True)
    @commands.check_any(commands.is_owner(), extraowner())
    async def invite_to_guild(self, ctx, guild_id: int):
        guild = self.client.get_guild(guild_id)
        if not guild:
            return await ctx.send("<:HadeCross:1454058806211514492> | Could not find a server with the provided ID.")

        for channel in guild.text_channels:
            try:
                invite = await channel.create_invite(max_age=604800, max_uses=1)
                return await ctx.send(f"Here's the invite link: {invite}")
            except discord.Forbidden:
                continue

        await ctx.send("<:HadeCross:1454058806211514492> | Could not create an invite for any channel in the server.")

    # ---------------- BACKUP ----------------
    @commands.command(name="backup", hidden=True)
    @main_owner_only()  # ONLY MAIN OWNER CAN USE THIS
    async def create_backup(self, ctx):
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"fault_backup_{timestamp}.tar.gz"

            buffer = io.BytesIO()
            with tarfile.open(fileobj=buffer, mode="w:gz") as tar:
                files_to_backup = [
                    "cogs",
                    "databases",
                    "main.py",
                    "Fault.py",
                    "r.txt",
                    "assets"
                ]

                for item in files_to_backup:
                    if os.path.exists(item):
                        if os.path.isdir(item):
                            for root, _, files in os.walk(item):
                                for file in files:
                                    path = os.path.join(root, file)
                                    tar.add(path, arcname=path)
                        else:
                            tar.add(item, arcname=item)

            buffer.seek(0)

            owner = await self.client.fetch_user(ctx.author.id)
            embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Backup created: **{backup_filename}**", color=0x2b2d31)
            await owner.send(embed=embed, file=discord.File(buffer, backup_filename))

            await ctx.reply(
                embed=discord.Embed(description="<:HadeTick:1454058805473050636> | Backup sent to your DM.", color=0x2b2d31),
                mention_author=False
            )

        except Exception as e:
            await ctx.reply(
                embed=discord.Embed(description=f"<:HadeCross:1454058806211514492> | Backup error: {e}", color=0x2b2d31),
                mention_author=False
            )

    # ---------------- TOP.GG ----------------
    @commands.command(name="topgg", hidden=True)
    @main_owner_only()  # ONLY MAIN OWNER CAN USE THIS
    async def post_topgg(self, ctx):
        url = f"https://top.gg/api/bots/{self.client.user.id}/stats"
        headers = {
            "Authorization": TOPGG_TOKEN,
            "Content-Type": "application/json"
        }
        payload = {
            "server_count": len(self.client.guilds)
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    embed = discord.Embed(
                        description="<:HadeCross:1454058806211514492> | Failed to post stats to Top.gg.",
                        color=0x2b2d31
                    )
                    return await ctx.reply(embed=embed, mention_author=False)

        embed = discord.Embed(
            description=f"<:HadeTick:1454058805473050636> | Successfully posted stats to Top.gg.\nServers: {len(self.client.guilds)}",
            color=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)


async def setup(client):
    await client.add_cog(Owner(client))