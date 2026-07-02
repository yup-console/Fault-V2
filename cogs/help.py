import discord
import asyncio
import sqlite3
from discord.ext import commands


class MenuView(discord.ui.View):
    def __init__(self, ctx, timeout=60):
        super().__init__(timeout=timeout)
        self.ctx = ctx
        self.author = ctx.author
        self.client = ctx.bot
        self.con = sqlite3.connect('databases/settings.db', check_same_thread=False)
        self.message = None

    async def on_timeout(self):
        for child in self.children:
            child.disabled = True
        try:
            if self.message:
                await self.message.edit(view=self)
        except:
            pass

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.author.id:
            await interaction.response.send_message("This is not your interaction.", ephemeral=True)
            return False
        return True


    # ----------------------
    # CATEGORY DROPDOWN WITH CUSTOM EMOJIS
    # ----------------------
    @discord.ui.select(placeholder="Make a selection", options=[
        discord.SelectOption(label="Music", value="music", emoji="<:emoji:1454836809476477103>"),
        discord.SelectOption(label="Filter", value="filter", emoji="<:filters:1454834955828990057>"),
        discord.SelectOption(label="Information", value="info", emoji="<:Infozz:1454836490738864220>"),
        discord.SelectOption(label="Utility", value="utility", emoji="<:Utilityaa:1454837295445442693>"),
        discord.SelectOption(label="Profile", value="profile", emoji="<:Profile:1454050322900058256>"),
        discord.SelectOption(label="Playlist", value="playlist", emoji="<:playlist:1454050403648929844>"),
        discord.SelectOption(label="Fun", value="fun", emoji="<:RedonFun:1454836013561155698>"),
        discord.SelectOption(label="Spotify", value="spotify", emoji="<:Spotify:1454149285439475712>"),
        discord.SelectOption(label="Lastfm", value="lastfm", emoji="<:lastfm:1454165185831895264>"),
    ])
    async def select_category(self, interaction: discord.Interaction, select: discord.ui.Select):

        selected = select.values[0]
        embed = discord.Embed(colour=0x2b2d31)
        
        # Add emoji to title based on selection
        emoji_map = {
            "music": " ",
            "filter": " ", 
            "info": " ",
            "utility": " ",
            "profile": " ",
            "playlist": " ",
            "fun": " ",
            "spotify": " ",
            "lastfm": " "
        }
        
        embed.set_author(
            name=f"{emoji_map.get(selected, '')} {selected.capitalize()} Commands", 
            icon_url=interaction.user.display_avatar.url
        )
        embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)

        if selected == "music":
            embed.description = "`Autoplay`, `Play`, `Pause`, `Resume`, `Stop`, `Queue`, `Volume`, `Skip`, `ClearQueue`, `Join`, `Disconnect`, `NowPlaying`, `Queueremove`, `Forceleave`"
        elif selected == "filter":
            embed.description = "`Vaporwave`, `Lofi`, `8d`, `Slowmo`, `BassBoost`, `China`, `Chipmunk`, `DarthVader`, `Demon`, `Funny`, `Karoke`, `NightCore`, `Pop`, `Soft`, `TrebleBass`, `Tremolo`, `Alien`, `LowPass`, `Reset`"
        elif selected == "info":
            embed.description = "`Ping`, `Uptime`, `Invite`, `Support`, `Vote`, `Stats`, `Help`, `Avatar`, `Banner`, `ServerAvatar`, `ServerBanner`, `Policy`, `Tos`, `Node`"
        elif selected == "utility":
            embed.description = "`SetPrefix`, `Purge`, `PurgeBots`, `Report`, `Ignore add`, `Ignore remove`, `Ignore reset`, `Ignore list`, `Smart Vc`, `247`"
        elif selected == "profile":
            embed.description = "`Profile`, `Setbio`"
        elif selected == "playlist":
            embed.description = "`Playlist`, `Playlist create`, `Playlist remove`, `Playlist rename`, `Playlist list`, `Playlist view`, `Playlist delete`, `Playlist play`, `Playlist clear`"
        elif selected == "fun":
            embed.description = "`Adance`, `Blush`, `Bonk`, `Cry`, `Cuddle`, `Hug`, `Kiss`, `Kill`, `Pat`, `Punch`, `Roast`, `Ship`, `Shoot`, `Slap`, `Wink`"
        elif selected == "spotify":
            embed.description = "`Spotify`, `Spotify Link`, `Spotify Profile`, `Spotify Playlist`, `Spotify Unlink`"
        elif selected == "lastfm":
            embed.description = "`Lastfm`, `Lastfm Login`, `Lastfm Profile`, `Lastfm np`, `Lastfm Topartists`, `Lastfm Toptracks`, `Lastfm Scrobble`, `Lastfm Compat`, `Lastfm Logout`"

        await interaction.response.edit_message(embed=embed, view=self)


    # ----------------------
    # HOME BUTTON
    # ----------------------
    @discord.ui.button(label="Home", style=discord.ButtonStyle.secondary)
    async def home_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        cur = self.con.cursor()
        cur.execute("SELECT prefix FROM Prefix WHERE guild_id = ?", (interaction.guild.id,))
        server_prefix = cur.fetchone()
        prefix = server_prefix[0] if server_prefix else "F"

        embed = discord.Embed(
            colour=0x2b2d31,
            description=(
                "## > <a:sparkleaaa:1454888560317694156> Fault Help Menu <a:sparkleaaa:1454888560317694156>\n"
                "### <:Prefix:1454888698557497580> Jumpstart Your Music Journey\n"
                f"<:music:1454153742898171968> **[`{prefix}play <song name | URL>`](https://discord.gg/TG26Tfn2eD)** - Start enjoying your favorite tunes instantly.\n\n"
                "### > <:modules:1454888773405118615> Command Categories\n"
                "• <:emoji:1454836809476477103> **: Music**\n"
                "• <:filters:1454834955828990057> **: Filters**\n"
                "• <:Infozz:1454836490738864220> **: Information**\n"
                "• <:Utilityaa:1454837295445442693> **: Utility**\n"
                "• <:Profile:1454050322900058256> **: Profile**\n"
                "• <:playlist:1454050403648929844> **: Playlist**\n"
                "• <:RedonFun:1454836013561155698> **: Fun**\n"
                "• <:Spotify:1454149285439475712> **: Spotify**\n"
                "• <:lastfm:1454165185831895264> **: Lastfm**\n\n"
                "### > <:links:1454359084353585314> Links\n"
                "- **[Invite Fault](https://discord.com/oauth2/authorize?client_id=1419347731545329744) | [Support Server](https://discord.gg/TG26Tfn2eD)**"
            )
        )

        embed.set_author(name=self.ctx.author.name, icon_url=self.ctx.author.display_avatar.url)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)

        await interaction.response.edit_message(embed=embed, view=self)


    # ----------------------
    # COMMAND LIST BUTTON
    # ----------------------
    @discord.ui.button(label="Command List", style=discord.ButtonStyle.secondary)
    async def cmdlist_button(self, interaction: discord.Interaction, button: discord.ui.Button):

        embed = discord.Embed(
            colour=0x2b2d31,
            title="Fault All Commands List"
        )

        embed.add_field(
            name="<:emoji:1454836809476477103> Music",
            value="`Autoplay`, `Play`, `Pause`, `Resume`, `Stop`, `Queue`, `Volume`, `Skip`, `ClearQueue`, `Join`, `Disconnect`, `NowPlaying`, `Queueremove`, `Forceleave`",
            inline=False
        )

        embed.add_field(
            name="<:filters:1454834955828990057> Filter",
            value="`Vaporwave`, `Lofi`, `8d`, `Slowmo`, `BassBoost`, `China`, `Chipmunk`, `DarthVader`, `Demon`, `Funny`, `Karoke`, `NightCore`, `Pop`, `Soft`, `TrebleBass`, `Tremolo`, `Alien`, `LowPass`, `Reset`",
            inline=False
        )

        embed.add_field(
            name="<:Infozz:1454836490738864220> Information",
            value="`Ping`, `Uptime`, `Invite`, `Support`, `Vote`, `Stats`, `Help`, `Avatar`, `Banner`, `ServerAvatar`, `ServerBanner`, `Policy`, `Tos`, `Node`",
            inline=False
        )

        embed.add_field(
            name="<:Utilityaa:1454837295445442693> Utility",
            value="`SetPrefix`, `Purge`, `PurgeBots`, `Report`, `Ignore add`, `Ignore remove`, `Ignore reset`, `Ignore list`, `Smart Vc`, `247`",
            inline=False
        )

        embed.add_field(
            name="<:Profile:1454050322900058256> Profile",
            value="`Profile`, `Setbio`",
            inline=False
        )

        embed.add_field(
            name="<:playlist:1454050403648929844> Playlist",
            value="`Playlist`, `Playlist create`, `Playlist remove`, `Playlist rename`, `Playlist list`, `Playlist view`, `Playlist delete`, `Playlist play`, `Playlist clear`",
            inline=False
        )
        
        embed.add_field(
            name="<:RedonFun:1454836013561155698> Fun",
            value="`Adance`, `Blush`, `Bonk`, `Cry`, `Cuddle`, `Hug`, `Kiss`, `Kill`, `Pat`, `Punch`, `Roast`, `Ship`, `Shoot`, `Slap`, `Wink`",
            inline=False
        )
        
        embed.add_field(
            name="<:Spotify:1454149285439475712> Spotify",
            value="`Spotify`, `Spotify Link`, `Spotify Profile`, `Spotify Playlist`, `Spotify Unlink`",
            inline=False
        )
        
        embed.add_field(
            name="<:lastfm:1454165185831895264> Lastfm",
            value="`Lastfm`, `Lastfm Login`, `Lastfm Profile`, `Lastfm np`, `Lastfm Topartists`, `Lastfm Toptracks`, `Lastfm Scrobble`, `Lastfm Compat`, `Lastfm Logout`",
            inline=False
        )

        embed.set_author(name=self.ctx.author.name, icon_url=self.ctx.author.display_avatar.url)
        embed.set_thumbnail(url=self.ctx.author.display_avatar.url)
        embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)

        await interaction.response.edit_message(embed=embed, view=self)


    # ----------------------
    # DELETE BUTTON
    # ----------------------
    @discord.ui.button(label="Delete", style=discord.ButtonStyle.danger)
    async def delete_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        try:
            await interaction.message.delete()
        except:
            pass


# -------------------------------------------------------
# HELP COMMAND
# -------------------------------------------------------
class Help(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.client.remove_command("help")
        self.con = sqlite3.connect('databases/settings.db', check_same_thread=False)

    @commands.Cog.listener()
    async def on_ready(self):
        print("Help Is Ready")

    @commands.command(aliases=['h'], help="Shows the help command of the bot", usage="help [command]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def help(self, ctx, query=None):

        if query:
            command = self.client.get_command(query)
            if command:
                aliases = ", ".join(command.aliases) if command.aliases else "None"
                embed = discord.Embed(colour=0x2b2d31, description=f"**{command.help or 'No description'}**")
                embed.add_field(name="Aliases", value=f"`{aliases}`", inline=False)
                embed.add_field(name="Usage", value=f"`{command.usage or command.name}`", inline=False)
                embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
                embed.set_thumbnail(url=ctx.author.display_avatar.url)
                embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)
                return await ctx.send(embed=embed)
            else:
                return await ctx.send("Command not found.")

        view = MenuView(ctx)

        cur = self.con.cursor()
        cur.execute("SELECT prefix FROM Prefix WHERE guild_id = ?", (ctx.guild.id,))
        server_prefix = cur.fetchone()
        prefix = server_prefix[0] if server_prefix else "F"

        embed = discord.Embed(
            colour=0x2b2d31,
            description=(
                "## > <a:sparkleaaa:1454888560317694156> Fault Help Menu <a:sparkleaaa:1454888560317694156>\n"
                "### <:Prefix:1454888698557497580> Jumpstart Your Music Journey\n"
                f"<:music:1454153742898171968> **[`{prefix}play <song name | URL>`](https://discord.gg/TG26Tfn2eD)** - Start enjoying your favorite tunes instantly.\n\n"
                "### > <:modules:1454888773405118615> Command Categories\n"
                "• <:emoji:1454836809476477103> **: Music**\n"
                "• <:filters:1454834955828990057> **: Filters**\n"
                "• <:Infozz:1454836490738864220> **: Information**\n"
                "• <:Utilityaa:1454837295445442693> **: Utility**\n"
                "• <:Profile:1454050322900058256> **: Profile**\n"
                "• <:playlist:1454050403648929844> **: Playlist**\n"
                "• <:RedonFun:1454836013561155698> **: Fun**\n"
                "• <:Spotify:1454149285439475712> **: Spotify**\n"
                "• <:lastfm:1454165185831895264> **: Lastfm**\n\n"
                "### > <:links:1454359084353585314> Links\n"
                "- **[Invite Fault](https://discord.com/oauth2/authorize?client_id=1419347731545329744) | [Support Server](https://discord.gg/TG26Tfn2eD)**"
            )
        )

        embed.set_author(name=ctx.author.name, icon_url=ctx.author.display_avatar.url)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        embed.set_footer(text="Fault Is Love", icon_url=self.client.user.avatar.url)

        message = await ctx.reply(embed=embed, view=view, mention_author=False)
        view.message = message


async def setup(client):
    await client.add_cog(Help(client))