import discord
from discord.ext import commands
import aiohttp
import random
from PIL import Image, ImageDraw, ImageFont
import io
from animact import async_animact

API_URLS = {
    "adance": "https://nekos.best/api/v2/dance",
    "blush": "https://nekos.best/api/v2/blush",
    "bonk": "https://api.waifu.pics/sfw/bonk",
    "cry": "https://nekos.best/api/v2/cry",
    "cuddle": "https://nekos.best/api/v2/cuddle",
    "hug": "https://nekos.best/api/v2/hug",
    "kill": None,
    "kiss": "https://nekos.best/api/v2/kiss",
    "pat": "https://nekos.best/api/v2/pat",
    "punch": "https://nekos.best/api/v2/punch",
    "shoot": None,
    "slap": "https://nekos.best/api/v2/slap",
    "wink": "https://nekos.best/api/v2/wink",
}

ROAST_LINES = [
    "I'd agree with you, but then we'd both be wrong.",
    "You have the confidence of someone who has no idea what's going on.",
    "You're not stupid—you just have bad luck thinking.",
    "Somewhere out there is a tree working overtime to replace the oxygen you waste.",
    "If laziness was a sport, you'd get lifetime achievement award.",
    "You're like a cloud. Once you disappear, it's a beautiful day.",
    "You're proof that evolution can go in reverse.",
    "You don't need a GPS. You're already lost in life.",
    "Your secrets are always safe with me. I never even listen.",
    "You're not useless. You could at least serve as a bad example."
]


class Fun(commands.Cog):
    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_ready(self):
        print("Fun Is Ready")

    async def send_action(self, ctx, action: str, target=None):
        # Function to get member object from ID or mention
        async def get_member(identifier):
            if identifier is None:
                return None
            
            # If it's already a Member object
            if isinstance(identifier, discord.Member):
                return identifier
            
            # If it's already a User object
            if isinstance(identifier, discord.User):
                return identifier
            
            # If it's a string (mention or ID)
            if isinstance(identifier, str):
                # Remove mention formatting
                user_id = identifier.replace("<@", "").replace(">", "").replace("!", "")
            else:
                return None
            
            # Try to get from guild first
            try:
                member = ctx.guild.get_member(int(user_id))
                if member:
                    return member
            except:
                pass
            
            # Try to fetch from Discord API (global support)
            try:
                user = await self.client.fetch_user(int(user_id))
                return user
            except:
                return None
        
        # Get the target member/user
        member_target = await get_member(target) if target else None
        
        # Get image URL
        if action == "kill":
            image = await async_animact.kill()
        elif action == "shoot":
            image = await async_animact.shoot()
        else:
            url = API_URLS[action]
            async with aiohttp.ClientSession() as cs:
                async with cs.get(url) as r:
                    if r.status != 200:
                        return await ctx.reply("API error occurred.", mention_author=False)

                    data = await r.json()
                    image = data["url"] if "url" in data else data["results"][0]["url"]

        # Create description
        if member_target:
            target_name = member_target.name if hasattr(member_target, 'name') else str(member_target)
            desc = f"{ctx.author.name} {action} {target_name}."
        else:
            desc = f"{ctx.author.name} used {action}."
        
        embed = discord.Embed(description=desc, colour=0x2b2d31)
        embed.set_image(url=image)

        await ctx.reply(embed=embed, mention_author=False)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def adance(self, ctx, member=None):
        await self.send_action(ctx, "adance", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def blush(self, ctx, member=None):
        await self.send_action(ctx, "blush", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def bonk(self, ctx, member=None):
        await self.send_action(ctx, "bonk", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def cry(self, ctx, member=None):
        await self.send_action(ctx, "cry", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def cuddle(self, ctx, member=None):
        await self.send_action(ctx, "cuddle", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def hug(self, ctx, member=None):
        await self.send_action(ctx, "hug", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def kill(self, ctx, member=None):
        await self.send_action(ctx, "kill", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def kiss(self, ctx, member=None):
        await self.send_action(ctx, "kiss", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def pat(self, ctx, member=None):
        await self.send_action(ctx, "pat", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def punch(self, ctx, member=None):
        await self.send_action(ctx, "punch", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def shoot(self, ctx, member=None):
        await self.send_action(ctx, "shoot", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def slap(self, ctx, member=None):
        await self.send_action(ctx, "slap", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def wink(self, ctx, member=None):
        await self.send_action(ctx, "wink", member)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def roast(self, ctx, member=None):
        # Function to get member object from ID or mention for roast command
        async def get_member(identifier):
            if identifier is None:
                return None
            
            # If it's already a Member object
            if isinstance(identifier, discord.Member):
                return identifier
            
            # If it's a string (mention or ID)
            if isinstance(identifier, str):
                # Remove mention formatting
                user_id = identifier.replace("<@", "").replace(">", "").replace("!", "")
            else:
                return None
            
            # Try to get from guild first
            try:
                member_obj = ctx.guild.get_member(int(user_id))
                if member_obj:
                    return member_obj
            except:
                pass
            
            # Try to fetch from Discord API (global support)
            try:
                user = await self.client.fetch_user(int(user_id))
                return user
            except:
                return None
        
        # Get the member/user
        member_obj = await get_member(member) if member else None
        
        # Create message
        if member_obj:
            mention = member_obj.mention if hasattr(member_obj, 'mention') else str(member_obj)
            msg = f"{mention} {random.choice(ROAST_LINES)}"
        else:
            msg = random.choice(ROAST_LINES)
        
        await ctx.reply(msg, mention_author=False)

    @commands.command()
    @commands.cooldown(1, 5, commands.BucketType.user)
    async def ship(self, ctx, user1=None, user2=None):
        # Handle preset ship combinations that always give 100%
        preset_ships = {
            ("901487880067776524", "1321800698974830624"): 100,
        }
        
        # Function to extract user ID from any input format
        def extract_user_id(input_value):
            if input_value is None:
                return None
            if isinstance(input_value, discord.Member):
                return str(input_value.id)
            if isinstance(input_value, discord.User):
                return str(input_value.id)
            # If it's a string (mention or ID)
            if isinstance(input_value, str):
                # Remove mention formatting
                cleaned = input_value.replace("<@", "").replace(">", "").replace("!", "")
                return cleaned
            return str(input_value)
        
        # Get all user IDs involved
        author_id = str(ctx.author.id)
        uid1 = extract_user_id(user1) if user1 else None
        uid2 = extract_user_id(user2) if user2 else None
        
        # Check for preset ships BEFORE handling cases
        is_preset = False
        percent = random.randint(0, 100)  # Default random percentage
        
        # Determine which users we're actually shipping
        final_uid1 = None
        final_uid2 = None
        random_ship = False  # Flag to indicate random ship
        random_member = None  # Store random member if we pick one
        
        if uid1 and uid2:
            # Two users provided
            # Check if both are same (user mention or ID)
            if uid1 == uid2:
                return await ctx.reply("You can't ship the same user!", mention_author=False)
            final_uid1 = uid1
            final_uid2 = uid2
        elif uid1 and not uid2:
            # Only one user provided - ship author with that user
            final_uid1 = author_id
            final_uid2 = uid1
        else:
            # No user provided - ship author with a random user from server (not bots)
            # First, try to fetch all members
            try:
                # Try to fetch all members
                all_members = []
                async for member in ctx.guild.fetch_members(limit=None):
                    if not member.bot and member.id != ctx.author.id:
                        all_members.append(member)
                
                # If fetch_members doesn't work or returns empty, fall back to cached members
                if not all_members:
                    all_members = [member for member in ctx.guild.members if not member.bot and member.id != ctx.author.id]
            except:
                # Fall back to cached members if fetch fails
                all_members = [member for member in ctx.guild.members if not member.bot and member.id != ctx.author.id]
            
            # Make sure we have at least one member
            if not all_members:
                # If no non-bot members, try including bots (except the command bot itself and author)
                all_members = [member for member in ctx.guild.members 
                              if member.id != self.client.user.id and member.id != ctx.author.id]
            
            if not all_members:
                return await ctx.reply("Could not find any other users in this server to ship with!", mention_author=False)
            
            # Pick ONE random member (author will be the other)
            random_member = random.choice(all_members)
            final_uid1 = author_id
            final_uid2 = str(random_member.id)
            random_ship = True
        
        # Now check if this pair is in preset ships
        for (id1, id2), percentage in preset_ships.items():
            # Check both orders (A,B) and (B,A)
            if (final_uid1 == str(id1) and final_uid2 == str(id2)) or (final_uid1 == str(id2) and final_uid2 == str(id1)):
                percent = percentage
                is_preset = True
                break
        
        # Function to get member object from ID or mention
        async def get_member(identifier, is_author=False):
            # If we need the author and identifier is the author ID
            if is_author:
                return ctx.author
            
            # If it's already a Member object (for random ships)
            if isinstance(identifier, discord.Member):
                return identifier
            
            # If it's a string ID
            if isinstance(identifier, str):
                user_id = identifier
            else:
                return None
            
            # Try to get from guild
            try:
                member = ctx.guild.get_member(int(user_id))
                if member:
                    return member
            except:
                pass
            
            # Try to fetch from Discord API
            try:
                user = await self.client.fetch_user(int(user_id))
                return user
            except:
                return None
        
        # Get member objects
        if random_ship:
            # We have author and random member
            member1 = ctx.author
            member2 = random_member
        else:
            # Check if final_uid1 is the author
            if final_uid1 == author_id:
                member1 = ctx.author
            else:
                member1 = await get_member(final_uid1)
            
            # Check if final_uid2 is the author
            if final_uid2 == author_id:
                member2 = ctx.author
            else:
                member2 = await get_member(final_uid2)
        
        if not member1 or not member2:
            return await ctx.reply("Could not find one or both users!", mention_author=False)
        
        # Check if members are the same (after conversion)
        if member1.id == member2.id:
            return await ctx.reply("You can't ship the same user!", mention_author=False)

        WIDTH, HEIGHT = 900, 450
        base = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 255))

        # Function to get avatar URL
        def get_avatar_url(member):
            if hasattr(member, 'display_avatar'):
                return member.display_avatar.url
            elif hasattr(member, 'avatar_url'):
                return member.avatar_url
            else:
                return member.default_avatar_url

        # Fetch avatars
        async with aiohttp.ClientSession() as session:
            async with session.get(get_avatar_url(member1)) as r1:
                avatar1 = Image.open(io.BytesIO(await r1.read())).convert("RGBA")
            async with session.get(get_avatar_url(member2)) as r2:
                avatar2 = Image.open(io.BytesIO(await r2.read())).convert("RGBA")

        avatar1 = avatar1.resize((100, 100))
        avatar2 = avatar2.resize((100, 100))

        base.paste(avatar1, (250, 70), avatar1)
        base.paste(avatar2, (250, 260), avatar2)

        try:
            line = Image.open("assets/line.png").convert("RGBA")
            line = line.resize((520, 360))
            base.paste(line, (180, 40), line)
        except:
            draw = ImageDraw.Draw(base)
            draw.ellipse((600, 100, 700, 200), fill="red", outline="red")
            draw.ellipse((700, 100, 800, 200), fill="red", outline="red")
            draw.polygon([(600, 150), (800, 150), (700, 300)], fill="red")
            draw.line((140, 160, 600, 150), fill="white", width=3)
            draw.line((140, 300, 600, 150), fill="white", width=3)

        draw = ImageDraw.Draw(base)

        percent_font = None
        name_font = None

        font_options = [
            "arial.ttf",
            "Arial.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "C:\\Windows\\Fonts\\arial.ttf",
            "C:\\Windows\\Fonts\\Arial.ttf"
        ]

        for font_path in font_options:
            try:
                percent_font = ImageFont.truetype(font_path, 72)
                name_font = ImageFont.truetype(font_path, 28)
                break
            except:
                continue

        if percent_font is None:
            percent_font = ImageFont.load_default()
            name_font = ImageFont.load_default()

        percent_x = 600
        percent_y = 200

        for ox in range(-3, 4):
            for oy in range(-3, 4):
                if ox or oy:
                    draw.text((percent_x + ox, percent_y + oy), f"{percent}%", fill="black", font=percent_font, anchor="mm")

        draw.text((percent_x, percent_y), f"{percent}%", fill="white", font=percent_font, anchor="mm")

        # Get usernames (not display names)
        name1 = member1.name
        name2 = member2.name
        
        name1 = name1[:12] + "..." if len(name1) > 12 else name1
        name2 = name2[:12] + "..." if len(name2) > 12 else name2

        for x in [-2, 2, 0, 0]:
            for y in [0, 0, -2, 2]:
                draw.text((250 + x, 35 + y), name1, fill="black", font=name_font)
                draw.text((250 + x, 365 + y), name2, fill="black", font=name_font)

        draw.text((250, 35), name1, fill="red", font=name_font)
        draw.text((250, 365), name2, fill="red", font=name_font)

        buffer = io.BytesIO()
        base.save(buffer, format="PNG")
        buffer.seek(0)

        if is_preset:
            message = f"**MAFE FOR EACH OTHER** 💘 {member1.name} × {member2.name} = {percent}%"
        elif percent >= 90:
            message = f"**PERFECT MATCH!** ❤️ {member1.name} × {member2.name} = {percent}%"
        elif percent >= 70:
            message = f"**Great chemistry!** ✨ {member1.name} × {member2.name} = {percent}%"
        elif percent >= 50:
            message = f"**Not bad!** 💕 {member1.name} × {member2.name} = {percent}%"
        elif percent >= 30:
            message = f"**Could work...** 🤔 {member1.name} × {member2.name} = {percent}%"
        else:
            message = f"**Better as friends** 😅 {member1.name} × {member2.name} = {percent}%"
        
        # Add note if it's a random ship
        if random_ship:
            message = f"**Random Ship!** 🎲 " + message

        await ctx.reply(
            content=message,
            file=discord.File(fp=buffer, filename="ship.png"),
            mention_author=False
        )


async def setup(client):
    await client.add_cog(Fun(client))