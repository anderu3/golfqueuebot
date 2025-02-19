import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio

load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.reactions = True
intents.messages = True
intents.message_content = True
intents.guilds = True
bot = commands.Bot(command_prefix='!', intents=intents)

# dictionary to store poll data
polls = {}
poll_messages = {}

@bot.event
async def on_ready():
    print(f'Bot is ready. Logged in as {bot.user}')

class CourseInputModal(discord.ui.Modal):
    def __init__(self):
        super().__init__(title="Enter Course & Date Info")
        self.course_info = discord.ui.TextInput(label="Course & Date", placeholder="E.g., Lynnwood GC Mar 15, 4PM")
        self.add_item(self.course_info)

    async def on_submit(self, interaction: discord.Interaction):
        course_details = self.course_info.value.strip()
        
        await interaction.response.defer()

        poll_message = await interaction.channel.send(
            f"{interaction.user.mention} starting a game, who tryna play\n"
            f"{course_details}\n\n"
            f"1.\n"
            f"2.\n"
            f"3.\n"
            f"4.\n"
        )

        polls[poll_message.id] = {"down": [], "details": course_details}

        await poll_message.add_reaction('✅')

        # delete the original message that contains the button
        if interaction.message.id in poll_messages:
            await poll_messages[interaction.message.id].delete()

class ModalButton(discord.ui.Button):
    def __init__(self):
        super().__init__(label="Schedule Game", style=discord.ButtonStyle.primary)  # change the label here

    async def callback(self, interaction: discord.Interaction):
        await interaction.response.send_modal(CourseInputModal())

class ModalView(discord.ui.View):
    def __init__(self):
        super().__init__()
        self.add_item(ModalButton())

@bot.command(name="start")
async def createpoll(ctx):
    message = await ctx.send("Click to make, type out the date, Discord channel doesnt recognize punctuation:", view=ModalView())
    poll_messages[message.id] = message

@bot.event
async def on_reaction_add(reaction, user):
    if user.bot:
        return

    message = reaction.message
    if message.id not in polls:
        return

    poll_data = polls[message.id]

    if reaction.emoji == '✅' and user.display_name not in poll_data["down"]:
        if len(poll_data["down"]) < 4:  # Limit to 1 player for debugging
            poll_data["down"].append(user.display_name)

    await update_poll_message(message, poll_data)

    if len(poll_data["down"]) == 4:  # Check for 1 player for debugging
        down_list = poll_data["down"] + [""] * (4 - len(poll_data["down"]))  # Fill up to 4 slots
        await create_event_channel(message.guild, poll_data["details"], poll_data["down"], down_list)
        await message.clear_reactions()  # Disable further reactions
        await message.edit(content=f"{message.content}\n\nPoll closed.")

@bot.event
async def on_raw_reaction_remove(payload):
    guild = bot.get_guild(payload.guild_id)
    if guild is None:
        return

    channel = guild.get_channel(payload.channel_id)
    if channel is None:
        return

    message = await channel.fetch_message(payload.message_id)
    if message is None:
        return

    if message.id not in polls:
        return

    poll_data = polls[message.id]

    user = guild.get_member(payload.user_id)
    if user is None:
        user = await bot.fetch_user(payload.user_id)
        if user is None:
            return

    if user.bot:
        return

    if user.display_name in poll_data["down"]:
        poll_data["down"].remove(user.display_name)

    await update_poll_message(message, poll_data)

async def update_poll_message(message, poll_data):
    """Update the poll message content based on the current votes."""
    down_list = poll_data["down"] + [""] * (4 - len(poll_data["down"]))  # fill up to 4 slots

    new_content = (
        f"{message.content.splitlines()[0]}\n"
        f"{message.content.splitlines()[1]}\n\n"
        f"1. {down_list[0]}\n"
        f"2. {down_list[1]}\n"
        f"3. {down_list[2]}\n"
        f"4. {down_list[3]}\n"
    )

    await message.edit(content=new_content)

async def create_event_channel(guild, event_name, members, down_list):
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True)
    }

    for member_name in members:
        member = discord.utils.get(guild.members, name=member_name)
        if member:
            overwrites[member] = discord.PermissionOverwrite(read_messages=True)

    # find the "Text Channels" category
    category = discord.utils.get(guild.categories, name="Text Channels")

    if category:
        channel = await category.create_text_channel(event_name, overwrites=overwrites)
    else:
        channel = await guild.create_text_channel(event_name, overwrites=overwrites)
    
    await channel.send(f"Event: {event_name}\nPlayers: {', '.join(down_list)}")

bot.run(TOKEN)