import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import requests

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")

bot = commands.Bot(command_prefix='!', intents=intents)

# Default server and channel
monitored_server = "play.example.com"
status_channel_id = None  # no channel at first

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
    except Exception as e:
        print(e)
    update_status.start()

# Slash command to change monitored server
@bot.tree.command(name="set_server", description="Set Minecraft server address")
@app_commands.describe(server_address="The Minecraft server address")
async def set_server(interaction: discord.Interaction, server_address: str):
    global monitored_server
    monitored_server = server_address
    await interaction.response.send_message(f"Monitored server updated to: {server_address}")

# Slash command to set the status channel
@bot.tree.command(name="set_channel", description="Set the channel where status will be posted")
async def set_channel(interaction: discord.Interaction):
    global status_channel_id
    status_channel_id = interaction.channel.id
    await interaction.response.send_message(f"Status updates will now be posted in this channel.")

# Background task to update status every 5 minutes
@tasks.loop(minutes=5)
async def update_status():
    global monitored_server, status_channel_id

    if status_channel_id is None:
        print("No status channel set yet.")
        return

    url = f"https://api.mcsrvstat.us/2/{monitored_server}"
    response = requests.get(url)
    data = response.json()

    channel = bot.get_channel(status_channel_id)
    if not channel:
        print("Channel not found!")
        return

    embed = discord.Embed(title="Minecraft Server Status", color=discord.Color.green())

    if data.get("online"):
        embed.add_field(name="Server", value=monitored_server, inline=False)
        embed.add_field(name="Players", value=f"{data['players']['online']}/{data['players'].get('max', '?')}", inline=False)
    else:
        embed.description = f"{monitored_server} is offline."
        embed.color = discord.Color.red()

    await channel.send(embed=embed)
