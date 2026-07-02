import discord
from discord.ext import commands
import sqlite3
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import io
import aiohttp
import os
import subprocess


def extraowner():
    async def predicate(ctx: commands.Context):
        with sqlite3.connect('databases/owner.db') as con:
            cur = con.cursor()
            cur.execute("SELECT user_id FROM Owner")
            ids_ = cur.fetchall()
            return ctx.author.id in [i[0] for i in ids_]
    return commands.check(predicate)


class Profile(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.con = sqlite3.connect('databases/profile.db', check_same_thread=False)
        self.cur = self.con.cursor()
        self.bg_path = "assets/pfpbg.jpg"
        
        # Install emoji fonts
        self.install_emoji_fonts()

    def install_emoji_fonts(self):
        """Install emoji fonts in Pterodactyl"""
        try:
            result = subprocess.run(['which', 'apt-get'], capture_output=True)
            if result.returncode == 0:
                subprocess.run(['apt-get', 'update'], capture_output=True)
                subprocess.run(['apt-get', 'install', '-y', 'fonts-noto-color-emoji', 'fonts-symbola'], 
                             capture_output=True)
        except Exception:
            pass

    def get_emoji_font(self, size, bold=False):
        """Get a font that supports emojis"""
        font_paths = [
            "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
            "/usr/share/fonts/truetype/noto/NotoSans-Regular.ttf", 
            "/usr/share/fonts/truetype/ancient-scripts/Symbola.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        ]
        
        for font_path in font_paths:
            if os.path.exists(font_path):
                try:
                    return ImageFont.truetype(font_path, size)
                except:
                    continue
        
        return ImageFont.load_default()

    @commands.Cog.listener()
    async def on_ready(self):
        print("Profile Is Ready")

    async def fetch_avatar(self, user: discord.User) -> Image.Image:
        avatar_url = user.display_avatar.with_size(256).url
        async with aiohttp.ClientSession() as session:
            async with session.get(avatar_url) as resp:
                if resp.status == 200:
                    data = await resp.read()
                    return Image.open(io.BytesIO(data)).convert("RGBA")
        return None

    def create_circular_avatar(self, avatar: Image.Image, size: int = 120) -> Image.Image:
        avatar = avatar.resize((size, size), Image.Resampling.LANCZOS)
        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0, size, size), fill=255)
        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(avatar, (0, 0), mask)
        return output

    def get_user_bio(self, user_id: int) -> str:
        self.cur.execute("SELECT bio FROM user_profiles WHERE user_id = ?", (user_id,))
        result = self.cur.fetchone()
        return result[0] if result else "I love Fault"

    def set_user_bio(self, user_id: int, bio: str):
        self.cur.execute(
            "INSERT OR REPLACE INTO user_profiles (user_id, bio) VALUES (?, ?)",
            (user_id, bio)
        )
        self.con.commit()

    def get_user_badges(self, user_id: int) -> list:
        self.cur.execute("SELECT badge_name FROM user_badges WHERE user_id = ?", (user_id,))
        results = self.cur.fetchall()
        if results:
            return [r[0] for r in results]
        return ["Fault User"]

    def add_user_badge(self, user_id: int, badge_name: str) -> bool:
        try:
            self.cur.execute(
                "INSERT OR IGNORE INTO user_badges (user_id, badge_name) VALUES (?, ?)",
                (user_id, badge_name)
            )
            self.con.commit()
            return self.cur.rowcount > 0
        except Exception:
            return False

    def remove_user_badge(self, user_id: int, badge_name: str) -> bool:
        self.cur.execute(
            "DELETE FROM user_badges WHERE user_id = ? AND badge_name = ?",
            (user_id, badge_name)
        )
        self.con.commit()
        return self.cur.rowcount > 0

    def generate_profile_image(self, username: str, avatar: Image.Image, bio: str, badges: list) -> io.BytesIO:
        img_width, img_height = 600, 400
        
        if os.path.exists(self.bg_path):
            background = Image.open(self.bg_path).convert("RGBA")
            background = background.resize((img_width, img_height), Image.Resampling.LANCZOS)
        else:
            background = Image.new("RGBA", (img_width, img_height), (30, 30, 40, 255))
        
        overlay = Image.new("RGBA", (img_width, img_height), (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        
        box_margin = 30
        box_x1, box_y1 = box_margin, box_margin
        box_x2, box_y2 = img_width - box_margin, img_height - box_margin
        box_radius = 20
        
        overlay_draw.rounded_rectangle(
            [box_x1, box_y1, box_x2, box_y2],
            radius=box_radius,
            fill=(0, 0, 0, 180)
        )
        
        background = Image.alpha_composite(background, overlay)
        draw = ImageDraw.Draw(background)
        
        # Use emoji-supporting fonts
        title_font = self.get_emoji_font(24, bold=True)
        text_font = self.get_emoji_font(16)
        badge_font = self.get_emoji_font(14)
        
        avatar_size = 100
        avatar_x = box_x1 + 30
        avatar_y = box_y1 + 30
        
        if avatar:
            circular_avatar = self.create_circular_avatar(avatar, avatar_size)
            background.paste(circular_avatar, (avatar_x, avatar_y), circular_avatar)
        
        username_x = avatar_x + avatar_size + 20
        username_y = avatar_y + 20
        
        if len(username) > 20:
            username = username[:17] + "..."
        
        draw.text((username_x, username_y), username, font=title_font, fill=(255, 255, 255, 255))
        
        bio_label_y = avatar_y + avatar_size + 30
        draw.text((box_x1 + 30, bio_label_y), "Bio", font=title_font, fill=(180, 180, 255, 255))
        
        bio_y = bio_label_y + 35
        max_bio_width = box_x2 - box_x1 - 60
        
        if len(bio) > 100:
            bio = bio[:97] + "..."
        
        words = bio.split()
        lines = []
        current_line = ""
        
        for word in words:
            test_line = current_line + (" " if current_line else "") + word
            bbox = draw.textbbox((0, 0), test_line, font=text_font)
            if bbox[2] - bbox[0] <= max_bio_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = word
        if current_line:
            lines.append(current_line)
        
        lines = lines[:3]
        
        for i, line in enumerate(lines):
            draw.text((box_x1 + 30, bio_y + i * 22), line, font=text_font, fill=(220, 220, 220, 255))
        
        badges_label_y = bio_y + len(lines) * 22 + 25
        draw.text((box_x1 + 30, badges_label_y), "Badges", font=title_font, fill=(180, 180, 255, 255))
        
        badge_y = badges_label_y + 35
        badge_x = box_x1 + 30
        badge_spacing = 10
        badge_padding = 8
        
        for badge in badges[:5]:
            if len(badge) > 20:
                badge = badge[:17] + "..."
            
            bbox = draw.textbbox((0, 0), badge, font=badge_font)
            badge_width = bbox[2] - bbox[0] + badge_padding * 2
            badge_height = bbox[3] - bbox[1] + badge_padding * 2
            
            if badge_x + badge_width > box_x2 - 30:
                badge_x = box_x1 + 30
                badge_y += badge_height + badge_spacing
            
            if badge_y + badge_height > box_y2 - 20:
                break
            
            draw.rounded_rectangle(
                [badge_x, badge_y, badge_x + badge_width, badge_y + badge_height],
                radius=5,
                fill=(60, 60, 100, 200),
                outline=(100, 100, 180, 255)
            )
            
            draw.text(
                (badge_x + badge_padding, badge_y + badge_padding - 2),
                badge,
                font=badge_font,
                fill=(255, 255, 255, 255)
            )
            
            badge_x += badge_width + badge_spacing
        
        buffer = io.BytesIO()
        background = background.convert("RGB")
        background.save(buffer, format="PNG", quality=95)
        buffer.seek(0)
        return buffer

    @commands.command(aliases=['pr'], help="Shows your profile card", usage="profile [user]")
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def profile(self, ctx, user: discord.User = None):
        async with ctx.typing():
            target_user = user or ctx.author
            
            avatar = await self.fetch_avatar(target_user)
            bio = self.get_user_bio(target_user.id)
            badges = self.get_user_badges(target_user.id)
            
            image_buffer = self.generate_profile_image(
                username=target_user.name,
                avatar=avatar,
                bio=bio,
                badges=badges
            )
            
            file = discord.File(image_buffer, filename="profile.png")
            await ctx.reply(file=file, mention_author=False)

    @commands.command(help="Set your profile bio", usage="setbio <text>")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def setbio(self, ctx, *, bio: str):
        if len(bio) > 150:
            embed = discord.Embed(
                description="Bio must be 150 characters or less.",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)
        
        self.set_user_bio(ctx.author.id, bio)
        embed = discord.Embed(
            description=f"Successfully updated your bio!",
            color=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)

    @commands.group(description="Badge management commands", invoke_without_command=True, hidden=True)
    @commands.check_any(commands.is_owner(), extraowner())
    async def badge(self, ctx):
        embed = discord.Embed(
            description="Use `badge add <user> <badge_name>` or `badge remove <user> <badge_name>`",
            color=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)

    @badge.command(name="add", description="Add a badge to a user")
    @commands.check_any(commands.is_owner(), extraowner())
    async def badge_add(self, ctx, user: discord.User, *, badge_name: str):
        if len(badge_name) > 30:
            embed = discord.Embed(
                description="Badge name must be 30 characters or less.",
                color=0x2b2d31
            )
            return await ctx.reply(embed=embed, mention_author=False)
        
        if self.add_user_badge(user.id, badge_name):
            embed = discord.Embed(
                description=f"Successfully added badge **{badge_name}** to **{user}**.",
                color=0x2b2d31
            )
        else:
            embed = discord.Embed(
                description=f"**{user}** already has the badge **{badge_name}**.",
                color=0x2b2d31
            )
        await ctx.reply(embed=embed, mention_author=False)

    @badge.command(name="remove", description="Remove a badge from a user")
    @commands.check_any(commands.is_owner(), extraowner())
    async def badge_remove(self, ctx, user: discord.User, *, badge_name: str):
        if self.remove_user_badge(user.id, badge_name):
            embed = discord.Embed(
                description=f"Successfully removed badge **{badge_name}** from **{user}**.",
                color=0x2b2d31
            )
        else:
            embed = discord.Embed(
                description=f"**{user}** doesn't have the badge **{badge_name}**.",
                color=0x2b2d31
            )
        await ctx.reply(embed=embed, mention_author=False)

    @badge.command(name="list", description="List all badges of a user")
    @commands.check_any(commands.is_owner(), extraowner())
    async def badge_list(self, ctx, user: discord.User = None):
        target_user = user or ctx.author
        badges = self.get_user_badges(target_user.id)
        
        badges_text = "\n".join([f"- {badge}" for badge in badges])
        embed = discord.Embed(
            title=f"Badges for {target_user.display_name}",
            description=badges_text,
            color=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)

    @badge.command(name="clear", description="Clear all badges from a user")
    @commands.check_any(commands.is_owner(), extraowner())
    async def badge_clear(self, ctx, user: discord.User):
        self.cur.execute("DELETE FROM user_badges WHERE user_id = ?", (user.id,))
        self.con.commit()
        embed = discord.Embed(
            description=f"Successfully cleared all badges from **{user}**.",
            color=0x2b2d31
        )
        await ctx.reply(embed=embed, mention_author=False)


async def setup(client):
    await client.add_cog(Profile(client))