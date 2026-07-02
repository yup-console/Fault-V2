import discord
import lavalink
import sqlite3
import asyncio
import re
import os
from discord.ext import commands
import Fault
from cogs.owner import vote_required

# Try to import spotipy for Spotify support
try:
    import spotipy
    from spotipy.oauth2 import SpotifyClientCredentials
    SPOTIFY_AVAILABLE = True
except ImportError:
    SPOTIFY_AVAILABLE = False
    print("Spotipy not installed. Spotify features will be limited.")


class Music(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.color = Fault.color
        self.db = sqlite3.connect('databases/music.db', check_same_thread=False)
        self._init_tables()
        
        # Initialize Spotify client if available
        self.spotify = None
        if SPOTIFY_AVAILABLE:
            self._init_spotify()

    def _init_spotify(self):
        """Initialize Spotify client with credentials from Fault module"""
        try:
            # Check if Fault has Spotify credentials
            if hasattr(Fault, 'SPOTIFY_CLIENT_ID') and hasattr(Fault, 'SPOTIFY_CLIENT_SECRET'):
                client_id = Fault.SPOTIFY_CLIENT_ID
                client_secret = Fault.SPOTIFY_CLIENT_SECRET
                
                if client_id and client_secret and client_id != 'your_spotify_client_id_here':
                    auth_manager = SpotifyClientCredentials(
                        client_id=client_id,
                        client_secret=client_secret
                    )
                    self.spotify = spotipy.Spotify(auth_manager=auth_manager)
                    print("Spotify client initialized successfully from Fault.py")
                else:
                    print("Spotify credentials not properly set in Fault.py")
                    print("Please update SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in Fault.py")
                    self.spotify = None
            else:
                print("Fault.py doesn't have Spotify credentials")
                print("Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to Fault.py")
                self.spotify = None
        except Exception as e:
            print(f"Failed to initialize Spotify client: {e}")
            self.spotify = None

    def _init_tables(self):
        cursor = self.db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dj_roles (
                guild_id INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS dj_users (
                guild_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS smart_vc_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS twentyfourseven_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS autoplay_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER DEFAULT 0
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS music_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
            )
        """)
        self.db.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        print("Music Is Ready")
        await self.reconnect_247_guilds()

    async def reconnect_247_guilds(self):
        from main import LavalinkVoiceClient
        await asyncio.sleep(5)
        
        cursor = self.db.execute("SELECT guild_id, channel_id FROM twentyfourseven_settings")
        guilds_to_reconnect = cursor.fetchall()
        
        for guild_id, channel_id in guilds_to_reconnect:
            try:
                guild = self.client.get_guild(guild_id)
                if not guild:
                    continue
                    
                channel = guild.get_channel(channel_id)
                if not channel:
                    self.db.execute("DELETE FROM twentyfourseven_settings WHERE guild_id = ?", (guild_id,))
                    self.db.commit()
                    continue
                
                if guild.voice_client:
                    continue
                    
                await channel.connect(cls=LavalinkVoiceClient, self_deaf=True)
                print(f"24/7: Reconnected to {channel.name} in {guild.name}")
            except Exception as e:
                print(f"24/7 reconnect error for guild {guild_id}: {e}")

    def is_247_enabled(self, guild_id):
        cursor = self.db.execute(
            "SELECT channel_id FROM twentyfourseven_settings WHERE guild_id = ?", (guild_id,))
        return cursor.fetchone() is not None

    def is_autoplay_enabled(self, guild_id):
        cursor = self.db.execute(
            "SELECT enabled FROM autoplay_settings WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        return result[0] == 1 if result else False

    def is_smart_vc_enabled(self, guild_id):
        cursor = self.db.execute(
            "SELECT enabled FROM smart_vc_settings WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        return result[0] == 1 if result else False

    def has_dj_role(self, member):
        cursor = self.db.execute(
            "SELECT role_id FROM dj_roles WHERE guild_id = ?", (member.guild.id,))
        dj_roles = [row[0] for row in cursor.fetchall()]
        return any(role.id in dj_roles for role in member.roles)

    def is_dj_user(self, guild_id, user_id):
        cursor = self.db.execute(
            "SELECT user_id FROM dj_users WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id))
        return cursor.fetchone() is not None

    async def check_music_control(self, ctx, require_bot_connected=True):
        if require_bot_connected and not ctx.voice_client:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not in any voice channel.", colour=self.color)
            await ctx.reply(embed=embed, mention_author=False)
            return False

        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | You must be in a voice channel to use this command.", colour=self.color)
            await ctx.reply(embed=embed, mention_author=False)
            return False

        if ctx.voice_client and ctx.author.voice.channel == ctx.voice_client.channel:
            return True

        if ctx.voice_client and ctx.author.voice.channel != ctx.voice_client.channel:
            if self.is_smart_vc_enabled(ctx.guild.id):
                if ctx.author.guild_permissions.administrator:
                    return True
                if self.has_dj_role(ctx.author):
                    return True
                if self.is_dj_user(ctx.guild.id, ctx.author.id):
                    return True
            
            embed = discord.Embed(
                description="<:HadeCross:1453797650875809814> | You need to be in the same voice channel as me to control music.",
                colour=self.color
            )
            await ctx.reply(embed=embed, mention_author=False)
            return False

        return False

    async def ensure_voice(self, ctx):
        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | You are not in a voice channel.", colour=self.color)
            await ctx.reply(embed=embed, mention_author=False)
            return False
        return True

    async def get_player(self, ctx, create=False):
        if not self.client.lavalink:
            return None
        player = self.client.lavalink.player_manager.get(ctx.guild.id)
        if not player and create:
            player = self.client.lavalink.player_manager.create(ctx.guild.id)
        return player

    async def connect_to_voice(self, ctx):
        from main import LavalinkVoiceClient
        try:
            await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient, self_deaf=True)
            return True
        except Exception as e:
            print(f"Connection error: {e}")
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | Could not connect to voice channel.", colour=self.color)
            await ctx.reply(embed=embed, mention_author=False)
            return False

    def _store_music_channel(self, guild_id, channel_id):
        try:
            self.db.execute(
                "INSERT OR REPLACE INTO music_channels (guild_id, channel_id) VALUES (?, ?)",
                (guild_id, channel_id))
            self.db.commit()
        except Exception as e:
            print(f"Error storing music channel: {e}")

    def is_spotify_url(self, url):
        """Check if URL is a Spotify URL"""
        spotify_patterns = [
            r'open\.spotify\.com/',
            r'spotify\.com/',
            r'spotify\.link/'
        ]
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in spotify_patterns)

    def is_spotify_album(self, url):
        """Check if URL is a Spotify album"""
        album_patterns = [
            r'open\.spotify\.com/album/',
            r'spotify\.com/album/'
        ]
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in album_patterns)

    def is_spotify_track(self, url):
        """Check if URL is a Spotify track"""
        track_patterns = [
            r'open\.spotify\.com/track/',
            r'spotify\.com/track/'
        ]
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in track_patterns)

    def is_spotify_playlist(self, url):
        """Check if URL is a Spotify playlist"""
        playlist_patterns = [
            r'open\.spotify\.com/playlist/',
            r'spotify\.com/playlist/'
        ]
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in playlist_patterns)

    def is_youtube_playlist(self, url):
        """Check if URL is a YouTube playlist"""
        playlist_patterns = [
            r'youtube\.com/playlist\?list=',
            r'youtu\.be/playlist\?list='
        ]
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in playlist_patterns)

    def is_youtube_url(self, url):
        """Check if URL is a YouTube URL"""
        youtube_patterns = [
            r'youtube\.com/watch\?v=',
            r'youtu\.be/',
            r'youtube\.com/embed/',
            r'youtube\.com/shorts/',
            r'youtube\.com/playlist'
        ]
        return any(re.search(pattern, url, re.IGNORECASE) for pattern in youtube_patterns)

    async def get_spotify_track_info(self, url):
        """Get track info from Spotify URL"""
        if not self.spotify:
            return None
        
        try:
            track_id = self.extract_spotify_id(url)
            if not track_id:
                return None
            
            track = self.spotify.track(track_id)
            if not track:
                return None
            
            # Extract track information
            track_name = track['name']
            artists = ', '.join([artist['name'] for artist in track['artists']])
            
            return {
                'name': track_name,
                'artists': artists,
                'full_query': f"{track_name} {artists}",
                'duration_ms': track['duration_ms']
            }
        except Exception as e:
            print(f"Error getting Spotify track info: {e}")
            return None

    async def get_spotify_album_tracks(self, url):
        """Get all tracks from a Spotify album"""
        if not self.spotify:
            return None
        
        try:
            album_id = self.extract_spotify_id(url)
            if not album_id:
                return None
            
            tracks = []
            results = self.spotify.album_tracks(album_id)
            
            while results:
                for item in results['items']:
                    track_name = item['name']
                    artists = ', '.join([artist['name'] for artist in item['artists']])
                    tracks.append({
                        'name': track_name,
                        'artists': artists,
                        'full_query': f"{track_name} {artists}"
                    })
                
                if results['next']:
                    results = self.spotify.next(results)
                else:
                    break
            
            # Get album info for better display
            album_info = self.spotify.album(album_id)
            return {
                'tracks': tracks,
                'album_name': album_info.get('name', 'Unknown Album'),
                'artist_name': ', '.join([artist['name'] for artist in album_info.get('artists', [])])
            }
        except Exception as e:
            print(f"Error getting Spotify album tracks: {e}")
            return None

    async def search_spotify_for_track(self, query):
        """Search Spotify for a track and return the best match"""
        if not self.spotify:
            return None
        
        try:
            results = self.spotify.search(q=query, type='track', limit=5)
            tracks = results.get('tracks', {}).get('items', [])
            
            if tracks:
                # Return the first (most relevant) track
                track = tracks[0]
                track_name = track['name']
                artists = ', '.join([artist['name'] for artist in track['artists']])
                return {
                    'name': track_name,
                    'artists': artists,
                    'full_query': f"{track_name} {artists}",
                    'duration_ms': track['duration_ms'],
                    'spotify_url': track['external_urls']['spotify']
                }
        except Exception as e:
            print(f"Error searching Spotify: {e}")
        
        return None

    async def get_spotify_recommendations(self, track_info):
        """Get Spotify recommendations based on a track"""
        if not self.spotify:
            return []
        
        try:
            # Try to find the track on Spotify first
            search_results = self.spotify.search(q=f"{track_info['name']} {track_info['artists']}", type='track', limit=1)
            tracks = search_results.get('tracks', {}).get('items', [])
            
            if tracks:
                seed_track = tracks[0]['id']
                recommendations = self.spotify.recommendations(seed_tracks=[seed_track], limit=10)
                
                rec_tracks = []
                for track in recommendations['tracks']:
                    track_name = track['name']
                    artists = ', '.join([artist['name'] for artist in track['artists']])
                    rec_tracks.append({
                        'name': track_name,
                        'artists': artists,
                        'full_query': f"{track_name} {artists}"
                    })
                
                return rec_tracks
        except Exception as e:
            print(f"Error getting Spotify recommendations: {e}")
        
        return []

    async def get_spotify_playlist_tracks(self, url):
        """Get all tracks from a Spotify playlist"""
        if not self.spotify:
            return None
        
        try:
            playlist_id = self.extract_spotify_id(url)
            if not playlist_id:
                return None
            
            tracks = []
            results = self.spotify.playlist_tracks(playlist_id)
            
            while results:
                for item in results['items']:
                    track = item['track']
                    if track:
                        track_name = track['name']
                        artists = ', '.join([artist['name'] for artist in track['artists']])
                        tracks.append({
                            'name': track_name,
                            'artists': artists,
                            'full_query': f"{track_name} {artists}"
                        })
                
                if results['next']:
                    results = self.spotify.next(results)
                else:
                    break
            
            return tracks
        except Exception as e:
            print(f"Error getting Spotify playlist tracks: {e}")
            return None

    def extract_spotify_id(self, url):
        """Extract ID from Spotify URL"""
        try:
            # Remove query parameters
            url = url.split('?')[0]
            
            # Extract ID from various Spotify URL formats
            if '/track/' in url:
                return url.split('/track/')[-1].split('/')[0]
            elif '/playlist/' in url:
                return url.split('/playlist/')[-1].split('/')[0]
            elif '/album/' in url:
                return url.split('/album/')[-1].split('/')[0]
            elif '/artist/' in url:
                return url.split('/artist/')[-1].split('/')[0]
        except:
            return None
        return None

    async def search_youtube_for_track(self, query):
        """Search YouTube for a track"""
        if not self.client.lavalink:
            return None
        
        try:
            # Get any player just for searching
            player = self.client.lavalink.player_manager.create(0)
            results = await player.node.get_tracks(f'ytsearch:{query}')
            
            if results and hasattr(results, 'tracks') and results.tracks:
                return results.tracks[0]
        except Exception as e:
            print(f"Error searching YouTube: {e}")
        
        return None

    async def handle_spotify_album(self, ctx, player, url):
        """Handle Spotify album"""
        try:
            # Show loading message
            embed = discord.Embed(
                description="<a:loading:1453982243633758228> | Fetching album info from Spotify...",
                colour=self.color
            )
            loading_msg = await ctx.reply(embed=embed, mention_author=False)
            
            # Get album tracks from Spotify
            album_data = await self.get_spotify_album_tracks(url)
            if not album_data or len(album_data['tracks']) == 0:
                embed = discord.Embed(
                    description="<:HadeCross:1453797650875809814> | Could not fetch album from Spotify. Please check if Spotify credentials are set in Fault.py",
                    colour=self.color
                )
                await loading_msg.edit(embed=embed)
                return
            
            tracks = album_data['tracks']
            album_name = album_data['album_name']
            artist_name = album_data['artist_name']
            
            # Update loading message
            embed.description = f"<:HadeTick:1453797563701395608> | Found album **{album_name}** by **{artist_name}** with {len(tracks)} tracks. Searching on YouTube..."
            await loading_msg.edit(embed=embed)
            
            added_count = 0
            failed_count = 0
            
            # Process tracks in batches to avoid timeout
            for i, track_info in enumerate(tracks[:25]):  # Limit to 25 tracks for albums
                try:
                    # Search YouTube for the track
                    youtube_track = await self.search_youtube_for_track(track_info['full_query'])
                    
                    if youtube_track:
                        player.add(requester=ctx.author.id, track=youtube_track)
                        added_count += 1
                    else:
                        failed_count += 1
                    
                    # Update progress every 5 tracks
                    if i % 5 == 0:
                        embed.description = f"<a:loading:1453982243633758228> | Processing album... {i+1}/{min(len(tracks), 25)} tracks"
                        await loading_msg.edit(embed=embed)
                        
                except Exception as e:
                    failed_count += 1
                    print(f"Error processing track {track_info['name']}: {e}")
            
            # Start playing if not already playing
            if not player.is_playing and added_count > 0:
                await player.play()
            
            # Final message
            embed.description = f"<:HadeTick:1453797563701395608> | Added {added_count} tracks from album **{album_name}** by **{artist_name}** to queue"
            if failed_count > 0:
                embed.description += f"\n<:HadeCross:1453797650875809814> | Failed to add {failed_count} tracks"
            
            await loading_msg.edit(embed=embed)
            
        except Exception as e:
            print(f"Spotify album error: {e}")
            embed = discord.Embed(
                description=f"<:HadeCross:1453797650875809814> | Error processing Spotify album: {str(e)}",
                colour=self.color
            )
            try:
                await ctx.reply(embed=embed, mention_author=False)
            except:
                pass

    async def handle_spotify_track(self, ctx, player, url):
        """Handle Spotify track"""
        try:
            # Show loading message
            embed = discord.Embed(
                description="Fetching track info from Spotify...",
                colour=self.color
            )
            loading_msg = await ctx.reply(embed=embed, mention_author=False)
            
            # Get track info from Spotify
            track_info = await self.get_spotify_track_info(url)
            if not track_info:
                embed = discord.Embed(
                    description="<:HadeCross:1453797650875809814> | Could not fetch track info from Spotify. Please check if Spotify credentials are set in Fault.py",
                    colour=self.color
                )
                await loading_msg.edit(embed=embed)
                return
            
            # Update loading message
            embed.description = f"<:search:1453982306581745828> | Searching for: **{track_info['name']}** by **{track_info['artists']}**"
            await loading_msg.edit(embed=embed)
            
            # Search YouTube for the track
            youtube_track = await self.search_youtube_for_track(track_info['full_query'])
            
            if not youtube_track:
                embed = discord.Embed(
                    description=f"<:HadeCross:1453797650875809814> | Could not find **{track_info['name']}** on YouTube.",
                    colour=self.color
                )
                await loading_msg.edit(embed=embed)
                return
            
            # Add to queue
            player.add(requester=ctx.author.id, track=youtube_track)
            
            if not player.is_playing:
                await player.play()
                embed = discord.Embed(
                    description=f"<:HadeTick:1453797563701395608> | Now playing: **{youtube_track.title}** (Originally: {track_info['name']} by {track_info['artists']})",
                    colour=self.color
                )
            else:
                embed = discord.Embed(
                    description=f"<:HadeTick:1453797563701395608> | Added to queue: **{youtube_track.title}** (Originally: {track_info['name']} by {track_info['artists']})",
                    colour=self.color
                )
            
            await loading_msg.edit(embed=embed)
            
        except Exception as e:
            print(f"Spotify track error: {e}")
            embed = discord.Embed(
                description=f"<:HadeCross:1453797650875809814> | Error processing Spotify track: {str(e)}",
                colour=self.color
            )
            try:
                await ctx.reply(embed=embed, mention_author=False)
            except:
                pass

    async def handle_spotify_playlist(self, ctx, player, url):
        """Handle Spotify playlist"""
        try:
            # Show loading message
            embed = discord.Embed(
                description="<a:loading:1453982243633758228> | Fetching playlist info from Spotify...",
                colour=self.color
            )
            loading_msg = await ctx.reply(embed=embed, mention_author=False)
            
            # Get playlist tracks from Spotify
            tracks = await self.get_spotify_playlist_tracks(url)
            if not tracks or len(tracks) == 0:
                embed = discord.Embed(
                    description="<:HadeCross:1453797650875809814> | Could not fetch playlist from Spotify. Please check if Spotify credentials are set in Fault.py",
                    colour=self.color
                )
                await loading_msg.edit(embed=embed)
                return
            
            # Update loading message
            embed.description = f"<:HadeTick:1453797563701395608> | Found {len(tracks)} tracks. Searching on YouTube..."
            await loading_msg.edit(embed=embed)
            
            added_count = 0
            failed_count = 0
            
            # Process tracks in batches to avoid timeout
            for i, track_info in enumerate(tracks[:50]):  # Limit to 50 tracks
                try:
                    # Search YouTube for the track
                    youtube_track = await self.search_youtube_for_track(track_info['full_query'])
                    
                    if youtube_track:
                        player.add(requester=ctx.author.id, track=youtube_track)
                        added_count += 1
                    else:
                        failed_count += 1
                    
                    # Update progress every 10 tracks
                    if i % 10 == 0:
                        embed.description = f"<a:loading:1453982243633758228> | Processing playlist... {i+1}/{min(len(tracks), 50)} tracks"
                        await loading_msg.edit(embed=embed)
                        
                except Exception as e:
                    failed_count += 1
                    print(f"Error processing track {track_info['name']}: {e}")
            
            # Start playing if not already playing
            if not player.is_playing and added_count > 0:
                await player.play()
            
            # Final message
            embed.description = f"<:HadeTick:1453797563701395608> | Added {added_count} tracks from Spotify playlist to queue"
            if failed_count > 0:
                embed.description += f"\n<:HadeCross:1453797650875809814> | Failed to add {failed_count} tracks"
            
            await loading_msg.edit(embed=embed)
            
        except Exception as e:
            print(f"Spotify playlist error: {e}")
            embed = discord.Embed(
                description=f"<:HadeCross:1453797650875809814> | Error processing Spotify playlist: {str(e)}",
                colour=self.color
            )
            try:
                await ctx.reply(embed=embed, mention_author=False)
            except:
                pass

    async def handle_youtube_playlist(self, ctx, player, url):
        """Handle YouTube playlist"""
        try:
            results = await player.node.get_tracks(url)
            
            if not results or not hasattr(results, 'tracks') or not results.tracks:
                embed = discord.Embed(description='<:HadeCross:1453797650875809814> | Could not load YouTube playlist.', colour=self.color)
                return await ctx.reply(embed=embed, mention_author=False)
            
            tracks = results.tracks
            loaded_count = 0
            
            for track in tracks:
                player.add(requester=ctx.author.id, track=track)
                loaded_count += 1
            
            if not player.is_playing:
                await player.play()
            
            embed = discord.Embed(
                description=f"<:HadeTick:1453797563701395608> | Added {loaded_count} tracks from YouTube playlist to queue.",
                colour=self.color
            )
            await ctx.reply(embed=embed, mention_author=False)
                
        except Exception as e:
            print(f"YouTube playlist error: {e}")
            embed = discord.Embed(
                description="<:HadeCross:1453797650875809814> | An error occurred while loading the YouTube playlist.",
                colour=self.color
            )
            await ctx.reply(embed=embed, mention_author=False)

    @commands.group(name="smartvc", invoke_without_command=True, help="Smart VC control settings")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def smartvc(self, ctx):
        enabled = self.is_smart_vc_enabled(ctx.guild.id)
        status = "enabled" if enabled else "disabled"
        
        cursor = self.db.execute(
            "SELECT role_id FROM dj_roles WHERE guild_id = ?", (ctx.guild.id,))
        dj_roles = [ctx.guild.get_role(row[0]) for row in cursor.fetchall()]
        dj_roles = [r.mention for r in dj_roles if r]
        
        cursor = self.db.execute(
            "SELECT user_id FROM dj_users WHERE guild_id = ?", (ctx.guild.id,))
        dj_users = [ctx.guild.get_member(row[0]) for row in cursor.fetchall()]
        dj_users = [u.mention for u in dj_users if u]
        
        embed = discord.Embed(title="Smart VC Settings", color=self.color)
        embed.add_field(name="Status", value=status.capitalize(), inline=False)
        embed.add_field(name="DJ Roles", value=", ".join(dj_roles) if dj_roles else "None set", inline=False)
        embed.add_field(name="DJ Users", value=", ".join(dj_users) if dj_users else "None set", inline=False)
        embed.set_footer(text="Use &smartvc enable/disable, &smartvc addrole/removerole, &smartvc adduser/removeuser")
        await ctx.reply(embed=embed, mention_author=False)

    @smartvc.command(name="enable", help="Enable smart VC recognition")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def smartvc_enable(self, ctx):
        self.db.execute(
            "INSERT OR REPLACE INTO smart_vc_settings (guild_id, enabled) VALUES (?, 1)",
            (ctx.guild.id,))
        self.db.commit()
        embed = discord.Embed(
            description="<:HadeTick:1453797563701395608> | Smart VC recognition enabled! DJ roles/users can now control music from any voice channel.",
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @smartvc.command(name="disable", help="Disable smart VC recognition")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def smartvc_disable(self, ctx):
        self.db.execute(
            "INSERT OR REPLACE INTO smart_vc_settings (guild_id, enabled) VALUES (?, 0)",
            (ctx.guild.id,))
        self.db.commit()
        embed = discord.Embed(
            description="<:HadeTick:1453797563701395608> | Smart VC recognition disabled. Users must be in the same VC to control music.",
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @smartvc.command(name="addrole", help="Add a DJ role")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def smartvc_addrole(self, ctx, role: discord.Role):
        try:
            self.db.execute(
                "INSERT OR IGNORE INTO dj_roles (guild_id, role_id) VALUES (?, ?)",
                (ctx.guild.id, role.id))
            self.db.commit()
            embed = discord.Embed(
                description=f"<:HadeTick:1453797563701395608> | {role.mention} has been added as a DJ role.",
                color=self.color
            )
        except Exception as e:
            embed = discord.Embed(description=f"<:HadeCross:1453797650875809814> | Error adding role: {e}", color=self.color)
        await ctx.reply(embed=embed, mention_author=False)

    @smartvc.command(name="removerole", help="Remove a DJ role")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def smartvc_removerole(self, ctx, role: discord.Role):
        self.db.execute(
            "DELETE FROM dj_roles WHERE guild_id = ? AND role_id = ?",
            (ctx.guild.id, role.id))
        self.db.commit()
        embed = discord.Embed(
            description=f"<:HadeTick:1453797563701395608> | {role.mention} has been removed from DJ roles.",
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @smartvc.command(name="adduser", help="Add a DJ user")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def smartvc_adduser(self, ctx, user: discord.Member):
        try:
            self.db.execute(
                "INSERT OR IGNORE INTO dj_users (guild_id, user_id) VALUES (?, ?)",
                (ctx.guild.id, user.id))
            self.db.commit()
            embed = discord.Embed(
                description=f"<:HadeTick:1453797563701395608> | {user.mention} has been added as a DJ user.",
                color=self.color
            )
        except Exception as e:
            embed = discord.Embed(description=f"<:HadeCross:1453797650875809814> | Error adding user: {e}", color=self.color)
        await ctx.reply(embed=embed, mention_author=False)

    @smartvc.command(name="removeuser", help="Remove a DJ user")
    @commands.has_permissions(administrator=True)
    @commands.guild_only()
    async def smartvc_removeuser(self, ctx, user: discord.Member):
        self.db.execute(
            "DELETE FROM dj_users WHERE guild_id = ? AND user_id = ?",
            (ctx.guild.id, user.id))
        self.db.commit()
        embed = discord.Embed(
            description=f"<:HadeTick:1453797563701395608> | {user.mention} has been removed from DJ users.",
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['p'], help="Play music from Spotify or YouTube! Spotify search is prioritized.", usage="play <query/link>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def play(self, ctx, *, query):
        if not await self.ensure_voice(ctx):
            return

        if ctx.voice_client:
            if ctx.author.voice.channel != ctx.voice_client.channel:
                if self.is_smart_vc_enabled(ctx.guild.id):
                    if not (ctx.author.guild_permissions.administrator or 
                            self.has_dj_role(ctx.author) or 
                            self.is_dj_user(ctx.guild.id, ctx.author.id)):
                        embed = discord.Embed(
                            description="<:HadeCross:1453797650875809814> | You need to be in the same voice channel as me to control music.",
                            colour=self.color
                        )
                        return await ctx.reply(embed=embed, mention_author=False)
                else:
                    embed = discord.Embed(
                        description="<:HadeCross:1453797650875809814> | You need to be in the same voice channel as me to control music.",
                        colour=self.color
                    )
                    return await ctx.reply(embed=embed, mention_author=False)
        else:
            if not await self.connect_to_voice(ctx):
                return

        try:
            self._store_music_channel(ctx.guild.id, ctx.channel.id)
            
            player = await self.get_player(ctx, create=True)
            if not player:
                embed = discord.Embed(description="<:HadeCross:1453797650875809814> | Music system is not ready. Please try again.", colour=self.color)
                return await ctx.reply(embed=embed, mention_author=False)

            # Check if query is a Spotify album
            if self.is_spotify_album(query):
                return await self.handle_spotify_album(ctx, player, query)
            
            # Check if query is a Spotify track
            elif self.is_spotify_track(query):
                return await self.handle_spotify_track(ctx, player, query)
            
            # Check if query is a Spotify playlist
            elif self.is_spotify_playlist(query):
                return await self.handle_spotify_playlist(ctx, player, query)
            
            # Check if query is a YouTube playlist
            elif self.is_youtube_playlist(query):
                return await self.handle_youtube_playlist(ctx, player, query)
            
            # Check if query is a YouTube URL
            elif self.is_youtube_url(query):
                results = await player.node.get_tracks(query)
            else:
                # For search queries, try YouTube first, then fallback to Spotify
                    # Try YouTube search directly
                    results = await player.node.get_tracks(f'ytsearch:{query}')

                    # If YouTube search returned nothing, try Spotify -> then search YouTube for the Spotify result
                    if not results or not hasattr(results, 'tracks') or not results.tracks:
                        spotify_result = None
                        if self.spotify:
                            try:
                                # Show loading message for Spotify search
                                embed = discord.Embed(
                                    description="<:search:1453982306581745828> | No results on YouTube, searching Spotify...",
                                    colour=self.color
                                )
                                loading_msg = await ctx.reply(embed=embed, mention_author=False)

                                spotify_result = await self.search_spotify_for_track(query)

                                if spotify_result:
                                    # Update loading message and search YouTube for the Spotify match
                                    embed.description = f"<:HadeTick:1453797563701395608> | Found on Spotify: **{spotify_result['name']}** by **{spotify_result['artists']}**. Searching YouTube..."
                                    await loading_msg.edit(embed=embed)

                                    youtube_track = await self.search_youtube_for_track(spotify_result['full_query'])
                                    if youtube_track:
                                        player.add(requester=ctx.author.id, track=youtube_track)
                                        if not player.is_playing:
                                            await player.play()
                                            embed = discord.Embed(
                                                description=f"<:HadeTick:1453797563701395608> | Now playing: **{youtube_track.title}** (Found via Spotify: {spotify_result['name']} by {spotify_result['artists']})",
                                                colour=self.color
                                            )
                                        else:
                                            embed = discord.Embed(
                                                description=f"<:HadeTick:1453797563701395608> | Added to queue: **{youtube_track.title}** (Found via Spotify: {spotify_result['name']} by {spotify_result['artists']})",
                                                colour=self.color
                                            )
                                        await loading_msg.edit(embed=embed)
                                        return
                                    else:
                                        # Spotify returned a track but we couldn't find it on YouTube
                                        embed.description = f"<:HadeCross:1453797650875809814> | Found on Spotify but could not find on YouTube: **{spotify_result['name']}** by **{spotify_result['artists']}**"
                                        await loading_msg.edit(embed=embed)
                            except Exception as e:
                                print(f"Spotify search error: {e}")
                            finally:
                                # Clean up loading message if it exists
                                if 'loading_msg' in locals():
                                    try:
                                        await loading_msg.delete()
                                    except:
                                        pass

            if not results or not hasattr(results, 'tracks') or not results.tracks:
                embed = discord.Embed(description='<:HadeCross:1453797650875809814> | No songs found with that query.', colour=self.color)
                return await ctx.reply(embed=embed, mention_author=False)

            # Handle multiple tracks (playlist or search results)
            if hasattr(results, 'loadType'):
                if results.loadType == 'PLAYLIST_LOADED':
                    tracks = results.tracks
                    for track in tracks:
                        player.add(requester=ctx.author.id, track=track)
                    
                    if not player.is_playing:
                        await player.play()
                    
                    embed = discord.Embed(
                        description=f"<:HadeTick:1453797563701395608> | Added {len(tracks)} tracks to queue.",
                        colour=self.color
                    )
                    return await ctx.reply(embed=embed, mention_author=False)
                elif results.loadType == 'SEARCH_RESULT' or results.loadType == 'TRACK_LOADED':
                    tracks = results.tracks
                else:
                    tracks = results.tracks
            else:
                tracks = results.tracks

            # Handle single track
            if not tracks:
                embed = discord.Embed(description='<:HadeCross:1453797650875809814> | No songs found with that query.', colour=self.color)
                return await ctx.reply(embed=embed, mention_author=False)

            track = tracks[0]
            player.add(requester=ctx.author.id, track=track)

            if not player.is_playing:
                await player.play()
                embed = discord.Embed(description=f"<:HadeTick:1453797563701395608> | Now playing: **{track.title}**", colour=self.color)
            else:
                embed = discord.Embed(description=f"<:HadeTick:1453797563701395608> | Added to queue: **{track.title}**", colour=self.color)

            await ctx.reply(embed=embed, mention_author=False)
        except Exception as e:
            print(f"Play command error: {e}")
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | An error occurred while playing music.", colour=self.color)
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['wait'], help="Pause The Playing Music!", usage="pause")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def pause(self, ctx):
        if not await self.check_music_control(ctx):
            return

        player = await self.get_player(ctx)
        if not player or not player.is_playing:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not playing anything.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        await player.set_pause(True)
        embed = discord.Embed(description="<:HadeTick:1453797563701395608> | Paused the player.", colour=self.color)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['begin'], help="Resume the Current Music!", usage="resume")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def resume(self, ctx):
        if not await self.check_music_control(ctx):
            return

        player = await self.get_player(ctx)
        if not player:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not playing anything.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        if player.paused:
            await player.set_pause(False)
            embed = discord.Embed(description="<:HadeTick:1453797563701395608> | Resumed the player.", colour=self.color)
        else:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | Player is not paused.", colour=self.color)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['stp'], help="Stop the music and clear the queue", usage="stop")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def stop(self, ctx):
        if not await self.check_music_control(ctx):
            return

        if not ctx.voice_client:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        player = await self.get_player(ctx)
        if player:
            player.queue.clear()
            await player.stop()
            embed = discord.Embed(description="<:HadeTick:1453797563701395608> | Stopped the music and cleared the queue.", colour=self.color)
        else:
            embed = discord.Embed(description="<:HadeTick:1453797563701395608> | Stopped the music.", colour=self.color)
        
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['q'], help="Look Into The Queue", usage="queue")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def queue(self, ctx):
        if not ctx.voice_client:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        player = await self.get_player(ctx)
        if not player or not player.is_playing:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        queue_tracks = list(player.queue)
        if not queue_tracks:
            track_list = "Queue is empty"
        else:
            track_list = '\n'.join(f'`{num}.` {track.title}' for num, track in enumerate(queue_tracks, start=1))

        current = player.current
        if current:
            embed = discord.Embed(
                description=f'**Now Playing:** {current.title}\n\n**Queue:**\n{track_list}',
                color=self.color
            )
        else:
            embed = discord.Embed(description="Nothing is playing.", color=self.color)

        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['qremove', 'qr'], help="Remove a track from queue by number", usage="queueremove <number>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def queueremove(self, ctx, number: int):
        if not await self.check_music_control(ctx):
            return

        player = await self.get_player(ctx)
        if not player:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        if not player.is_playing:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not playing anything.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        queue_tracks = list(player.queue)
        if not queue_tracks:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | Queue is empty.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        if number < 1 or number > len(queue_tracks):
            embed = discord.Embed(
                description=f"<:HadeCross:1453797650875809814> | Please provide a valid queue number (1-{len(queue_tracks)}).",
                colour=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        # Remove the track (queue index is 0-based)
        removed_track = player.queue.pop(number - 1)
        
        embed = discord.Embed(
            description=f"<:HadeTick:1453797563701395608> | Removed track **{removed_track.title}** from queue.",
            colour=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['vol'], help="Change The Volume", usage="volume <0-200>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def volume(self, ctx, volume: int):
        if not await self.check_music_control(ctx):
            return

        player = await self.get_player(ctx)
        if not player:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not playing anything.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        if not 0 <= volume <= 200:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | Volume must be between 0 and 200.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        await player.set_volume(volume)
        embed = discord.Embed(description=f"<:HadeTick:1453797563701395608> | Volume set to {volume}%", colour=self.color)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['s'], help="Plays The Next Track", usage="skip")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def skip(self, ctx):
        if not await self.check_music_control(ctx):
            return

        player = await self.get_player(ctx)
        if not player:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        if not player.is_playing:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not playing anything.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        await player.skip()
        embed = discord.Embed(description="<:HadeTick:1453797563701395608> | Skipped the current song.", colour=self.color)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['cq'], help="Clears The Queue", usage="clearqueue")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def clearqueue(self, ctx):
        if not await self.check_music_control(ctx):
            return

        player = await self.get_player(ctx)
        if not player:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        if not player.is_playing:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not playing anything.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        player.queue.clear()
        embed = discord.Embed(description="<:HadeTick:1453797563701395608> | Successfully cleared the queue.", colour=self.color)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['j'], help="Joins The VC", usage="join")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def join(self, ctx):
        if not await self.ensure_voice(ctx):
            return

        if ctx.voice_client:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am already in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        if await self.connect_to_voice(ctx):
            embed = discord.Embed(description="<:HadeTick:1453797563701395608> | Successfully joined your voice channel.", colour=self.color)
            await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['dc'], help="Disconnect from the voice channel", usage="disconnect")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def disconnect(self, ctx):
        if not await self.check_music_control(ctx):
            return

        if not ctx.voice_client:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        player = await self.get_player(ctx)
        if player:
            player.queue.clear()
            await player.stop()

        if self.is_247_enabled(ctx.guild.id):
            embed = discord.Embed(
                description="<:HadeCross:1453797650875809814> | 24/7 mode is enabled. Disable 247 first, or use forceleave to override.",
                colour=self.color
            )
        else:
            await ctx.voice_client.disconnect(force=True)
            embed = discord.Embed(description="<:HadeTick:1453797563701395608> | Successfully disconnected from the voice channel.", colour=self.color)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['fl'], help="Force leave VC (overrides 24/7 mode)", usage="forceleave")
    @commands.has_permissions(administrator=True)
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def forceleave(self, ctx):
        if not ctx.voice_client:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not in any voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        player = await self.get_player(ctx)
        if player:
            player.queue.clear()
            await player.stop()

        self.db.execute("DELETE FROM twentyfourseven_settings WHERE guild_id = ?", (ctx.guild.id,))
        self.db.commit()

        await ctx.voice_client.disconnect(force=True)
        embed = discord.Embed(description="<:HadeTick:1453797563701395608> | Force left the voice channel and disabled 24/7 mode.", colour=self.color)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['nowp'], help="Shows What's Playing", usage="nowplaying")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def nowplaying(self, ctx):
        if not ctx.voice_client:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not in a voice channel.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        player = await self.get_player(ctx)
        if not player or not player.current:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | I am not playing any song.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        track = player.current
        
        duration_ms = track.duration
        minutes, seconds = divmod(duration_ms // 1000, 60)
        duration_str = f"{minutes:02d}m {seconds:02d}s"
        
        requester_id = track.requester if hasattr(track, 'requester') else None
        if requester_id and requester_id != self.client.user.id:
            requester = self.client.get_user(requester_id)
            requester_text = requester.mention if requester else f"<@{requester_id}>"
        else:
            requester_text = "<@1419347731545329744>"
        
        embed = discord.Embed(
            title="Now Playing",
            description=f"[{track.title}]({track.uri})\nDuration: {duration_str} - ({requester_text})",
            color=self.color
        )
        
        if hasattr(track, 'artwork_url') and track.artwork_url:
            embed.set_thumbnail(url=track.artwork_url)
        elif hasattr(track, 'identifier'):
            embed.set_thumbnail(url=f"https://img.youtube.com/vi/{track.identifier}/hqdefault.jpg")
        
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="247", aliases=['twentyfourseven'], help="Toggle 24/7 mode - bot stays in VC (Vote required or use vote bypass)", usage="247")
    @vote_required()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def twentyfourseven(self, ctx):
        if not await self.check_music_control(ctx):
            return

        if self.is_247_enabled(ctx.guild.id):
            self.db.execute("DELETE FROM twentyfourseven_settings WHERE guild_id = ?", (ctx.guild.id,))
            self.db.commit()
            embed = discord.Embed(
                description="<a:disabled1:1453797823198789653> | 24/7 mode has been disabled. I will now leave the voice channel when the queue ends.",
                color=self.color
            )
        else:
            if not ctx.author.voice or not ctx.author.voice.channel:
                embed = discord.Embed(
                    description="<:HadeCross:1453797650875809814> | You must be in a voice channel to enable 24/7 mode.",
                    color=self.color
                )
                return await ctx.reply(embed=embed, mention_author=False)
            
            channel_id = ctx.author.voice.channel.id
            
            if not ctx.voice_client:
                if not await self.connect_to_voice(ctx):
                    return
            
            self.db.execute(
                "INSERT OR REPLACE INTO twentyfourseven_settings (guild_id, channel_id) VALUES (?, ?)",
                (ctx.guild.id, channel_id)
            )
            self.db.commit()
            embed = discord.Embed(
                description=f"<a:enabled:1453797767364346048> | 24/7 mode has been enabled! I will stay in <#{channel_id}> and reconnect after restarts.",
                color=self.color
            )
        
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(name="autoplay", aliases=['ap'], help="Toggle autoplay mode - automatically plays Spotify recommendations (Vote required or use vote bypass)", usage="autoplay")
    @vote_required()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def autoplay(self, ctx):
        if not await self.check_music_control(ctx):
            return

        if self.is_autoplay_enabled(ctx.guild.id):
            self.db.execute(
                "INSERT OR REPLACE INTO autoplay_settings (guild_id, enabled) VALUES (?, 0)",
                (ctx.guild.id,)
            )
            self.db.commit()
            embed = discord.Embed(
                description="<a:disabled1:1453797823198789653> | Autoplay mode has been disabled. The bot will stop when the queue is empty.",
                color=self.color
            )
        else:
            self.db.execute(
                "INSERT OR REPLACE INTO autoplay_settings (guild_id, enabled) VALUES (?, 1)",
                (ctx.guild.id,)
            )
            self.db.commit()
            embed = discord.Embed(
                description="<a:enabled:1453797767364346048> | Autoplay mode has been enabled! The bot will automatically play Spotify recommendations when the queue is empty.",
                color=self.color
            )
        
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['find'], help="Search for songs and select one to play (Vote required or use vote bypass)", usage="search <query>")
    @vote_required()
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def search(self, ctx, *, query: str):
        if not self.client.lavalink:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | Music system is not ready. Please try again.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        player = await self.get_player(ctx, create=True)
        if not player:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | Music system is not ready. Please try again.", colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        results = await player.node.get_tracks(f'ytsearch:{query}')

        if not results or not hasattr(results, 'tracks') or not results.tracks:
            embed = discord.Embed(description='<:HadeCross:1453797650875809814> | No songs found with that query.', colour=self.color)
            return await ctx.reply(embed=embed, mention_author=False)

        tracks = results.tracks[:10]
        
        track_list = []
        for i, track in enumerate(tracks, 1):
            duration_ms = track.duration
            minutes, seconds = divmod(duration_ms // 1000, 60)
            duration_str = f"{minutes:02d}m {seconds:02d}s"
            track_list.append(f"`{i}.` **{track.title}** `{duration_str}`")

        embed = discord.Embed(
            title=f"<:search:1453982306581745828> | Search Results for: {query}",
            description="\n".join(track_list),
            color=self.color
        )
        embed.set_footer(text="Reply with a number (1-10) to select a song, or 'cancel' to cancel.")
        
        search_msg = await ctx.reply(embed=embed, mention_author=False)

        def check(m):
            return m.author == ctx.author and m.channel == ctx.channel and (
                m.content.lower() == 'cancel' or (m.content.isdigit() and 1 <= int(m.content) <= len(tracks))
            )

        try:
            response = await self.client.wait_for('message', check=check, timeout=30.0)
            
            if response.content.lower() == 'cancel':
                embed = discord.Embed(description="<:HadeTick:1453797563701395608> | Search cancelled.", colour=self.color)
                await ctx.reply(embed=embed, mention_author=False)
                return

            selection = int(response.content) - 1
            selected_track = tracks[selection]

            if not ctx.author.voice or not ctx.author.voice.channel:
                embed = discord.Embed(description="<:HadeCross:1453797650875809814> | You must be in a voice channel to play music.", colour=self.color)
                return await ctx.reply(embed=embed, mention_author=False)

            if ctx.voice_client:
                if ctx.author.voice.channel != ctx.voice_client.channel:
                    if self.is_smart_vc_enabled(ctx.guild.id):
                        if not (ctx.author.guild_permissions.administrator or 
                                self.has_dj_role(ctx.author) or 
                                self.is_dj_user(ctx.guild.id, ctx.author.id)):
                            embed = discord.Embed(
                                description="<:HadeCross:1453797650875809814> | You need to be in the same voice channel as me to control music.",
                                colour=self.color
                            )
                            return await ctx.reply(embed=embed, mention_author=False)
                    else:
                        embed = discord.Embed(
                            description="<:HadeCross:1453797650875809814> | You need to be in the same voice channel as me to control music.",
                            colour=self.color
                        )
                        return await ctx.reply(embed=embed, mention_author=False)
            else:
                if not await self.connect_to_voice(ctx):
                    return

            self._store_music_channel(ctx.guild.id, ctx.channel.id)
            
            player.add(requester=ctx.author.id, track=selected_track)

            if not player.is_playing:
                await player.play()
                embed = discord.Embed(description=f"<:HadeTick:1453797563701395608> | Now playing: **{selected_track.title}**", colour=self.color)
            else:
                embed = discord.Embed(description=f"<:HadeTick:1453797563701395608> | Added to queue: **{selected_track.title}**", colour=self.color)

            await ctx.reply(embed=embed, mention_author=False)

        except asyncio.TimeoutError:
            embed = discord.Embed(description="<:HadeCross:1453797650875809814> | Search timed out. Please try again.", colour=self.color)
            await ctx.reply(embed=embed, mention_author=False)


async def setup(client):
    await client.add_cog(Music(client))