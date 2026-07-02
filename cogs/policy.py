import discord
from discord.ext import commands


class PageView(discord.ui.View):
    def __init__(self, pages, ctx):
        super().__init__(timeout=60)
        self.pages = pages
        self.current = 0
        self.ctx = ctx

    async def update(self, interaction):
        embed = self.pages[self.current]
        await interaction.response.edit_message(embed=embed, view=self)

    @discord.ui.button(label="Previous", style=discord.ButtonStyle.secondary)
    async def previous(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("You cannot control this pagination.", ephemeral=True)

        if self.current > 0:
            self.current -= 1
            await self.update(interaction)
        else:
            await interaction.response.defer()

    @discord.ui.button(label="Next", style=discord.ButtonStyle.secondary)
    async def next(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user != self.ctx.author:
            return await interaction.response.send_message("You cannot control this pagination.", ephemeral=True)

        if self.current < len(self.pages) - 1:
            self.current += 1
            await self.update(interaction)
        else:
            await interaction.response.defer()


class Policy(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Policy Cog Loaded")

    # ========================= PRIVACY POLICY =========================
    @commands.command(help="Shows the privacy policy of the bot", usage="policy")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def policy(self, ctx):

        pages = []

        page1 = discord.Embed(
            title="Privacy Policy: Overview",
            description=(
                "This Privacy Policy explains how Fault collects, stores, and uses data.\n\n"
                "By using Fault, you agree to the terms described in this policy.\n"
                "Fault values user privacy and only collects the minimum data required "
                "to provide its features."
            )
        )
        pages.append(page1)

        page2 = discord.Embed(
            title="Data We Collect",
            description=(
                "Fault collects and stores the following information:\n\n"
                "- User IDs (used for profile and playlist features)\n"
                "- Server IDs and Channel IDs (used for 24/7 and autoplay features)\n"
                "- Playlist data created by users\n"
                "- Guild join and guild leave logs\n\n"
                "**Note:** Fault does *not* generate invite links automatically.\n"
                "An invite link is only created when:\n"
                "- A user submits a report in the support server, or\n"
                "- A verified developer requests it during emergencies."
            )
        )
        pages.append(page2)

        page3 = discord.Embed(
            title="Data Deletion",
            description=(
                "Users may request deletion of their playlist data at any time:\n\n"
                "- You can delete your playlist by clearing all playlists yourself.\n"
                "- For complete data removal, contact the developer.\n\n"
                "Developer ID: iworship.ayush | 901487880067776524\n"
                "Support Server: https://discord.gg/TG26Tfn2eD"
            )
        )
        pages.append(page3)

        page4 = discord.Embed(
            title="Data Usage",
            description=(
                "Fault does not use, sell, or share any collected data for external purposes.\n\n"
                "Data is used only for internal bot features such as:\n"
                "- Music playback\n"
                "- Profile settings\n"
                "- Autoplay and 24/7 functionality\n\n"
                "Fault does not log message content or moderation actions."
            )
        )
        pages.append(page4)

        page5 = discord.Embed(
            title="Contact",
            description=(
                "For any questions, concerns, or data removal requests:\n\n"
                "Developer ID: iworship.ayush | 901487880067776524\n"
                "Support Server: https://discord.gg/zBT5Er5zHv\n"
                "You may also open a support ticket in the support server."
            )
        )
        pages.append(page5)

        view = PageView(pages, ctx)
        await ctx.reply(embed=pages[0], view=view, mention_author=False)

    # ========================= TERMS OF SERVICE =========================
    @commands.command(help="Shows the terms of service of the bot", usage="tos")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def tos(self, ctx):

        pages = []

        page1 = discord.Embed(
            title="Terms of Service: Overview",
            description=(
                "These Terms of Service outline the rules for using Fault.\n\n"
                "By using the bot, you agree to follow these terms and Discord's Terms of Service."
            )
        )
        pages.append(page1)

        page2 = discord.Embed(
            title="Usage Requirements",
            description=(
                "Fault is a music bot intended for all audiences.\n\n"
                "You agree not to use the bot for:\n"
                "- Raid\n"
                "- Spam\n"
                "- Harassment\n"
                "- Violating Discord's TOS in any form\n\n"
                "The bot is designed for legitimate and safe usage."
            )
        )
        pages.append(page2)

        page3 = discord.Embed(
            title="Bot Functionality",
            description=(
                "Fault operates consistently across all servers.\n"
                "It does not include moderation commands and does not log moderation activities.\n\n"
                "All features are intended for music playback and profile customization."
            )
        )
        pages.append(page3)

        page4 = discord.Embed(
            title="Liability",
            description=(
                "The developers are not responsible for any misuse of Fault.\n"
                "Misuse may result in the bot being removed from your server.\n\n"
                "Fault is provided on an as-is basis without uptime guarantees."
            )
        )
        pages.append(page4)

        page5 = discord.Embed(
            title="Contact",
            description=(
                "If you need assistance or wish to report an issue:\n\n"
                "Developer ID: iworship.ayush | 901487880067776524\n"
                "Support Server: https://discord.gg/TG26Tfn2eD\n"
                "Or open a ticket anytime."
            )
        )
        pages.append(page5)

        view = PageView(pages, ctx)
        await ctx.reply(embed=pages[0], view=view, mention_author=False)


async def setup(client):
    await client.add_cog(Policy(client))