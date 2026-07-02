import discord
import sqlite3
from discord.ext import commands
from lavalink.filters import Timescale, Rotation, Equalizer, Tremolo, Vibrato, LowPass


class Filters(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.filters = {}
        self.db = sqlite3.connect('databases/music.db', check_same_thread=False)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Filters Is Ready")

    async def get_filter(self, filter_: str, guild_id):
        flt = self.filters.get(guild_id)
        if flt is None:
            return False
        return filter_.lower() in flt

    async def _filter(self, filter_name: str, guild_id):
        flt = self.filters.get(guild_id)
        if flt is None:
            self.filters[guild_id] = []
            self.filters[guild_id].append(filter_name.lower())
            return
        if filter_name.lower() in flt:
            self.filters[guild_id].remove(filter_name.lower())
        else:
            self.filters[guild_id].append(filter_name.lower())

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

    async def check_voice(self, ctx):
        if not ctx.voice_client:
            embed = discord.Embed(description="I am not in any voice channel.", colour=0x2b2d31)
            await ctx.reply(embed=embed, mention_author=False)
            return False

        if not getattr(ctx.author.voice, "channel", None):
            embed = discord.Embed(description="You must be in a voice channel to use this command.", colour=0x2b2d31)
            await ctx.reply(embed=embed, mention_author=False)
            return False

        if ctx.author.voice.channel == ctx.voice_client.channel:
            return True

        if ctx.author.guild_permissions.administrator:
            return True

        if self.is_smart_vc_enabled(ctx.guild.id):
            if self.has_dj_role(ctx.author):
                return True
            if self.is_dj_user(ctx.guild.id, ctx.author.id):
                return True

        embed = discord.Embed(
            description="<:HadeCross:1454058806211514492> | You need to be in the same voice channel as me, or have DJ permissions to use filters.",
            colour=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)
        return False

    async def get_player(self, ctx):
        if not self.client.lavalink:
            return None
        return self.client.lavalink.player_manager.get(ctx.guild.id)

    async def apply_filter(self, ctx, filter_name, filter_obj):
        if not await self.check_voice(ctx):
            return

        player = await self.get_player(ctx)
        if not player or not player.is_playing:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | I am not playing anything.", colour=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        if player.paused:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | I am currently paused. Please use `&resume`.", colour=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        flt = await self.get_filter(filter_name, ctx.guild.id)
        if not flt:
            await player.set_filter(filter_obj)
            await self._filter(filter_name, ctx.guild.id)
            embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Set **{filter_name.capitalize()}** filter to the player.", color=0x2b2d31)
        else:
            await player.remove_filter(filter_name.lower())
            await self._filter(filter_name, ctx.guild.id)
            embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Removed **{filter_name.capitalize()}** filter from the player.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

    async def reset_filters(self, ctx, filter_names):
        if not await self.check_voice(ctx):
            return

        player = await self.get_player(ctx)
        if not player or not player.is_playing:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | I am not playing anything.", colour=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        if player.paused:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | I am currently paused. Please use `&resume`.", colour=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        for filter_name in filter_names:
            flt = await self.get_filter(filter_name, ctx.guild.id)
            if flt:
                await player.remove_filter(filter_name.lower())
                await self._filter(filter_name, ctx.guild.id)

        embed = discord.Embed(description="<:HadeTick:1454058805473050636> | All the filters have been reset.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)

    @commands.command(aliases=['retro'], help="Music Like Retro", usage="vaporwave")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def vaporwave(self, ctx):
        timescale = Timescale()
        timescale.update(speed=0.74, pitch=0.8, rate=1.0)
        await self.apply_filter(ctx, 'vaporwave', timescale)

    @commands.command(aliases=['classic'], help="Classic Music", usage="lofi")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def lofi(self, ctx):
        timescale = Timescale()
        timescale.update(speed=0.73, pitch=0.86, rate=1.0)
        await self.apply_filter(ctx, 'lofi', timescale)

    @commands.command(name="8d", aliases=['Rotation'], help="Surrounder Effect", usage="8d")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def _8d(self, ctx):
        rotation = Rotation()
        rotation.update(rotation_hz=0.086)
        await self.apply_filter(ctx, '8d', rotation)

    @commands.command(aliases=['slow'], help="Slowed Music", usage="slowmo")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def slowmo(self, ctx):
        timescale = Timescale()
        timescale.update(speed=0.68)
        await self.apply_filter(ctx, 'slowmo', timescale)

    @commands.command(aliases=['bass'], help="Hear The Boosted Music", usage="bassboost")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def bassboost(self, ctx):
        equalizer = Equalizer()
        equalizer.update(bands=[(0, 0.6), (1, 0.5), (2, 0.4), (3, 0.3), (4, 0.2)])
        await self.apply_filter(ctx, 'bassboost', equalizer)

    @commands.command(aliases=['chin'], help="Chinese Style Music", usage="china")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def china(self, ctx):
        equalizer = Equalizer()
        equalizer.update(bands=[(14, 0.3)])
        await self.apply_filter(ctx, 'china', equalizer)

    @commands.command(aliases=['chips'], help="Hear The Chip's Sound", usage="chipmunk")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def chipmunk(self, ctx):
        timescale = Timescale()
        timescale.update(speed=1.5)
        await self.apply_filter(ctx, 'chipmunk', timescale)

    @commands.command(aliases=['breather'], help="Darth Vader Effect", usage="darthvader")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def darthvader(self, ctx):
        timescale = Timescale()
        timescale.update(speed=1.2, pitch=0.5)
        await self.apply_filter(ctx, 'darthvader', timescale)

    @commands.command(aliases=['lucifer'], help="Demon Voice Effect", usage="demon")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def demon(self, ctx):
        timescale = Timescale()
        timescale.update(speed=0.8, pitch=0.5)
        await self.apply_filter(ctx, 'demon', timescale)

    @commands.command(aliases=['comd'], help="Unique Funny Sound", usage="funny")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def funny(self, ctx):
        timescale = Timescale()
        timescale.update(speed=1.2, pitch=0.7)
        await self.apply_filter(ctx, 'funny', timescale)

    @commands.command(aliases=['singsong'], help="Karaoke Effect", usage="karaoke")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def karaoke(self, ctx):
        timescale = Timescale()
        timescale.update(speed=1.0, pitch=0.0)
        await self.apply_filter(ctx, 'karaoke', timescale)

    @commands.command(aliases=['sped'], help="Sped-Up Nightcore Music", usage="nightcore")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def nightcore(self, ctx):
        timescale = Timescale()
        timescale.update(speed=1.25, pitch=1.3)
        await self.apply_filter(ctx, 'nightcore', timescale)

    @commands.command(aliases=['bang'], help="Pop Music Style", usage="pop")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def pop(self, ctx):
        equalizer = Equalizer()
        equalizer.update(bands=[(10, 0.5)])
        await self.apply_filter(ctx, 'pop', equalizer)

    @commands.command(aliases=['rfilters'], help="Removes All The Filters", usage="reset")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def reset(self, ctx):
        all_filters = [
            'slowmo', 'lofi', 'vaporwave', '8d', 'bassboost', 'china',
            'chipmunk', 'darthvader', 'demon', 'funny', 'karaoke',
            'nightcore', 'pop', 'soft', 'treblebass', 'tremolo', 'alien', 'lowpass'
        ]
        await self.reset_filters(ctx, all_filters)

    @commands.command(aliases=['mushy'], help="Soft Music Effect", usage="soft")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def soft(self, ctx):
        equalizer = Equalizer()
        equalizer.update(bands=[(0, -0.25), (14, 0.25)])
        await self.apply_filter(ctx, 'soft', equalizer)

    @commands.command(aliases=['deep'], help="High-Pitched Music", usage="treblebass")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def treblebass(self, ctx):
        equalizer = Equalizer()
        equalizer.update(bands=[(0, 0.6), (14, -0.25)])
        await self.apply_filter(ctx, 'treblebass', equalizer)

    @commands.command(aliases=['tremble'], help="Trembling Music Effect", usage="tremolo")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def tremolo(self, ctx):
        tremolo = Tremolo()
        tremolo.update(depth=0.5, frequency=4.0)
        await self.apply_filter(ctx, 'tremolo', tremolo)

    @commands.command(aliases=['celestial'], help="Alien Sound Effect", usage="alien")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def alien(self, ctx):
        vibrato = Vibrato()
        vibrato.update(frequency=10.0, depth=0.9)
        await self.apply_filter(ctx, 'alien', vibrato)

    @commands.command(aliases=['lp'], help="Low Pass Filter", usage="lowpass <strength>")
    @commands.cooldown(1, 5, commands.BucketType.user)
    @commands.guild_only()
    async def lowpass(self, ctx, strength: float = 50.0):
        if not await self.check_voice(ctx):
            return

        player = await self.get_player(ctx)
        if not player or not player.is_playing:
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | I am not playing anything.", colour=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        strength = max(0.0, min(100.0, strength))

        if strength == 0.0:
            await player.remove_filter('lowpass')
            await self._filter('lowpass', ctx.guild.id)
            embed = discord.Embed(description="<:HadeCross:1454058806211514492> | Disabled **Low Pass Filter**", color=0x2b2d31)
            return await ctx.reply(embed=embed, mention_author=False)

        low_pass = LowPass()
        low_pass.update(smoothing=strength)
        await player.set_filter(low_pass)
        await self._filter('lowpass', ctx.guild.id)

        embed = discord.Embed(description=f"<:HadeTick:1454058805473050636> | Set **Low Pass Filter** strength to {strength}.", color=0x2b2d31)
        await ctx.reply(embed=embed, mention_author=False)


async def setup(client):
    await client.add_cog(Filters(client))
