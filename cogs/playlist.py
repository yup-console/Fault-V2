import discord
import sqlite3
import lavalink
from discord.ext import commands
import Fault


class Playlist(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.color = Fault.color
        self.db = sqlite3.connect('databases/playlist.db', check_same_thread=False)
        self._init_tables()

    def _init_tables(self):
        cursor = self.db.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, name)
            )
        """)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlist_songs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                playlist_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                duration INTEGER DEFAULT 0,
                added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE
            )
        """)
        self.db.commit()

    @commands.Cog.listener()
    async def on_ready(self):
        print("Playlist Is Ready")

    def get_playlist(self, user_id, name):
        cursor = self.db.execute(
            "SELECT id, name FROM playlists WHERE user_id = ? AND LOWER(name) = LOWER(?)",
            (user_id, name)
        )
        return cursor.fetchone()

    def get_user_playlists(self, user_id):
        cursor = self.db.execute(
            "SELECT id, name FROM playlists WHERE user_id = ?",
            (user_id,)
        )
        return cursor.fetchall()

    def get_playlist_songs(self, playlist_id):
        cursor = self.db.execute(
            "SELECT id, title, url, duration FROM playlist_songs WHERE playlist_id = ? ORDER BY id",
            (playlist_id,)
        )
        return cursor.fetchall()

    @commands.group(name="playlist", aliases=['pl'], invoke_without_command=True, help="Manage your personal playlists")
    @commands.cooldown(1, 3, commands.BucketType.user)
    async def playlist(self, ctx):
        embed = discord.Embed(
            title="Playlist Commands",
            description=(
                f"`{ctx.prefix}playlist create <name>` - Create a new playlist\n"
                f"`{ctx.prefix}playlist add <name> [song]` - Add a song (or current playing) to playlist\n"
                f"`{ctx.prefix}playlist remove <name> <number/name>` - Remove a song by position or name\n"
                f"`{ctx.prefix}playlist rename <old> <new>` - Rename a playlist\n"
                f"`{ctx.prefix}playlist list` - View all your playlists\n"
                f"`{ctx.prefix}playlist view <name>` - View songs in a playlist\n"
                f"`{ctx.prefix}playlist delete <name>` - Delete a playlist\n"
                f"`{ctx.prefix}playlist play <name>` - Play a playlist\n"
                f"`{ctx.prefix}playlist clear <name>` - Clear all songs from playlist"
            ),
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @playlist.command(name="create", help="Create a new playlist", usage="playlist create <name>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def playlist_create(self, ctx, *, name: str):
        if len(name) > 50:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | Playlist name must be 50 characters or less.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlists = self.get_user_playlists(ctx.author.id)
        if len(playlists) >= 10:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | You can only have up to 10 playlists.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        try:
            self.db.execute(
                "INSERT INTO playlists (user_id, name) VALUES (?, ?)",
                (ctx.author.id, name)
            )
            self.db.commit()
            embed = discord.Embed(
                description=f"<:HadeTick:1454058805473050636> | Successfully created playlist **{name}**!",
                color=self.color
            )
        except sqlite3.IntegrityError:
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | You already have a playlist named **{name}**.",
                color=self.color
            )
        await ctx.reply(embed=embed, mention_author=False)

    @playlist.command(name="add", help="Add a song to your playlist (or current song if none specified)", usage="playlist add <name> [song]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def playlist_add(self, ctx, name: str, *, query=None):
        playlist = self.get_playlist(ctx.author.id, name)
        if not playlist:
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | You don't have a playlist named **{name}**.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlist_id = playlist[0]

        songs = self.get_playlist_songs(playlist_id)
        if len(songs) >= 50:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | A playlist can only have up to 50 songs.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if not self.client.lavalink:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | Music system is not ready. Please try again later.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        try:
            player = self.client.lavalink.player_manager.get(ctx.guild.id) if ctx.guild else None
            
            if query is None:
                if not player or not player.current:
                    embed = discord.Embed(
                        description="<:HadeCross:1454058806211514492> | No song is currently playing. Specify a song to add or play something first.",
                        color=self.color
                    )
                    return await ctx.reply(embed=embed, mention_author=False)
                
                track = player.current
                self.db.execute(
                    "INSERT INTO playlist_songs (playlist_id, title, url, duration) VALUES (?, ?, ?, ?)",
                    (playlist_id, track.title, track.uri, track.duration)
                )
                self.db.commit()
                
                embed = discord.Embed(
                    description=f"<:HadeTick:1454058805473050636> | Added currently playing **{track.title}** to playlist **{name}**.",
                    color=self.color
                )
            else:
                if not player:
                    player = self.client.lavalink.player_manager.create(ctx.guild.id)

                results = await player.node.get_tracks(f'ytsearch:{query}')

                if not results or not hasattr(results, 'tracks') or not results.tracks:
                    embed = discord.Embed(
                        description="<:HadeCross:1454058806211514492> | No songs found with that query.",
                        color=self.color
                    )
                    return await ctx.reply(embed=embed, mention_author=False)

                track = results.tracks[0]

                self.db.execute(
                    "INSERT INTO playlist_songs (playlist_id, title, url, duration) VALUES (?, ?, ?, ?)",
                    (playlist_id, track.title, track.uri, track.duration)
                )
                self.db.commit()

                embed = discord.Embed(
                    description=f"<:HadeTick:1454058805473050636> | Added **{track.title}** to playlist **{name}**.",
                    color=self.color
                )
        except Exception as e:
            print(f"Playlist add error: {e}")
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | An error occurred while adding the song.",
                color=self.color
            )
        await ctx.reply(embed=embed, mention_author=False)

    @playlist.command(name="remove", help="Remove a song from your playlist by position or name", usage="playlist remove <playlist> <number or song name>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def playlist_remove(self, ctx, name: str, *, identifier: str):
        playlist = self.get_playlist(ctx.author.id, name)
        if not playlist:
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | You don't have a playlist named **{name}**.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlist_id = playlist[0]
        songs = self.get_playlist_songs(playlist_id)

        if not songs:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | This playlist is empty.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        song_to_remove = None
        
        if identifier.isdigit():
            number = int(identifier)
            if number < 1 or number > len(songs):
                embed = discord.Embed(
                    description=f"<:HadeCross:1454058806211514492> | Invalid song number. Use a number between 1 and {len(songs)}.",
                    color=self.color
                )
                return await ctx.reply(embed=embed, mention_author=False)
            song_to_remove = songs[number - 1]
        else:
            search_term = identifier.lower()
            for song in songs:
                if search_term in song[1].lower():
                    song_to_remove = song
                    break
            
            if not song_to_remove:
                embed = discord.Embed(
                    description=f"<:HadeCross:1454058806211514492> | No song found matching **{identifier}** in playlist **{name}**.",
                    color=self.color
                )
                return await ctx.reply(embed=embed, mention_author=False)

        song_id = song_to_remove[0]
        song_title = song_to_remove[1]

        self.db.execute("DELETE FROM playlist_songs WHERE id = ?", (song_id,))
        self.db.commit()

        embed = discord.Embed(
            description=f"<:HadeTick:1454058805473050636> | Removed **{song_title}** from playlist **{name}**.",
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @playlist.command(name="rename", help="Rename a playlist", usage="playlist rename <old name> <new name>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def playlist_rename(self, ctx, old_name: str, *, new_name: str):
        if len(new_name) > 50:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | New playlist name must be 50 characters or less.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlist = self.get_playlist(ctx.author.id, old_name)
        if not playlist:
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | You don't have a playlist named **{old_name}**.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        existing = self.get_playlist(ctx.author.id, new_name)
        if existing:
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | You already have a playlist named **{new_name}**.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlist_id = playlist[0]
        self.db.execute(
            "UPDATE playlists SET name = ? WHERE id = ?",
            (new_name, playlist_id)
        )
        self.db.commit()

        embed = discord.Embed(
            description=f"<:HadeTick:1454058805473050636> | Renamed playlist **{old_name}** to **{new_name}**.",
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @playlist.command(name="list", help="View all your playlists", usage="playlist list")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def playlist_list(self, ctx):
        playlists = self.get_user_playlists(ctx.author.id)

        if not playlists:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | You don't have any playlists yet. Create one with `playlist create <name>`!",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlist_info = []
        for pl_id, pl_name in playlists:
            songs = self.get_playlist_songs(pl_id)
            song_count = len(songs)
            playlist_info.append(f"**{pl_name}** - {song_count} song{'s' if song_count != 1 else ''}")

        embed = discord.Embed(
            title=f"{ctx.author.display_name}'s Playlists",
            description="\n".join(playlist_info),
            color=self.color
        )
        embed.set_footer(text=f"Total: {len(playlists)} playlist{'s' if len(playlists) != 1 else ''}")
        await ctx.reply(embed=embed, mention_author=False)

    @playlist.command(name="view", help="View songs in a playlist", usage="playlist view <name>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def playlist_view(self, ctx, *, name: str):
        playlist = self.get_playlist(ctx.author.id, name)
        if not playlist:
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | You don't have a playlist named **{name}**.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlist_id = playlist[0]
        playlist_name = playlist[1]
        songs = self.get_playlist_songs(playlist_id)

        if not songs:
            embed = discord.Embed(
                title=f"Playlist: {playlist_name}",
                description="This playlist is empty. Add songs with `playlist add <name> <song>`!",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        song_list = []
        total_duration = 0
        for i, (song_id, title, url, duration) in enumerate(songs, 1):
            minutes, seconds = divmod(duration // 1000, 60)
            duration_str = f"{minutes}:{seconds:02d}"
            song_list.append(f"`{i}.` [{title}]({url}) `{duration_str}`")
            total_duration += duration

        description = "\n".join(song_list[:20])
        if len(songs) > 20:
            description += f"\n\n*...and {len(songs) - 20} more songs*"

        total_minutes, total_seconds = divmod(total_duration // 1000, 60)
        total_hours, total_minutes = divmod(total_minutes, 60)
        if total_hours > 0:
            total_time = f"{total_hours}h {total_minutes}m"
        else:
            total_time = f"{total_minutes}m {total_seconds}s"

        embed = discord.Embed(
            title=f"Playlist: {playlist_name}",
            description=description,
            color=self.color
        )
        embed.set_footer(text=f"{len(songs)} songs | Total duration: {total_time}")
        await ctx.reply(embed=embed, mention_author=False)

    @playlist.command(name="delete", help="Delete a playlist", usage="playlist delete <name>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def playlist_delete(self, ctx, *, name: str):
        playlist = self.get_playlist(ctx.author.id, name)
        if not playlist:
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | You don't have a playlist named **{name}**.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlist_id = playlist[0]
        playlist_name = playlist[1]

        self.db.execute("DELETE FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
        self.db.execute("DELETE FROM playlists WHERE id = ?", (playlist_id,))
        self.db.commit()

        embed = discord.Embed(
            description=f"<:HadeTick:1454058805473050636> | Successfully deleted playlist **{playlist_name}**.",
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @playlist.command(name="clear", help="Clear all songs from a playlist", usage="playlist clear <name>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def playlist_clear(self, ctx, *, name: str):
        playlist = self.get_playlist(ctx.author.id, name)
        if not playlist:
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | You don't have a playlist named **{name}**.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlist_id = playlist[0]
        playlist_name = playlist[1]

        self.db.execute("DELETE FROM playlist_songs WHERE playlist_id = ?", (playlist_id,))
        self.db.commit()

        embed = discord.Embed(
            description=f"<:HadeTick:1454058805473050636> | Cleared all songs from playlist **{playlist_name}**.",
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)

    @playlist.command(name="play", help="Play a playlist", usage="playlist play <name>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def playlist_play(self, ctx, *, name: str):
        from main import LavalinkVoiceClient

        if not ctx.author.voice or not ctx.author.voice.channel:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | You must be in a voice channel to play a playlist.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if ctx.voice_client and ctx.author.voice.channel != ctx.voice_client.channel:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | You need to be in the same voice channel as me to play a playlist.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlist = self.get_playlist(ctx.author.id, name)
        if not playlist:
            embed = discord.Embed(
                description=f"<:HadeCross:1454058806211514492> | You don't have a playlist named **{name}**.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        playlist_id = playlist[0]
        playlist_name = playlist[1]
        songs = self.get_playlist_songs(playlist_id)

        if not songs:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | This playlist is empty.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if not ctx.voice_client:
            try:
                await ctx.author.voice.channel.connect(cls=LavalinkVoiceClient, self_deaf=True)
            except Exception as e:
                print(f"Connection error: {e}")
                embed = discord.Embed(
                    description="<:HadeCross:1454058806211514492> | Could not connect to voice channel.",
                    color=self.color
                )
                return await ctx.reply(embed=embed, mention_author=False)

        if not self.client.lavalink:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | Music system is not ready. Please try again later.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        player = self.client.lavalink.player_manager.get(ctx.guild.id)
        if not player:
            player = self.client.lavalink.player_manager.create(ctx.guild.id)

        added_count = 0
        for song_id, title, url, duration in songs:
            try:
                results = await player.node.get_tracks(url)
                if results and hasattr(results, 'tracks') and results.tracks:
                    track = results.tracks[0]
                    player.add(requester=ctx.author.id, track=track)
                    added_count += 1
            except Exception as e:
                print(f"Error adding track {title}: {e}")
                continue

        if added_count == 0:
            embed = discord.Embed(
                description="<:HadeCross:1454058806211514492> | Could not add any songs from the playlist.",
                color=self.color
            )
            return await ctx.reply(embed=embed, mention_author=False)

        if not player.is_playing:
            await player.play()

        embed = discord.Embed(
            description=f"<:HadeTick:1454058805473050636> | Added **{added_count}** songs from playlist **{playlist_name}** to the queue!",
            color=self.color
        )
        await ctx.reply(embed=embed, mention_author=False)


async def setup(client):
    await client.add_cog(Playlist(client))
