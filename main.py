import discord
import lavalink
import jishaku
from discord.ext import commands, tasks
import os
import asyncio
import sqlite3
import random

os.makedirs('databases', exist_ok=True)

con = sqlite3.connect('databases/settings.db', check_same_thread=False)
cur = con.cursor()
owner_con = sqlite3.connect('databases/owner.db', check_same_thread=False)
owner_cur = owner_con.cursor()

intents = discord.Intents.all()
intents.presences = False


def get_prefix(client, message):
    if not message.guild:
        return commands.when_mentioned_or('F')(client, message)
    
    try:
        cursor = con.execute(
            "SELECT prefix FROM Prefix WHERE guild_id = ?", (message.guild.id,))
        result = cursor.fetchone()
        
        if result is None:
            con.execute(
                "INSERT INTO Prefix(prefix, guild_id) VALUES(?, ?)", ('F', message.guild.id))
            con.commit()
            prefix = 'F'
        else:
            prefix = result[0]
        
        cursor = owner_con.execute("SELECT users FROM Np")
        np_users = cursor.fetchall()
        np_user_ids = [int(i[0]) for i in np_users] if np_users else []
        
        bot_mention = f'<@{client.user.id}>'
        bot_mention_nick = f'<@!{client.user.id}>'
        bot_mention_space = f'<@{client.user.id}> '
        bot_mention_nick_space = f'<@!{client.user.id}> '
        
        if message.author.id in np_user_ids:
            prefixes = [bot_mention_space, bot_mention_nick_space, bot_mention, bot_mention_nick, prefix, '']
            return prefixes
        else:
            prefixes = [bot_mention_space, bot_mention_nick_space, bot_mention, bot_mention_nick, prefix]
            return prefixes
    except Exception as e:
        print(f"Prefix error: {e}")
        return commands.when_mentioned_or('F')(client, message)


class LavalinkVoiceClient(discord.VoiceProtocol):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.client = client
        self.channel = channel
        self.guild_id = channel.guild.id
        self._destroyed = False
        self.lavalink = self.client.lavalink

    async def on_voice_server_update(self, data):
        lavalink_data = {'t': 'VOICE_SERVER_UPDATE', 'd': data}
        await self.lavalink.voice_update_handler(lavalink_data)

    async def on_voice_state_update(self, data):
        channel_id = data['channel_id']
        if not channel_id:
            await self._destroy()
            return
        self.channel = self.client.get_channel(int(channel_id))
        lavalink_data = {'t': 'VOICE_STATE_UPDATE', 'd': data}
        await self.lavalink.voice_update_handler(lavalink_data)

    async def connect(self, *, timeout: float, reconnect: bool, self_deaf: bool = False, self_mute: bool = False) -> None:
        self.lavalink.player_manager.create(guild_id=self.channel.guild.id)
        await self.channel.guild.change_voice_state(channel=self.channel, self_mute=self_mute, self_deaf=self_deaf)

    async def disconnect(self, *, force: bool = False) -> None:
        player = self.lavalink.player_manager.get(self.channel.guild.id)
        if not force and player and not player.is_connected:
            return
        await self.channel.guild.change_voice_state(channel=None)
        if player:
            player.channel_id = None
        await self._destroy()

    async def _destroy(self):
        self.cleanup()
        if self._destroyed:
            return
        self._destroyed = True
        try:
            await self.lavalink.player_manager.destroy(self.guild_id)
        except lavalink.errors.ClientError:
            pass


class Fault(commands.AutoShardedBot):
    def __init__(self):
        super().__init__(
            command_prefix=get_prefix,
            intents=intents,
            case_insensitive=True,
            strip_after_prefix=True,
            status=discord.Status.online
        )
        self.lavalink = None

    async def setup_hook(self):
        # Settings database tables
        cur.execute("CREATE TABLE IF NOT EXISTS Prefix(guild_id TEXT NOT NULL, prefix TEXT NOT NULL)")
        cur.execute("CREATE TABLE IF NOT EXISTS ignored_channels (guild_id INTEGER, channel_id INTEGER, PRIMARY KEY (guild_id, channel_id))")
        con.commit()
        
        # Owner database tables
        owner_cur.execute("CREATE TABLE IF NOT EXISTS Np(users TEXT)")
        owner_cur.execute("CREATE TABLE IF NOT EXISTS blacklist (user_id INTEGER PRIMARY KEY)")
        owner_cur.execute("CREATE TABLE IF NOT EXISTS Owner (user_id INTEGER PRIMARY KEY)")
        owner_con.commit()
        
        # Profile database tables
        profile_con = sqlite3.connect('databases/profile.db', check_same_thread=False)
        profile_cur = profile_con.cursor()
        profile_cur.execute("CREATE TABLE IF NOT EXISTS user_profiles (user_id INTEGER PRIMARY KEY, bio TEXT DEFAULT 'I love Fault')")
        profile_cur.execute("CREATE TABLE IF NOT EXISTS user_badges (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, badge_name TEXT NOT NULL, UNIQUE(user_id, badge_name))")
        profile_con.commit()
        
        # Music database tables
        music_con = sqlite3.connect('databases/music.db', check_same_thread=False)
        music_cur = music_con.cursor()
        music_cur.execute("""
            CREATE TABLE IF NOT EXISTS dj_roles (
                guild_id INTEGER,
                role_id INTEGER,
                PRIMARY KEY (guild_id, role_id)
            )
        """)
        music_cur.execute("""
            CREATE TABLE IF NOT EXISTS dj_users (
                guild_id INTEGER,
                user_id INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        """)
        music_cur.execute("""
            CREATE TABLE IF NOT EXISTS smart_vc_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER DEFAULT 0
            )
        """)
        music_cur.execute("""
            CREATE TABLE IF NOT EXISTS twentyfourseven_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
            )
        """)
        music_cur.execute("""
            CREATE TABLE IF NOT EXISTS autoplay_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER DEFAULT 0
            )
        """)
        music_cur.execute("""
            CREATE TABLE IF NOT EXISTS music_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
            )
        """)
        music_con.commit()
        print("Tables Initiated")
        
        for filename in os.listdir("./cogs"):
            if filename.endswith(".py"):
                try:
                    await self.load_extension(f"cogs.{filename[:-3]}")
                    print(f"Loaded: {filename}")
                except Exception as e:
                    print(f"Failed to load {filename}: {e}")


client = Fault()
shard_guild_counts = {}


@client.event
async def on_connect():
    await client.change_presence(
        status=discord.Status.idle,
        activity=discord.Activity(type=discord.ActivityType.listening, name="Fhelp || Fplay")
    )


@client.event
async def on_shard_ready(shard_id):
    guild_count = len(client.guilds)
    shard_guild_counts[shard_id] = guild_count
    print(f"Shard {shard_id} is ready and handling {guild_count} servers.")


@client.event
async def on_ready():
    if client.lavalink is None:
        await client.load_extension("jishaku")
        client.owner_ids = [901487880067776524]
        
        client.lavalink = lavalink.Client(client.user.id)
        client.lavalink.add_node(
            host='lavalink.jirayu.net',
            port=13592,
            password='youshallnotpass',
            region='us',
            name='Main-Node',
            ssl=False
        )
        
        client.lavalink.add_event_hooks(TrackEventHandler(client))
        
        cache_sweeper.start()
        print(f"Connected as {client.user}")
        print("Lavalink node added successfully")


class TrackEventHandler:
    def __init__(self, bot):
        self.bot = bot
        self.db = sqlite3.connect('databases/music.db', check_same_thread=False)
        self.last_track = {}
        self.played_tracks = {}
        self.music_channels = {}
        self.nowplaying_messages = {}
        self._init_tables()

    def _init_tables(self):
        """Initialize all necessary database tables"""
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS music_channels (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS autoplay_settings (
                guild_id INTEGER PRIMARY KEY,
                enabled INTEGER DEFAULT 0
            )
        """)
        self.db.execute("""
            CREATE TABLE IF NOT EXISTS twentyfourseven_settings (
                guild_id INTEGER PRIMARY KEY,
                channel_id INTEGER NOT NULL
            )
        """)
        self.db.commit()

    def get_music_channel(self, guild_id):
        cursor = self.db.execute(
            "SELECT channel_id FROM music_channels WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        return result[0] if result else None

    def set_music_channel(self, guild_id, channel_id):
        self.db.execute(
            "INSERT OR REPLACE INTO music_channels (guild_id, channel_id) VALUES (?, ?)",
            (guild_id, channel_id))
        self.db.commit()
        self.music_channels[guild_id] = channel_id

    def is_247_enabled(self, guild_id):
        cursor = self.db.execute(
            "SELECT channel_id FROM twentyfourseven_settings WHERE guild_id = ?", (guild_id,))
        return cursor.fetchone() is not None

    def is_autoplay_enabled(self, guild_id):
        cursor = self.db.execute(
            "SELECT enabled FROM autoplay_settings WHERE guild_id = ?", (guild_id,))
        result = cursor.fetchone()
        return result[0] == 1 if result else False

    def normalize_title(self, title):
        """Normalize track title for comparison"""
        if not title:
            return ""
        
        # Remove common YouTube suffixes
        suffixes = [
            ' (Official Video)', ' (Official Audio)', ' (Lyric Video)',
            ' (Official Music Video)', ' (Music Video)', ' (MV)',
            ' (Visualizer)', ' (Audio)', ' (Video)', 
            ' [Official Video]', ' [Official Audio]', ' [Lyric Video]',
            ' [Official Music Video]', ' [Music Video]', ' [MV]',
            ' [Visualizer]', ' [Audio]', ' [Video]',
            ' | Official Video', ' | Official Audio', ' | Lyric Video',
            ' ft.', ' ft ', ' featuring ', ' feat.', ' feat ',
            ' with ', ' x ', ' vs ', ' & ', ',',
            '【MV】', '【Official Video】', '【Audio】',
            '（MV）', '（Official Video）', '（Audio）'
        ]
        
        normalized = title
        for suffix in suffixes:
            normalized = normalized.replace(suffix, '')
        
        # Remove version tags in parentheses/brackets
        import re
        normalized = re.sub(r'\([^)]*\)', '', normalized)
        normalized = re.sub(r'\[[^\]]*\]', '', normalized)
        normalized = re.sub(r'【[^】]*】', '', normalized)
        normalized = re.sub(r'（[^）]*）', '', normalized)
        
        # Remove common version indicators
        version_keywords = [
            'remix', 'remastered', 'remaster', 'cover', 'live', 'acoustic',
            'piano', 'instrumental', 'orchestra', 'orchestral', 'version',
            'edit', 'mix', 'mashup', 'bootleg', 'rework', 'dub',
            'radio edit', 'single version', 'album version',
            'lofi', 'lo-fi', 'slowed', 'reverb', 'nightcore', 'sped up',
            'chill', 'soft', 'hard', 'club', 'dance', 'dj', 'tiktok',
            'shorts', 'clip', 'explicit', 'clean', 'demo', 'preview'
        ]
        
        words = normalized.lower().split()
        filtered_words = []
        for word in words:
            # Keep word only if it doesn't contain version keywords
            if not any(keyword in word for keyword in version_keywords):
                filtered_words.append(word)
        
        normalized = ' '.join(filtered_words)
        
        # Clean up extra spaces
        normalized = ' '.join(normalized.split())
        
        return normalized.strip().lower()

    def get_base_song_name(self, title, author):
        """Extract the base song name from track info"""
        if not title:
            return ""
        
        # Remove author name from title if present
        normalized_title = title.lower()
        if author:
            normalized_author = author.lower()
            if normalized_author in normalized_title:
                # Remove author and any separators
                normalized_title = normalized_title.replace(normalized_author, '')
                normalized_title = normalized_title.replace(' - ', ' ')
                normalized_title = normalized_title.replace('–', ' ')
        
        # Normalize the title
        return self.normalize_title(normalized_title)

    async def find_youtube_recommendation(self, track, player, played_track_ids):
        """Find a YouTube recommendation based on the current track"""
        if not track or not track.title:
            return None
        
        print(f"Autoplay: Finding recommendations for: {track.title}")
        
        # Extract song and artist info
        song_title = track.title
        song_author = track.author if hasattr(track, 'author') else ""
        
        # Get base song name (without versions)
        base_song = self.get_base_song_name(song_title, song_author)
        print(f"Autoplay: Base song name: {base_song}")
        
        # Strategy 1: Search by base song + "music" or "song"
        if base_song:
            search_queries = [
                f"ytsearch:{base_song} music",
                f"ytmsearch:{base_song} music",
                f"ytsearch:{base_song} song",
                f"ytmsearch:{base_song} song"
            ]
            
            if song_author and base_song:
                # Search with artist for related music
                search_queries.extend([
                    f"ytsearch:{song_author} music",
                    f"ytmsearch:{song_author} music",
                    f"ytsearch:similar to {song_author}",
                    f"ytmsearch:similar to {song_author}"
                ])
            
            for query in search_queries:
                try:
                    results = await player.node.get_tracks(query)
                    if results and hasattr(results, 'tracks') and results.tracks:
                        for candidate in results.tracks[:20]:  # Check first 20 results
                            # Skip if already played
                            if candidate.identifier in played_track_ids:
                                continue
                            
                            # Skip very short or very long tracks
                            if candidate.duration < 45000 or candidate.duration > 1200000:  # 45s to 20min
                                continue
                            
                            # Skip if it's a different version of the same song
                            candidate_base = self.get_base_song_name(
                                candidate.title, 
                                candidate.author if hasattr(candidate, 'author') else ""
                            )
                            
                            # Compare normalized titles
                            if candidate_base and base_song:
                                # If they share significant similarity, skip
                                words_base = set(base_song.split())
                                words_candidate = set(candidate_base.split())
                                common_words = words_base.intersection(words_candidate)
                                
                                # If more than 2 common words and it's not too short, skip
                                if len(common_words) >= 2 and len(words_base) > 2:
                                    print(f"Autoplay: Skipping similar track: {candidate.title}")
                                    continue
                            
                            # Check for unwanted content
                            candidate_lower = candidate.title.lower() if candidate.title else ""
                            unwanted_keywords = [
                                '#shorts', 'shorts', 'tiktok', 'clip', 
                                'tutorial', 'reaction', 'cover', 'remix',
                                'lofi', 'lo-fi', 'slowed', 'reverb', 
                                'nightcore', 'sped up', 'chill', 'soft',
                                'acoustic', 'piano', 'instrumental', 'dj',
                                'edit', 'mix', 'version', 'live at', 
                                'concert', 'performance'
                            ]
                            
                            if any(keyword in candidate_lower for keyword in unwanted_keywords):
                                continue
                            
                            # Check if it's by the same artist (good sign)
                            if song_author and candidate.author:
                                if song_author.lower() in candidate.author.lower():
                                    print(f"Autoplay: Found track by same artist: {candidate.title}")
                                    return candidate
                            
                            # Check if it contains common music indicators
                            music_indicators = ['official', 'video', 'audio', 'song', 'track', 'music']
                            indicator_count = sum(1 for indicator in music_indicators if indicator in candidate_lower)
                            
                            if indicator_count >= 1:
                                print(f"Autoplay: Found candidate: {candidate.title}")
                                return candidate
                
                except Exception as e:
                    print(f"Autoplay search error for '{query}': {e}")
                    continue
        
        # Strategy 2: If we have an artist, search for their popular tracks
        if song_author:
            try:
                results = await player.node.get_tracks(f"ytmsearch:{song_author} popular songs")
                if results and hasattr(results, 'tracks') and results.tracks:
                    for candidate in results.tracks[:15]:
                        if candidate.identifier in played_track_ids:
                            continue
                        
                        if candidate.duration < 45000 or candidate.duration > 1200000:
                            continue
                        
                        # Skip if it's the same song
                        if self.get_base_song_name(candidate.title, candidate.author) == base_song:
                            continue
                        
                        print(f"Autoplay: Found popular track: {candidate.title}")
                        return candidate
            except Exception as e:
                print(f"Autoplay popular search error: {e}")
        
        # Strategy 3: Generic music search
        try:
            # Try some generic music search terms
            generic_searches = [
                "ytsearch:popular music 2024",
                "ytsearch:trending music",
                "ytmsearch:top hits",
                "ytsearch:best songs",
                "ytmsearch:recommended music"
            ]
            
            for query in generic_searches:
                results = await player.node.get_tracks(query)
                if results and hasattr(results, 'tracks') and results.tracks:
                    for candidate in results.tracks[:10]:
                        if candidate.identifier in played_track_ids:
                            continue
                        
                        if candidate.duration < 45000 or candidate.duration > 1200000:
                            continue
                        
                        # Check for music indicators
                        candidate_lower = candidate.title.lower() if candidate.title else ""
                        if any(word in candidate_lower for word in ['official', 'video', 'audio']):
                            print(f"Autoplay: Found generic recommendation: {candidate.title}")
                            return candidate
        except Exception as e:
            print(f"Autoplay generic search error: {e}")
        
        return None

    @lavalink.listener(lavalink.events.TrackStartEvent)
    async def on_track_start(self, event: lavalink.events.TrackStartEvent):
        guild_id = event.player.guild_id
        track = event.track
        self.last_track[guild_id] = track
        
        # Add to played tracks
        if guild_id not in self.played_tracks:
            self.played_tracks[guild_id] = set()
        self.played_tracks[guild_id].add(track.identifier)
        
        # Keep only last 30 tracks
        if len(self.played_tracks[guild_id]) > 30:
            # Convert to list, keep last 30, convert back to set
            tracks_list = list(self.played_tracks[guild_id])
            self.played_tracks[guild_id] = set(tracks_list[-30:])
        
        # Send now playing message
        channel_id = self.music_channels.get(guild_id) or self.get_music_channel(guild_id)
        if channel_id:
            channel = self.bot.get_channel(channel_id)
            if channel:
                try:
                    duration_ms = track.duration
                    minutes, seconds = divmod(duration_ms // 1000, 60)
                    duration_str = f"{minutes:02d}m {seconds:02d}s"
                    
                    requester_id = track.requester if hasattr(track, 'requester') else None
                    if requester_id and requester_id != self.bot.user.id:
                        requester = self.bot.get_user(requester_id)
                        requester_text = requester.mention if requester else f"<@{requester_id}>"
                    else:
                        requester_text = "<@1419347731545329744>"
                    
                    embed = discord.Embed(
                        title="Now Playing",
                        description=f"[{track.title}]({track.uri})\n"
                                    f"Duration: {duration_str} - ({requester_text})",
                        color=0x2b2d31
                    )
                    
                    if hasattr(track, 'artwork_url') and track.artwork_url:
                        embed.set_thumbnail(url=track.artwork_url)
                    elif hasattr(track, 'identifier'):
                        embed.set_thumbnail(url=f"https://img.youtube.com/vi/{track.identifier}/hqdefault.jpg")
                    
                    # Delete previous now playing message
                    if guild_id in self.nowplaying_messages:
                        try:
                            old_msg = self.nowplaying_messages[guild_id]
                            await old_msg.delete()
                        except:
                            pass
                    
                    msg = await channel.send(embed=embed)
                    self.nowplaying_messages[guild_id] = msg
                except Exception as e:
                    print(f"Error sending now playing embed: {e}")

    @lavalink.listener(lavalink.events.TrackEndEvent)
    async def on_track_end(self, event: lavalink.events.TrackEndEvent):
        guild_id = event.player.guild_id
        
        # Delete now playing message
        if guild_id in self.nowplaying_messages:
            try:
                msg = self.nowplaying_messages[guild_id]
                await msg.delete()
                del self.nowplaying_messages[guild_id]
            except:
                pass

    @lavalink.listener(lavalink.events.QueueEndEvent)
    async def on_queue_end(self, event: lavalink.events.QueueEndEvent):
        guild_id = event.player.guild_id
        guild = self.bot.get_guild(guild_id)
        
        if not guild:
            return
        
        # Check if autoplay is enabled
        if self.is_autoplay_enabled(guild_id):
            track = self.last_track.get(guild_id)
            
            if track:
                print(f"Autoplay triggered for guild {guild_id}")
                
                try:
                    # Get played tracks for this guild
                    played_track_ids = self.played_tracks.get(guild_id, set())
                    
                    # Find a recommendation
                    next_track = await self.find_youtube_recommendation(track, event.player, played_track_ids)
                    
                    if next_track:
                        # Add the track to queue
                        event.player.add(requester=self.bot.user.id, track=next_track)
                        await event.player.play()
                        
                        # Add to played tracks
                        played_track_ids.add(next_track.identifier)
                        self.played_tracks[guild_id] = played_track_ids
                        
                        print(f"Autoplay: Added '{next_track.title}'")
                    else:
                        print(f"Autoplay: No suitable recommendations found")
                        
                        # Try to clear some history and search again
                        if len(played_track_ids) > 15:
                            # Keep only last 10 tracks
                            self.played_tracks[guild_id] = set(list(played_track_ids)[-10:])
                            print("Autoplay: Cleared old track history")
                        
                        # Try one more search with cleared history
                        if track:
                            next_track = await self.find_youtube_recommendation(track, event.player, self.played_tracks.get(guild_id, set()))
                            if next_track:
                                event.player.add(requester=self.bot.user.id, track=next_track)
                                await event.player.play()
                                self.played_tracks[guild_id].add(next_track.identifier)
                                print(f"Autoplay: Found track after clearing history: {next_track.title}")
                
                except Exception as e:
                    print(f"Autoplay error: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Disconnect if not 24/7 and no autoplay
        if not self.is_247_enabled(guild_id) and not self.is_autoplay_enabled(guild_id):
            if guild.voice_client:
                await guild.voice_client.disconnect(force=True)


@client.event
async def on_message(message):
    if message.author.bot:
        return
    
    if not message.guild:
        await client.process_commands(message)
        return
    
    cur.execute('SELECT * FROM ignored_channels WHERE channel_id = ?', (message.channel.id,))
    if cur.fetchone():
        return
    
    owner_cur.execute('SELECT * FROM blacklist WHERE user_id = ?', (message.author.id,))
    if owner_cur.fetchone():
        return
    
    await client.process_commands(message)


@tasks.loop(minutes=60)
async def cache_sweeper():
    client._connection._private_channels.clear()
    client._connection._users.clear()
    client._connection._messages.clear()
    print("Cleared Cache")


async def main():
    async with client:
        await client.start("TOKEN HERE")


if __name__ == "__main__":
    asyncio.run(main())