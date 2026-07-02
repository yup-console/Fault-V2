import discord
from discord.ext import commands
import sqlite3
import re
import asyncio
import aiohttp
import lavalink
from datetime import datetime

try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False
    print("⚠️ Spotipy not installed. Install with: pip install spotipy")


class Spotify(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.db = sqlite3.connect('databases/spotify.db', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self._init_database()
        
        # Initialize Spotify API
        self.spotify_api = None
        if SPOTIFY_AVAILABLE:
            self._init_spotify()
    
    def _init_database(self):
        """Initialize database tables"""
        cursor = self.db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spotify_users (
                discord_id INTEGER PRIMARY KEY,
                spotify_id TEXT NOT NULL,
                spotify_url TEXT NOT NULL,
                linked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS spotify_cache (
                spotify_id TEXT PRIMARY KEY,
                display_name TEXT,
                avatar_url TEXT,
                followers INTEGER,
                profile_url TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.db.commit()
        print("✅ Spotify database initialized")
    
    def _init_spotify(self):
        """Initialize Spotify API client"""
        try:
            import Fault
            
            if hasattr(Fault, 'SPOTIFY_CLIENT_ID') and hasattr(Fault, 'SPOTIFY_CLIENT_SECRET'):
                client_id = Fault.SPOTIFY_CLIENT_ID
                client_secret = Fault.SPOTIFY_CLIENT_SECRET
                
                if client_id and client_secret and client_id != 'your_spotify_client_id_here':
                    auth_manager = SpotifyClientCredentials(
                        client_id=client_id,
                        client_secret=client_secret
                    )
                    self.spotify_api = spotipy.Spotify(auth_manager=auth_manager)
                    print("✅ Spotify API initialized successfully")
                else:
                    print("⚠️ Spotify credentials not properly set in Fault.py")
            else:
                print("⚠️ Fault.py doesn't have Spotify credentials")
        except Exception as e:
            print(f"❌ Failed to initialize Spotify API: {e}")
            self.spotify_api = None
    
    @commands.Cog.listener()
    async def on_ready(self):
        print("Spotify Cog Is Ready")
    
    def get_lavalink(self):
        """Get Lavalink client from bot"""
        return self.client.lavalink
    
    async def get_player(self, ctx, create=False):
        """Get or create Lavalink player for guild"""
        lavalink_client = self.get_lavalink()
        if not lavalink_client:
            return None
        
        player = lavalink_client.player_manager.get(ctx.guild.id)
        if not player and create:
            player = lavalink_client.player_manager.create(ctx.guild.id)
            # Store channel ID for now playing embeds
            player.channel_id = ctx.channel.id
        
        return player
    
    async def connect_to_voice(self, ctx):
        """Connect bot to voice channel"""
        from main import LavalinkVoiceClient
        
        if not ctx.author.voice or not ctx.author.voice.channel:
            return False
        
        try:
            # Check if already connected
            if ctx.voice_client:
                # Already in same channel
                if ctx.voice_client.channel == ctx.author.voice.channel:
                    return True
                # In different channel, move
                await ctx.voice_client.move_to(ctx.author.voice.channel)
                return True
            
            # Connect to voice
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient, self_deaf=True)
            return True
        except Exception as e:
            print(f"❌ Voice connection error: {e}")
            return False
    
    def extract_spotify_id(self, url):
        """Extract Spotify user ID from URL"""
        try:
            # Remove query parameters and trailing slash
            url = url.split('?')[0].rstrip('/')
            
            # Different Spotify URL patterns
            patterns = [
                r'open\.spotify\.com/user/([^/?]+)',
                r'spotify\.com/user/([^/?]+)',
                r'spotify\.com:user:([^/?]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, url, re.IGNORECASE)
                if match:
                    return match.group(1)
            
            return None
        except:
            return None
    
    async def fetch_spotify_profile(self, spotify_id):
        """Fetch Spotify profile info from API"""
        if not self.spotify_api:
            return None
        
        try:
            user = self.spotify_api.user(spotify_id)
            if user:
                profile_data = {
                    'display_name': user.get('display_name', spotify_id),
                    'id': user['id'],
                    'followers': user.get('followers', {}).get('total', 0),
                    'url': user.get('external_urls', {}).get('spotify', f'https://open.spotify.com/user/{spotify_id}'),
                    'images': user.get('images', [])
                }
                return profile_data
        except Exception as e:
            print(f"❌ Error fetching Spotify profile: {e}")
        
        return None
    
    async def get_cached_profile(self, spotify_id):
        """Get cached Spotify profile - FIXED VERSION"""
        cursor = self.db.cursor()
        cursor.execute(
            "SELECT display_name, avatar_url, followers, profile_url, cached_at FROM spotify_cache WHERE spotify_id = ?",
            (spotify_id,)
        )
        result = cursor.fetchone()
        
        if result:
            try:
                # Check if cache is fresh (less than 24 hours old)
                cache_time_str = result['cached_at']
                if cache_time_str:
                    # Convert string timestamp to datetime object
                    cache_time = datetime.strptime(cache_time_str, '%Y-%m-%d %H:%M:%S')
                    current_time = datetime.now()
                    
                    # Calculate time difference
                    time_diff = current_time - cache_time
                    
                    if time_diff.total_seconds() < 86400:  # 24 hours in seconds
                        return {
                            'display_name': result['display_name'],
                            'avatar_url': result['avatar_url'],
                            'followers': result['followers'],
                            'profile_url': result['profile_url']
                        }
            except Exception as e:
                print(f"⚠️ Error checking cache freshness: {e}")
                # Return cached data anyway if there's an error
                return {
                    'display_name': result['display_name'],
                    'avatar_url': result['avatar_url'],
                    'followers': result['followers'],
                    'profile_url': result['profile_url']
                }
        
        return None
    
    async def cache_profile(self, spotify_id, profile_data):
        """Cache Spotify profile data"""
        cursor = self.db.cursor()
        
        # Get avatar URL if available
        avatar_url = None
        if profile_data.get('images') and len(profile_data['images']) > 0:
            avatar_url = profile_data['images'][0].get('url')
        
        cursor.execute("""
            INSERT OR REPLACE INTO spotify_cache 
            (spotify_id, display_name, avatar_url, followers, profile_url) 
            VALUES (?, ?, ?, ?, ?)
        """, (
            spotify_id,
            profile_data.get('display_name', spotify_id),
            avatar_url,
            profile_data.get('followers', 0),
            profile_data.get('url', f'https://open.spotify.com/user/{spotify_id}')
        ))
        self.db.commit()
    
    @commands.group(name="spotify", aliases=['sp'], invoke_without_command=True, help="Spotify commands - link, view profile, play playlists")
    async def spotify_group(self, ctx):
        """Spotify command group"""
        embed = discord.Embed(
            title="<:Spotify:1454149285439475712>  Spotify Commands",
            description="Connect your Spotify account and play music",
            color=0x1DB954
        )
        embed.add_field(
            name="<:Joined:1454050160073248871> Link Account", 
            value=f"`{ctx.prefix}spotify link <spotify_url>`\nLink your Spotify profile", 
            inline=False
        )
        embed.add_field(
            name="<:Profile:1454050322900058256> View Profile", 
            value=f"`{ctx.prefix}spotify profile [@user]`\nView Spotify profile info", 
            inline=False
        )
        embed.add_field(
            name="<:playlist:1454050403648929844> Play Playlists", 
            value=f"`{ctx.prefix}spotify playlist [@user]`\nBrowse and play Spotify playlists", 
            inline=False
        )
        embed.add_field(
            name="<:Leave:1454050272010571776> Unlink Account", 
            value=f"`{ctx.prefix}spotify unlink`\nUnlink your Spotify account", 
            inline=False
        )
        embed.set_footer(text="Your Spotify profile must be public for these commands to work")
        await ctx.reply(embed=embed, mention_author=False)
    
    @spotify_group.command(name="link", aliases=['login', 'connect'], help="Link your Spotify account", usage="spotify link <spotify_profile_url>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def spotify_link(self, ctx, spotify_url: str):
        """Link Spotify profile to Discord account"""
        try:
            # Extract Spotify ID from URL
            spotify_id = self.extract_spotify_id(spotify_url)
            
            if not spotify_id:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Invalid Spotify URL",
                    description="Please provide a valid Spotify profile URL.\n\n**Examples:**\n• `https://open.spotify.com/user/username`\n• `https://spotify.com/user/username`",
                    color=0xFF0000
                )
                embed.set_footer(text="Make sure your Spotify profile is public")
                return await ctx.reply(embed=embed, mention_author=False)
            
            # Check if already linked
            cursor = self.db.cursor()
            cursor.execute("SELECT spotify_id FROM spotify_users WHERE discord_id = ?", (ctx.author.id,))
            existing = cursor.fetchone()
            
            if existing:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Already Linked",
                    description=f"You already have Spotify account **{existing['spotify_id']}** linked.\nUse `{ctx.prefix}spotify unlink` to unlink first.",
                    color=0xFFA500
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            # Try to fetch profile to verify it exists
            profile_data = None
            if self.spotify_api:
                try:
                    profile_data = await self.fetch_spotify_profile(spotify_id)
                    if not profile_data:
                        embed = discord.Embed(
                            title="<:HadeCross:1454058806211514492> | Profile Not Found",
                            description="Could not find this Spotify profile.\nMake sure:\n1. The profile exists\n2. The profile is public\n3. You're using the correct username",
                            color=0xFF0000
                        )
                        return await ctx.reply(embed=embed, mention_author=False)
                    
                    # Cache the profile
                    await self.cache_profile(spotify_id, profile_data)
                except Exception as e:
                    print(f"<:HadeCross:1454058806211514492> | Could not verify profile: {e}")
                    # Still allow linking even if API fails
            
            # Link the account
            cursor.execute("""
                INSERT INTO spotify_users (discord_id, spotify_id, spotify_url) 
                VALUES (?, ?, ?)
            """, (ctx.author.id, spotify_id, spotify_url))
            self.db.commit()
            
            # Create success embed
            embed = discord.Embed(
                title="<:HadeTick:1454058805473050636> | Spotify Account Linked",
                description=f"Successfully linked **{ctx.author.name}** to Spotify account!",
                color=0x1DB954
            )
            
            if profile_data:
                embed.add_field(name="<:Spotify:1454149285439475712> Spotify Username", value=profile_data.get('display_name', spotify_id), inline=True)
                embed.add_field(name="<:followerso:1454151394855620841> Followers", value=f"{profile_data.get('followers', 0):,}", inline=True)
                
                # Add avatar if available
                if profile_data.get('images') and len(profile_data['images']) > 0:
                    embed.set_thumbnail(url=profile_data['images'][0]['url'])
            
            embed.add_field(name="<:Profile:1454050322900058256> Profile URL", value=f"[Open on Spotify](https://open.spotify.com/user/{spotify_id})", inline=False)
            embed.set_footer(text=f"Use {ctx.prefix}spotify profile to view your Spotify profile")
            
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in spotify link command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while linking your Spotify account.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    @spotify_group.command(name="unlink", aliases=['logout', 'disconnect'], help="Unlink your Spotify account", usage="spotify unlink")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def spotify_unlink(self, ctx):
        """Unlink Spotify profile from Discord account"""
        try:
            cursor = self.db.cursor()
            
            # Check if linked
            cursor.execute("SELECT spotify_id FROM spotify_users WHERE discord_id = ?", (ctx.author.id,))
            result = cursor.fetchone()
            
            if not result:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Not Linked",
                    description=f"You don't have a Spotify account linked.\nUse `{ctx.prefix}spotify link <spotify_url>` to link one.",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            spotify_id = result['spotify_id']
            
            # Unlink the account
            cursor.execute("DELETE FROM spotify_users WHERE discord_id = ?", (ctx.author.id,))
            self.db.commit()
            
            embed = discord.Embed(
                title="<:HadeTick:1454058805473050636> | Spotify Account Unlinked",
                description=f"Successfully unlinked **{ctx.author.name}** from Spotify account **{spotify_id}**.",
                color=0x1DB954
            )
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in spotify unlink command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while unlinking your Spotify account.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    @spotify_group.command(name="profile", aliases=['pr'], help="View Spotify profile", usage="spotify profile [@user]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def spotify_profile(self, ctx, user: discord.Member = None):
        """View Spotify profile of yourself or another user"""
        try:
            target_user = user or ctx.author
            
            # Get linked Spotify account
            cursor = self.db.cursor()
            cursor.execute("SELECT spotify_id, spotify_url FROM spotify_users WHERE discord_id = ?", (target_user.id,))
            result = cursor.fetchone()
            
            if not result:
                if target_user == ctx.author:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Spotify Account Linked",
                        description=f"You don't have a Spotify account linked.\nUse `{ctx.prefix}spotify link <spotify_url>` to link one.",
                        color=0xFF0000
                    )
                else:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Spotify Account",
                        description=f"**{target_user.name}** doesn't have a Spotify account linked.",
                        color=0xFF0000
                    )
                return await ctx.reply(embed=embed, mention_author=False)
            
            spotify_id = result['spotify_id']
            spotify_url = result['spotify_url']
            
            # Try to get cached profile first
            profile_data = await self.get_cached_profile(spotify_id)
            
            # If not cached or stale, fetch from API
            if not profile_data and self.spotify_api:
                api_data = await self.fetch_spotify_profile(spotify_id)
                if api_data:
                    await self.cache_profile(spotify_id, api_data)
                    profile_data = await self.get_cached_profile(spotify_id)
            
            # Create embed
            if profile_data:
                display_name = profile_data['display_name']
                followers = profile_data['followers']
                avatar_url = profile_data['avatar_url']
                profile_url = profile_data['profile_url']
                
                embed = discord.Embed(
                    title=f"<:Spotify:1454149285439475712>  {display_name}'s Spotify Profile",
                    color=0x1DB954
                )
                
                if avatar_url:
                    embed.set_thumbnail(url=avatar_url)
                else:
                    # Default Spotify avatar
                    embed.set_thumbnail(url="https://www.scdn.co/i/_global/favicon.png")
                
                embed.add_field(name="<:username:1454151270364483665> Username", value=spotify_id, inline=True)
                embed.add_field(name="<:followerso:1454151394855620841> Followers", value=f"{followers:,}", inline=True)
                embed.add_field(name="<:Profile:1454050322900058256> Profile", value=f"[Open on Spotify]({profile_url})", inline=False)
                
                # Add last linked time
                cursor.execute("SELECT linked_at FROM spotify_users WHERE discord_id = ?", (target_user.id,))
                linked_time_result = cursor.fetchone()
                if linked_time_result and linked_time_result['linked_at']:
                    linked_time = linked_time_result['linked_at']
                    embed.set_footer(text=f"Linked on {linked_time}")
                
            else:
                # Fallback if no profile data available
                embed = discord.Embed(
                    title=f"<:Spotify:1454149285439475712>  {target_user.name}'s Spotify Profile",
                    description=f"**Username:** {spotify_id}",
                    color=0x1DB954
                )
                embed.add_field(name="<:Profile:1454050322900058256> Profile URL", value=f"[Open on Spotify]({spotify_url})", inline=False)
                embed.set_footer(text="Profile data not available (API may be offline)")
            
            await ctx.reply(embed=embed, mention_author=False)
            
        except Exception as e:
            print(f"❌ Error in spotify profile command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while fetching the Spotify profile.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    @spotify_group.command(name="playlist", aliases=['pl'], help="Browse and play Spotify playlists", usage="spotify playlist [@user]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def spotify_playlist(self, ctx, user: discord.Member = None):
        """Browse Spotify playlists and play selected one"""
        try:
            if not self.spotify_api:
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Spotify API Not Available",
                    description="Spotify features are currently unavailable.\nPlease check if Spotify credentials are set in Fault.py",
                    color=0xFF0000
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            target_user = user or ctx.author
            
            # Get linked Spotify account
            cursor = self.db.cursor()
            cursor.execute("SELECT spotify_id FROM spotify_users WHERE discord_id = ?", (target_user.id,))
            result = cursor.fetchone()
            
            if not result:
                if target_user == ctx.author:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Spotify Account Linked",
                        description=f"You need to link a Spotify account first.\nUse `{ctx.prefix}spotify link <spotify_url>`",
                        color=0xFF0000
                    )
                else:
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Spotify Account",
                        description=f"**{target_user.name}** doesn't have a Spotify account linked.",
                        color=0xFF0000
                    )
                return await ctx.reply(embed=embed, mention_author=False)
            
            spotify_id = result['spotify_id']
            
            # Show loading message
            embed = discord.Embed(
                description="<a:loading:1454151640524390472> Fetching Spotify playlists...",
                color=0x1DB954
            )
            loading_msg = await ctx.reply(embed=embed, mention_author=False)
            
            try:
                # Fetch playlists
                playlists = self.spotify_api.user_playlists(spotify_id, limit=15)
                
                if not playlists or not playlists.get('items'):
                    embed = discord.Embed(
                        title="<:HadeCross:1454058806211514492> | No Playlists Found",
                        description=f"**{target_user.name}** has no public playlists.\n\nMake sure:\n1. Spotify profile is public\n2. You have at least one public playlist\n3. Try refreshing your playlists on Spotify",
                        color=0xFF0000
                    )
                    await loading_msg.edit(embed=embed)
                    return
                
                playlist_items = playlists['items']
                
                # Create selection embed
                playlist_text = ""
                for i, playlist in enumerate(playlist_items[:10], 1):
                    playlist_name = playlist['name']
                    track_count = playlist['tracks']['total']
                    is_public = "<:unlocked:1454151510161232094>" if playlist.get('public', False) else "<:locked:1454151508676444320>"
                    playlist_text += f"`{i}.` {is_public} **{playlist_name}** ({track_count} tracks)\n"
                
                # Get user display name
                profile_data = await self.get_cached_profile(spotify_id)
                display_name = profile_data['display_name'] if profile_data else target_user.name
                
                embed = discord.Embed(
                    title=f"<:Spotify:1454149285439475712>  {display_name}'s Playlists",
                    description=playlist_text,
                    color=0x1DB954
                )
                embed.set_footer(text="Reply with a number (1-10) to select, or 'cancel' to cancel")
                
                if profile_data and profile_data.get('avatar_url'):
                    embed.set_thumbnail(url=profile_data['avatar_url'])
                
                await loading_msg.edit(embed=embed)
                
                # Wait for user selection
                def check(m):
                    return m.author == ctx.author and m.channel == ctx.channel and (
                        m.content.lower() == 'cancel' or 
                        (m.content.isdigit() and 1 <= int(m.content) <= min(len(playlist_items), 10))
                    )
                
                try:
                    response = await self.client.wait_for('message', check=check, timeout=30.0)
                    
                    if response.content.lower() == 'cancel':
                        embed = discord.Embed(description="<:HadeCross:1454058806211514492> | Cancelled.", color=0x1DB954)
                        await ctx.reply(embed=embed, mention_author=False)
                        return
                    
                    selection = int(response.content) - 1
                    selected_playlist = playlist_items[selection]
                    
                    # Now handle playing the playlist
                    await self._play_spotify_playlist(ctx, loading_msg, selected_playlist, target_user)
                    
                except asyncio.TimeoutError:
                    embed = discord.Embed(description="<:HadeCross:1454058806211514492> | Selection timed out.", color=0x1DB954)
                    await ctx.reply(embed=embed, mention_author=False)
                
            except Exception as e:
                print(f"❌ Error fetching playlists: {e}")
                error_msg = str(e)
                if "unsupported operand type(s) for -" in error_msg:
                    error_msg = "API error: Invalid timestamp format. Please try again."
                
                embed = discord.Embed(
                    title="<:HadeCross:1454058806211514492> | Error",
                    description=f"Could not fetch playlists: {error_msg}",
                    color=0xFF0000
                )
                await loading_msg.edit(embed=embed)
                
        except Exception as e:
            print(f"❌ Error in spotify playlist command: {e}")
            embed = discord.Embed(
                title="<:HadeCross:1454058806211514492> | Error",
                description="An error occurred while accessing Spotify playlists.",
                color=0xFF0000
            )
            await ctx.reply(embed=embed, mention_author=False)
    
    async def _play_spotify_playlist(self, ctx, loading_msg, playlist, target_user):
        """Handle playing a Spotify playlist - NOW WITH PROPER LAVALINK"""
        try:
            # Update loading message
            embed = discord.Embed(
                description=f"<a:loading:1454151640524390472> Loading **{playlist['name']}** ({playlist['tracks']['total']} tracks)...",
                color=0x1DB954
            )
            await loading_msg.edit(embed=embed)
            
            # Check voice connection
            if not ctx.author.voice or not ctx.author.voice.channel:
                embed = discord.Embed(
                    description="<:HadeCross:1454058806211514492> | You must be in a voice channel to play music.",
                    color=0xFF0000
                )
                await loading_msg.edit(embed=embed)
                return
            
            # Check if Lavalink is available
            lavalink_client = self.get_lavalink()
            if not lavalink_client:
                embed = discord.Embed(
                    description="<:HadeCross:1454058806211514492> | Music system is not ready. Please try again in a moment.",
                    color=0xFF0000
                )
                await loading_msg.edit(embed=embed)
                return
            
            # Connect to voice channel
            if not await self.connect_to_voice(ctx):
                embed = discord.Embed(
                    description="<:HadeCross:1454058806211514492> | Could not connect to voice channel.",
                    color=0xFF0000
                )
                await loading_msg.edit(embed=embed)
                return
            
            # Get or create player
            player = await self.get_player(ctx, create=True)
            if not player:
                embed = discord.Embed(
                    description="<:HadeCross:1454058806211514492> | Could not create music player.",
                    color=0xFF0000
                )
                await loading_msg.edit(embed=embed)
                return
            
            # Fetch playlist tracks
            playlist_id = playlist['id']
            tracks = []
            
            try:
                results = self.spotify_api.playlist_tracks(playlist_id, limit=50)
                
                while results and len(tracks) < 20:  # Limit to 20 tracks for performance
                    for item in results['items']:
                        if len(tracks) >= 20:
                            break
                        
                        track = item['track']
                        if track:
                            track_name = track['name']
                            artists = ', '.join([artist['name'] for artist in track['artists']])
                            tracks.append(f"{track_name} {artists}")
                    
                    if results.get('next') and len(tracks) < 20:
                        results = self.spotify_api.next(results)
                    else:
                        break
            except Exception as e:
                print(f"❌ Error fetching playlist tracks: {e}")
                embed = discord.Embed(
                    description=f"<:HadeCross:1454058806211514492> | Error loading playlist tracks: {str(e)}",
                    color=0xFF0000
                )
                await loading_msg.edit(embed=embed)
                return
            
            if not tracks:
                embed = discord.Embed(
                    description=f"<:HadeCross:1454058806211514492> | **{playlist['name']}** has no playable tracks.",
                    color=0xFF0000
                )
                await loading_msg.edit(embed=embed)
                return
            
            # Add tracks to queue
            added = 0
            failed = 0
            added_tracks_info = []
            
            for i, track_query in enumerate(tracks):
                try:
                    # Update progress every 5 tracks
                    if i % 5 == 0:
                        embed.description = f"<a:loading:1454151640524390472> Loading **{playlist['name']}**... ({i+1}/{len(tracks)} tracks)"
                        await loading_msg.edit(embed=embed)
                    
                    # Search on YouTube using Lavalink
                    search_results = await player.node.get_tracks(f'ytsearch:{track_query}')
                    
                    if search_results and hasattr(search_results, 'tracks') and search_results.tracks:
                        track = search_results.tracks[0]
                        player.add(requester=ctx.author.id, track=track)
                        added += 1
                        added_tracks_info.append(track.title)
                    else:
                        failed += 1
                        
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.2)
                except Exception as e:
                    print(f"❌ Error adding track {track_query}: {e}")
                    failed += 1
            
            # Start playing if not already playing
            if added > 0 and not player.is_playing:
                try:
                    await player.play()
                    playing_status = "| <:music:1454153742898171968> Now playing!"
                except Exception as e:
                    print(f"❌ Error starting playback: {e}")
                    playing_status = "<:HadeCross:1454058806211514492> | Added to queue"
            elif added > 0:
                playing_status = "<:HadeTick:1454058805473050636> | Added to queue"
            else:
                playing_status = "<:HadeCross:1454058806211514492> | No tracks added"
            
            # Show results
            embed = discord.Embed(
                title="<:HadeTick:1454058805473050636> | Playlist Added",
                description=f"**{playlist['name']}** - {playing_status}",
                color=0x1DB954
            )
            embed.add_field(name="<:music_note:1454154237671112855> | Tracks Added", value=str(added), inline=True)
            embed.add_field(name="<:HadeCross:1454058806211514492> | Failed", value=str(failed), inline=True)
            
            if added > 0:
                success_rate = (added / len(tracks)) * 100
                embed.add_field(name="<:rate:1454153511188168825> | Success Rate", value=f"{success_rate:.1f}%", inline=True)
            
            # Show first few added tracks
            if added_tracks_info:
                first_tracks = "\n".join([f"• {track}" for track in added_tracks_info[:3]])
                if added > 3:
                    first_tracks += f"\n• ... and {added - 3} more"
                embed.add_field(name="<:HadeTick:1454058805473050636> | Added Tracks", value=first_tracks, inline=False)
            
            # Add playlist cover if available
            if playlist.get('images') and len(playlist['images']) > 0:
                embed.set_thumbnail(url=playlist['images'][0]['url'])
            
            await loading_msg.edit(embed=embed)
            
        except Exception as e:
            print(f"❌ Error playing playlist: {e}")
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | Error playing playlist: {str(e)}",
                color=0xFF0000
            )
            await loading_msg.edit(embed=embed)


async def setup(client):
    await client.add_cog(Spotify(client))