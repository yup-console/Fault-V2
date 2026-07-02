import discord
from discord.ext import commands
import sqlite3
import aiohttp
import asyncio
import os
from datetime import datetime
from urllib.parse import quote

# Try to get API keys from Fault.py
try:
    import Fault
    LASTFM_API_KEY = getattr(Fault, 'LASTFM_API_KEY', None)
except ImportError:
    LASTFM_API_KEY = None


class LastFM(commands.Cog):
    """Last.fm music tracking commands"""
    
    def __init__(self, client):
        self.client = client
        
        # Ensure databases directory exists
        if not os.path.exists('databases'):
            os.makedirs('databases')
        
        # Connect to database
        self.db_path = 'databases/lastfm.db'
        self.db = sqlite3.connect(self.db_path, check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_database()
        
        # API configuration
        self.base_url = "http://ws.audioscrobbler.com/2.0/"
        self.session = None
    
    def _init_database(self):
        """Initialize database tables"""
        cursor = self.db.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lastfm_users (
                discord_id INTEGER PRIMARY KEY,
                lastfm_username TEXT NOT NULL,
                scrobbles INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lastfm_cache (
                lastfm_username TEXT PRIMARY KEY,
                realname TEXT,
                avatar_url TEXT,
                country TEXT,
                playcount INTEGER,
                registered TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        self.db.commit()
    
    async def create_session(self):
        """Create aiohttp session if it doesn't exist"""
        if self.session is None:
            self.session = aiohttp.ClientSession()
    
    async def fetch_lastfm_data(self, method, **params):
        """Fetch data from Last.fm API"""
        if not LASTFM_API_KEY:
            return None
        
        await self.create_session()
        
        params.update({
            'method': method,
            'api_key': LASTFM_API_KEY,
            'format': 'json'
        })
        
        try:
            async with self.session.get(self.base_url, params=params, timeout=aiohttp.ClientTimeout(total=10)) as response:
                if response.status == 200:
                    data = await response.json()
                    if 'error' in data:
                        return None
                    return data
                return None
        except Exception as e:
            print(f"❌ Last.fm API error ({method}): {e}")
            return None
    
    async def get_cached_profile(self, username):
        """Get cached Last.fm profile"""
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT realname, avatar_url, country, playcount, registered FROM lastfm_cache WHERE lastfm_username = ?",
            (username,)
        )
        result = cursor.fetchone()
        
        if result:
            return dict(result)
        return None
    
    async def cache_profile(self, username, profile_data):
        """Cache Last.fm profile data"""
        cursor = self.db.cursor()
        
        avatar_url = None
        if profile_data.get('image'):
            images = profile_data.get('image', [])
            if isinstance(images, list) and len(images) > 0:
                avatar_url = images[-1].get('#text')
        
        cursor.execute("""
            INSERT OR REPLACE INTO lastfm_cache 
            (lastfm_username, realname, avatar_url, country, playcount, registered) 
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            username,
            profile_data.get('realname'),
            avatar_url,
            profile_data.get('country'),
            profile_data.get('playcount', 0),
            profile_data.get('registered', {}).get('#text', '')
        ))
        self.db.commit()
    
    @commands.Cog.listener()
    async def on_ready(self):
        """Called when cog is ready"""
        print("Last.fm Cog Is Ready")
    
    @commands.group(name="lastfm", aliases=['lfm', 'fm'], invoke_without_command=True, help="Last.fm commands - track your music listening")
    async def lastfm_group(self, ctx):
        """Last.fm command group - show help"""
        embed = discord.Embed(
            title="<:lastfm:1454165185831895264> Last.fm Commands",
            description="Track your music listening history with Last.fm",
            color=0xFF0000
        )
        embed.add_field(
            name="<:Joined:1454050160073248871> Link Account", 
            value=f"`{ctx.prefix}lastfm login <username>`\nLink your Last.fm account", 
            inline=False
        )
        embed.add_field(
            name="<:Profile:1454050322900058256> View Profile", 
            value=f"`{ctx.prefix}lastfm profile [@user]`\nView Last.fm profile info", 
            inline=False
        )
        embed.add_field(
            name="<:music_note:1454154237671112855> Now Playing", 
            value=f"`{ctx.prefix}lastfm np [@user]`\nView currently playing track", 
            inline=False
        )
        embed.add_field(
            name="<:List:1454166837221658676> Top Artists/Tracks", 
            value=f"`{ctx.prefix}lastfm topartists [@user] [period]`\n`{ctx.prefix}lastfm toptracks [@user] [period]`", 
            inline=False
        )
        embed.add_field(
            name="<:graphic:1454167459220164650> Scrobble Count", 
            value=f"`{ctx.prefix}lastfm scrobble [@user]`\nShow total scrobbles", 
            inline=False
        )
        embed.add_field(
            name="<:vs:1454165578485993685> Compare Taste", 
            value=f"`{ctx.prefix}lastfm compat @user1 @user2`\nCompare music taste between users", 
            inline=False
        )
        embed.add_field(
            name="<:Leave:1454050272010571776> Unlink Account", 
            value=f"`{ctx.prefix}lastfm logout`\nUnlink your Last.fm account", 
            inline=False
        )
        embed.set_footer(text="Get a Last.fm account at https://www.last.fm/join")
        await ctx.reply(embed=embed, mention_author=False)
    
    @lastfm_group.command(name="profile", aliases=['p', 'user'], help="View Last.fm profile", usage="lastfm profile [@user]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_profile(self, ctx, user: discord.Member = None):
        """Show Last.fm profile"""
        try:
            target_user = user or ctx.author
            
            cursor = self.db.cursor()
            cursor.execute("SELECT lastfm_username, scrobbles, registered_at FROM lastfm_users WHERE discord_id = ?", (target_user.id,))
            result = cursor.fetchone()
            
            if not result:
                if target_user == ctx.author:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Last.fm Account Linked",
                        description=f"You don't have a Last.fm account linked.\nUse `{ctx.prefix}lastfm login <username>` to link one.",
                        color=0xFF0000
                    )
                else:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Last.fm Account",
                        description=f"**{target_user.name}** doesn't have a Last.fm account linked.",
                        color=0xFF0000
                    )
                await ctx.reply(embed=embed, mention_author=False)
                return
            
            username = result['lastfm_username']
            scrobbles = result['scrobbles']
            registered_at = result['registered_at']
            
            # Try to get fresh profile data
            data = await self.fetch_lastfm_data('user.getInfo', user=username)
            
            embed = discord.Embed(
                title=f"<:lastfm:1454165185831895264> {target_user.name}'s Last.fm Profile",
                color=0xFF0000
            )
            
            if data and 'user' in data:
                user_info = data['user']
                realname = user_info.get('realname') or username
                playcount = int(user_info.get('playcount', 0))
                country = user_info.get('country', 'Not set')
                
                cursor.execute("UPDATE lastfm_users SET scrobbles = ?, last_updated = CURRENT_TIMESTAMP WHERE discord_id = ?",
                              (playcount, target_user.id))
                self.db.commit()
                
                await self.cache_profile(username, user_info)
                
                embed.description = f"**{realname}**"
                embed.add_field(name="<:username:1454151270364483665> Username", value=username, inline=True)
                embed.add_field(name="<:graphic:1454167459220164650> Scrobbles", value=f"{playcount:,}", inline=True)
                embed.add_field(name="<:locationn:1454377274911490048> Country", value=country, inline=True)
                
                registered = user_info.get('registered', {}).get('#text', '')
                if registered:
                    try:
                        reg_timestamp = int(registered)
                        reg_date = datetime.fromtimestamp(reg_timestamp)
                        embed.add_field(name="<:Calendar:1454377207647703102> Joined Last.fm", value=reg_date.strftime('%b %d, %Y'), inline=True)
                    except:
                        pass
                
                image_data = user_info.get('image', [])
                if isinstance(image_data, list) and len(image_data) > 2:
                    avatar_url = image_data[-1].get('#text')
                    if avatar_url:
                        embed.set_thumbnail(url=avatar_url)
                
                profile_url = f"https://www.last.fm/user/{quote(username)}"
                embed.add_field(name="<:links:1454359084353585314> Profile", value=f"[Open on Last.fm]({profile_url})", inline=False)
                
                embed.set_footer(text=f"Linked on Discord: {registered_at}")
            else:
                embed.description = f"**{username}**"
                embed.add_field(name="<:username:1454151270364483665> Username", value=username, inline=True)
                embed.add_field(name="<:graphic:1454167459220164650> Scrobbles", value=f"{scrobbles:,}", inline=True)
                embed.add_field(name="<:Calendar:1454377207647703102> Linked on Discord", value=registered_at, inline=True)
                
                profile_url = f"https://www.last.fm/user/{quote(username)}"
                embed.add_field(name="<:links:1454359084353585314> Profile", value=f"[Open on Last.fm]({profile_url})", inline=False)
                embed.set_footer(text="Using cached data")
            
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in lastfm profile command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while fetching the Last.fm profile.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    @lastfm_group.command(name="login", aliases=['link', 'set'], help="Link your Last.fm account", usage="lastfm login <username>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_login(self, ctx, username: str):
        """Link Last.fm account to Discord"""
        try:
            if not LASTFM_API_KEY:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Last.fm API Not Configured",
                    description="Last.fm features are not configured.\nPlease add `LASTFM_API_KEY` to Fault.py",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            cursor = self.db.cursor()
            cursor.execute("SELECT lastfm_username FROM lastfm_users WHERE discord_id = ?", (ctx.author.id,))
            existing = cursor.fetchone()
            
            if existing:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Already Linked",
                    description=f"You already have Last.fm account **{existing['lastfm_username']}** linked.\nUse `{ctx.prefix}lastfm logout` to unlink first.",
                    color=0xFFA500
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            data = await self.fetch_lastfm_data('user.getInfo', user=username)
            
            if not data or 'error' in data:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | User Not Found",
                    description=f"Last.fm user **{username}** not found.\nMake sure you entered the correct username.",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            user_info = data.get('user', {})
            playcount = int(user_info.get('playcount', 0))
            
            cursor.execute("""
                INSERT INTO lastfm_users (discord_id, lastfm_username, scrobbles) 
                VALUES (?, ?, ?)
            """, (ctx.author.id, username, playcount))
            self.db.commit()
            
            await self.cache_profile(username, user_info)
            
            embed = discord.Embed(
                title="<:HadeTick:1454058805473050636> | Last.fm Account Linked",
                description=f"Successfully linked **{ctx.author.name}** to Last.fm account!",
                color=0xFF0000
            )
            
            realname = user_info.get('realname') or username
            embed.add_field(name="<:username:1454151270364483665> Username", value=realname, inline=True)
            embed.add_field(name="<:graphic:1454167459220164650> Total Scrobbles", value=f"{playcount:,}", inline=True)
            
            if user_info.get('country'):
                embed.add_field(name="<:locationn:1454377274911490048> Country", value=user_info['country'], inline=True)
            
            registered = user_info.get('registered', {}).get('#text', '')
            if registered:
                try:
                    reg_timestamp = int(registered)
                    reg_date = datetime.fromtimestamp(reg_timestamp)
                    embed.add_field(name="<:Calendar:1454377207647703102> Joined Last.fm", value=reg_date.strftime('%b %d, %Y'), inline=True)
                except:
                    pass
            
            image_data = user_info.get('image', [])
            if isinstance(image_data, list) and len(image_data) > 2:
                avatar_url = image_data[-1].get('#text')
                if avatar_url:
                    embed.set_thumbnail(url=avatar_url)
            
            profile_url = f"https://www.last.fm/user/{quote(username)}"
            embed.add_field(name="<:links:1454359084353585314> Profile", value=f"[Open on Last.fm]({profile_url})", inline=False)
            
            embed.set_footer(text=f"Use {ctx.prefix}lastfm profile to view your profile")
            
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in lastfm login command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while linking your Last.fm account.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    @lastfm_group.command(name="logout", aliases=['unlink', 'disconnect'], help="Unlink your Last.fm account", usage="lastfm logout")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_logout(self, ctx):
        """Unlink Last.fm account"""
        try:
            cursor = self.db.cursor()
            
            cursor.execute("SELECT lastfm_username FROM lastfm_users WHERE discord_id = ?", (ctx.author.id,))
            result = cursor.fetchone()
            
            if not result:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Not Linked",
                    description=f"You don't have a Last.fm account linked.\nUse `{ctx.prefix}lastfm login <username>` to link one.",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            username = result['lastfm_username']
            
            cursor.execute("DELETE FROM lastfm_users WHERE discord_id = ?", (ctx.author.id,))
            self.db.commit()
            
            embed = discord.Embed(
                title="<:HadeTick:1454058805473050636> | Last.fm Account Unlinked",
                description=f"Successfully unlinked **{ctx.author.name}** from Last.fm account **{username}**.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in lastfm logout command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while unlinking your Last.fm account.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    @lastfm_group.command(name="scrobble", aliases=['scrobbles', 'plays'], help="Show your scrobble count", usage="lastfm scrobble [@user]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_scrobble(self, ctx, user: discord.Member = None):
        """Show scrobble count"""
        try:
            target_user = user or ctx.author
            
            cursor = self.db.cursor()
            cursor.execute("SELECT lastfm_username, scrobbles FROM lastfm_users WHERE discord_id = ?", (target_user.id,))
            result = cursor.fetchone()
            
            if not result:
                if target_user == ctx.author:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Last.fm Account Linked",
                        description=f"You don't have a Last.fm account linked.\nUse `{ctx.prefix}lastfm login <username>` to link one.",
                        color=0xFF0000
                    )
                else:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Last.fm Account",
                        description=f"**{target_user.name}** doesn't have a Last.fm account linked.",
                        color=0xFF0000
                    )
                return await ctx.reply(embed=embed, mention_author=False)
            
            username = result['lastfm_username']
            cached_scrobbles = result['scrobbles']
            
            data = await self.fetch_lastfm_data('user.getInfo', user=username)
            
            if data and 'user' in data:
                user_info = data['user']
                playcount = int(user_info.get('playcount', 0))
                
                cursor.execute("UPDATE lastfm_users SET scrobbles = ?, last_updated = CURRENT_TIMESTAMP WHERE discord_id = ?",
                              (playcount, target_user.id))
                self.db.commit()
                
                embed = discord.Embed(
                    title=f"<:lastfm:1454165185831895264> {target_user.name}'s Scrobbles",
                    description=f"**{username}** has **{playcount:,}** scrobbles",
                    color=0xFF0000
                )
                
                registered = user_info.get('registered', {}).get('#text', '')
                if registered:
                    try:
                        reg_timestamp = int(registered)
                        reg_date = datetime.fromtimestamp(reg_timestamp)
                        days_since = (datetime.now() - reg_date).days
                        if days_since > 0:
                            per_day = playcount / days_since
                            embed.add_field(name="<:graphic:1454167459220164650> Scrobbles/Day", value=f"{per_day:.1f}", inline=True)
                    except:
                        pass
                
                image_data = user_info.get('image', [])
                if isinstance(image_data, list) and len(image_data) > 2:
                    avatar_url = image_data[-1].get('#text')
                    if avatar_url:
                        embed.set_thumbnail(url=avatar_url)
            else:
                embed = discord.Embed(
                    title=f"<:lastfm:1454165185831895264> {target_user.name}'s Scrobbles",
                    description=f"**{username}** has **{cached_scrobbles:,}** scrobbles",
                    color=0xFF0000
                )
            
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in lastfm scrobble command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while fetching scrobble data.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    @lastfm_group.command(name="np", aliases=['nowplaying', 'current'], help="Show currently playing track", usage="lastfm np [@user]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_nowplaying(self, ctx, user: discord.Member = None):
        """Show currently playing track"""
        try:
            target_user = user or ctx.author
            
            cursor = self.db.cursor()
            cursor.execute("SELECT lastfm_username FROM lastfm_users WHERE discord_id = ?", (target_user.id,))
            result = cursor.fetchone()
            
            if not result:
                if target_user == ctx.author:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Last.fm Account Linked",
                        description=f"You don't have a Last.fm account linked.\nUse `{ctx.prefix}lastfm login <username>` to link one.",
                        color=0xFF0000
                    )
                else:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Last.fm Account",
                        description=f"**{target_user.name}** doesn't have a Last.fm account linked.",
                        color=0xFF0000
                    )
                return await ctx.reply(embed=embed, mention_author=False)
            
            username = result['lastfm_username']
            
            data = await self.fetch_lastfm_data('user.getRecentTracks', user=username, limit=1)
            
            if not data or 'error' in data:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | API Error",
                    description="Could not fetch now playing data from Last.fm.",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            track_list = data.get('recenttracks', {}).get('track', [])
            
            if not track_list:
                embed = discord.Embed(
                    title="<:music_note:1454154237671112855> No Recent Tracks",
                    description=f"**{username}** hasn't scrobbled any tracks yet.",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            track = track_list[0]
            
            is_now_playing = False
            if isinstance(track, dict):
                if '@attr' in track:
                    if isinstance(track['@attr'], dict):
                        is_now_playing = track['@attr'].get('nowplaying') == 'true'
                    else:
                        is_now_playing = str(track['@attr']).lower() == 'true'
                elif 'date' not in track:
                    is_now_playing = True
            
            if isinstance(track, dict):
                track_name = track.get('name', 'Unknown Track')
                artist_data = track.get('artist', {})
                if isinstance(artist_data, dict):
                    artist_name = artist_data.get('#text', 'Unknown Artist')
                else:
                    artist_name = str(artist_data)
                
                album_data = track.get('album', {})
                if isinstance(album_data, dict):
                    album_name = album_data.get('#text', 'Unknown Album')
                else:
                    album_name = str(album_data)
            else:
                track_name = 'Unknown Track'
                artist_name = 'Unknown Artist'
                album_name = 'Unknown Album'
            
            embed = discord.Embed(
                color=0xFF0000
            )
            
            if is_now_playing:
                embed.title = "<:music_note:1454154237671112855> Now Playing"
                embed.description = f"**{username}** is currently listening to:"
                embed.set_thumbnail(url="https://i.imgur.com/4u7H5GQ.png")
            else:
                embed.title = "<:music:1454153742898171968> Last Played"
                embed.description = f"**{username}** last listened to:"
                
                date_data = track.get('date', {})
                if isinstance(date_data, dict) and '#text' in date_data:
                    embed.add_field(name="<:Clock:1454359440814903514> Last Played", value=date_data['#text'], inline=False)
                elif 'date' in track and track['date']:
                    embed.add_field(name="<:Clock:1454359440814903514> Last Played", value=str(track['date']), inline=False)
            
            embed.add_field(name="<:music_note:1454154237671112855> Track", value=track_name, inline=True)
            embed.add_field(name="<:Artist:1454359679345102979> Artist", value=artist_name, inline=True)
            
            if album_name and album_name != 'Unknown Album':
                embed.add_field(name="<:UEC_musicCD:1454358951243022356> Album", value=album_name, inline=True)
            
            image_data = track.get('image', [])
            if isinstance(image_data, list) and len(image_data) > 2:
                image_url = image_data[-2].get('#text')
                if image_url:
                    embed.set_thumbnail(url=image_url)
            
            track_url = f"https://www.last.fm/music/{quote(artist_name)}/_/{quote(track_name)}"
            embed.add_field(name="<:links:1454359084353585314> Track Link", value=f"[Open on Last.fm]({track_url})", inline=False)
            
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in lastfm np command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while fetching now playing data.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    @lastfm_group.command(name="topartists", aliases=['topa', 'artists'], help="Show top artists", usage="lastfm topartists [@user] [period]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_topartists(self, ctx, user: discord.Member = None, period: str = "overall"):
        """Show top artists"""
        try:
            target_user = user or ctx.author
            
            cursor = self.db.cursor()
            cursor.execute("SELECT lastfm_username FROM lastfm_users WHERE discord_id = ?", (target_user.id,))
            result = cursor.fetchone()
            
            if not result:
                if target_user == ctx.author:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Last.fm Account Linked",
                        description=f"You don't have a Last.fm account linked.\nUse `{ctx.prefix}lastfm login <username>` to link one.",
                        color=0xFF0000
                    )
                else:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Last.fm Account",
                        description=f"**{target_user.name}** doesn't have a Last.fm account linked.",
                        color=0xFF0000
                    )
                return await ctx.reply(embed=embed, mention_author=False)
            
            username = result['lastfm_username']
            
            valid_periods = {
                'overall': 'all time',
                '7day': 'last 7 days',
                '1month': 'last month',
                '3month': 'last 3 months',
                '6month': 'last 6 months',
                '12month': 'last year'
            }
            
            period = period.lower()
            if period not in valid_periods:
                period = 'overall'
            
            data = await self.fetch_lastfm_data('user.getTopArtists', user=username, period=period, limit=10)
            
            if not data or 'error' in data:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | API Error",
                    description="Could not fetch top artists from Last.fm.",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            top_artists = data.get('topartists', {}).get('artist', [])
            
            if not top_artists:
                embed = discord.Embed(
                    title="<:music_note:1454154237671112855> No Top Artists",
                    description=f"**{username}** has no top artists data for this period.",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            period_name = valid_periods[period]
            embed = discord.Embed(
                title=f"🎤 {username}'s Top Artists ({period_name})",
                color=0xFF0000
            )
            
            artist_list = ""
            for i, artist in enumerate(top_artists[:10], 1):
                name = artist.get('name', 'Unknown Artist')
                playcount = artist.get('playcount', 0)
                artist_list += f"`{i}.` **{name}** - {playcount} plays\n"
            
            embed.description = artist_list
            
            profile_data = await self.get_cached_profile(username)
            if profile_data and profile_data.get('avatar_url'):
                embed.set_thumbnail(url=profile_data['avatar_url'])
            
            embed.set_footer(text=f"Period: {period_name}")
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in lastfm topartists command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while fetching top artists.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    @lastfm_group.command(name="toptracks", aliases=['topt', 'tracks'], help="Show top tracks", usage="lastfm toptracks [@user] [period]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_toptracks(self, ctx, user: discord.Member = None, period: str = "overall"):
        """Show top tracks"""
        try:
            target_user = user or ctx.author
            
            cursor = self.db.cursor()
            cursor.execute("SELECT lastfm_username FROM lastfm_users WHERE discord_id = ?", (target_user.id,))
            result = cursor.fetchone()
            
            if not result:
                if target_user == ctx.author:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Last.fm Account Linked",
                        description=f"You don't have a Last.fm account linked.\nUse `{ctx.prefix}lastfm login <username>` to link one.",
                        color=0xFF0000
                    )
                else:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Last.fm Account",
                        description=f"**{target_user.name}** doesn't have a Last.fm account linked.",
                        color=0xFF0000
                    )
                return await ctx.reply(embed=embed, mention_author=False)
            
            username = result['lastfm_username']
            
            valid_periods = {
                'overall': 'all time',
                '7day': 'last 7 days',
                '1month': 'last month',
                '3month': 'last 3 months',
                '6month': 'last 6 months',
                '12month': 'last year'
            }
            
            period = period.lower()
            if period not in valid_periods:
                period = 'overall'
            
            data = await self.fetch_lastfm_data('user.getTopTracks', user=username, period=period, limit=10)
            
            if not data or 'error' in data:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | API Error",
                    description="Could not fetch top tracks from Last.fm.",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            top_tracks = data.get('toptracks', {}).get('track', [])
            
            if not top_tracks:
                embed = discord.Embed(
                    title="<:lastfm:1454165185831895264> No Top Tracks",
                    description=f"**{username}** has no top tracks data for this period.",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            period_name = valid_periods[period]
            embed = discord.Embed(
                title=f"<:lastfm:1454165185831895264> {username}'s Top Tracks ({period_name})",
                color=0xFF0000
            )
            
            track_list = ""
            for i, track in enumerate(top_tracks[:10], 1):
                name = track.get('name', 'Unknown Track')
                artist = track.get('artist', {}).get('name', 'Unknown Artist')
                playcount = track.get('playcount', 0)
                track_list += f"`{i}.` **{name}** by *{artist}* - {playcount} plays\n"
            
            embed.description = track_list
            
            profile_data = await self.get_cached_profile(username)
            if profile_data and profile_data.get('avatar_url'):
                embed.set_thumbnail(url=profile_data['avatar_url'])
            
            embed.set_footer(text=f"Period: {period_name}")
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in lastfm toptracks command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while fetching top tracks.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    @lastfm_group.command(name="compat", aliases=['compare', 'taste'], help="Compare music taste between users", usage="lastfm compat @user1 @user2")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def lastfm_compat(self, ctx, user1: discord.Member, user2: discord.Member = None):
        """Compare music taste between users - FIXED VERSION"""
        try:
            target_user2 = user2 or ctx.author
            
            cursor = self.db.cursor()
            
            cursor.execute("SELECT lastfm_username FROM lastfm_users WHERE discord_id = ?", (user1.id,))
            result1 = cursor.fetchone()
            
            cursor.execute("SELECT lastfm_username FROM lastfm_users WHERE discord_id = ?", (target_user2.id,))
            result2 = cursor.fetchone()
            
            if not result1 or not result2:
                missing_users = []
                if not result1:
                    missing_users.append(user1.name)
                if not result2:
                    missing_users.append(target_user2.name)
                
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Missing Last.fm Accounts",
                    description=f"The following users don't have Last.fm accounts linked:\n{', '.join(missing_users)}",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            username1 = result1['lastfm_username']
            username2 = result2['lastfm_username']
            
            # Use tasteometer.compare method with correct parameters
            data = await self.fetch_lastfm_data('tasteometer.compare', 
                                              type1='user', 
                                              value1=username1,
                                              type2='user', 
                                              value2=username2)
            
            if not data:
                # Try alternative method: get both users' top artists and compare manually
                embed = await self._manual_comparison(ctx, username1, username2, user1, target_user2)
                return await ctx.reply(embed=embed, mention_author=False)
            
            comparison = data.get('comparison', {})
            result = comparison.get('result', {})
            
            if 'error' in result or not result:
                # Fallback to manual comparison
                embed = await self._manual_comparison(ctx, username1, username2, user1, target_user2)
                return await ctx.reply(embed=embed, mention_author=False)
            
            score = float(result.get('score', 0)) * 100
            artists = result.get('artists', {}).get('artist', [])
            
            embed = discord.Embed(
                title="<:vs:1454165578485993685> Music Taste Comparison",
                color=0xFF0000
            )
            
            if score >= 80:
                emoji = "❤️"
                description = "Excellent match!"
            elif score >= 60:
                emoji = "💚"
                description = "Great match!"
            elif score >= 40:
                emoji = "💛"
                description = "Good match"
            elif score >= 20:
                emoji = "🧡"
                description = "Some common taste"
            else:
                emoji = "💔"
                description = "Not much in common"
            
            embed.add_field(name=f"{emoji} Compatibility Score", value=f"**{score:.1f}%**\n{description}", inline=False)
            
            if artists:
                common_artists = ", ".join([artist.get('name', 'Unknown') for artist in artists[:5]])
                embed.add_field(name="<:vs:1454165578485993685> Common Artists", value=common_artists, inline=False)
            
            embed.add_field(name="<:lastfm:1454165185831895264> User 1", value=f"{user1.mention} ({username1})", inline=True)
            embed.add_field(name="<:lastfm:1454165185831895264> User 2", value=f"{target_user2.mention} ({username2})", inline=True)
            
            if score >= 80:
                match_msg = "You should listen to music together! 🎵"
            elif score >= 60:
                match_msg = "You have similar music taste! 👍"
            elif score >= 40:
                match_msg = "You share some favorite artists! 🎤"
            else:
                match_msg = "You might discover new music from each other! 🎧"
            
            embed.set_footer(text=match_msg)
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in lastfm compat command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while comparing music taste.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    async def _manual_comparison(self, ctx, username1, username2, user1, user2):
        """Manual comparison when Last.fm API fails"""
        try:
            # Get top artists for both users
            data1 = await self.fetch_lastfm_data('user.getTopArtists', user=username1, period='overall', limit=50)
            data2 = await self.fetch_lastfm_data('user.getTopArtists', user=username2, period='overall', limit=50)
            
            if not data1 or not data2:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Comparison Failed",
                    description="Could not fetch user data for comparison.",
                    color=0xFF0000
                )
                return embed
            
            artists1 = data1.get('topartists', {}).get('artist', [])
            artists2 = data2.get('topartists', {}).get('artist', [])
            
            if not artists1 or not artists2:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Not Enough Data",
                    description="One or both users don't have enough listening data.",
                    color=0xFF0000
                )
                return embed
            
            # Get artist names
            artist_names1 = {artist.get('name', '').lower() for artist in artists1 if artist.get('name')}
            artist_names2 = {artist.get('name', '').lower() for artist in artists2 if artist.get('name')}
            
            # Find common artists
            common_artists = artist_names1.intersection(artist_names2)
            
            # Calculate compatibility score (based on overlap percentage)
            total_unique = len(artist_names1.union(artist_names2))
            if total_unique > 0:
                score = (len(common_artists) / total_unique) * 100
            else:
                score = 0
            
            embed = discord.Embed(
                title="<:vs:1454165578485993685> Music Taste Comparison",
                color=0xFF0000
            )
            
            if score >= 80:
                emoji = "❤️"
                description = "Excellent match!"
            elif score >= 60:
                emoji = "💚"
                description = "Great match!"
            elif score >= 40:
                emoji = "💛"
                description = "Good match"
            elif score >= 20:
                emoji = "🧡"
                description = "Some common taste"
            else:
                emoji = "💔"
                description = "Not much in common"
            
            embed.add_field(name=f"{emoji} Compatibility Score", value=f"**{score:.1f}%**\n{description}", inline=False)
            
            if common_artists:
                common_list = list(common_artists)[:5]
                common_display = ", ".join([artist.title() for artist in common_list])
                embed.add_field(name="🎤 Common Artists", value=common_display, inline=False)
            
            embed.add_field(name="<:lastfm:1454165185831895264> User 1", value=f"{user1.mention} ({username1})", inline=True)
            embed.add_field(name="<:lastfm:1454165185831895264> User 2", value=f"{user2.mention} ({username2})", inline=True)
            
            embed.set_footer(text="Comparison based on top 50 artists")
            return embed
            
        except Exception as e:
            print(f"❌ Error in manual comparison: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Comparison Failed",
                description="Could not compare music taste.",
                color=0xFF0000
            )
            return embed
    
    async def cog_unload(self):
        """Clean up on cog unload"""
        if self.session:
            await self.session.close()
        
        if self.db:
            self.db.close()


async def setup(client):
    """Setup function for the cog"""
    await client.add_cog(LastFM(client))