import discord
from discord.ext import tasks
from discord import app_commands
import requests
import json
import os

DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
CHANNEL_ID = 1382645080447516753  # replace with your channel ID
CONFIG_FILE = "config.json"

intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)
tree = app_commands.CommandTree(bot)

status_message = None
config = {}

# Load and save config functions
def load_config():
    global config
    try:
        with open(CONFIG_FILE, "r") as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        config = {"server": "prinzcraft.com"}
        save_config()

def save_config():
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=4)


def fetch_server_status(server):
    url = f'https://api.mcsrvstat.us/2/{server}'
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        return data
    except Exception:
        return None


def create_embed(data, server):
    if data is None:
        embed = discord.Embed(
            title="⚠️ Failed to fetch server status",
            color=discord.Color.orange()
        )
        return embed

    if data.get('online'):
        online_players = data['players']['online']
        max_players = data['players']['max']
        motd = '\n'.join(data['motd']['clean'])
        version = data['version']

        embed = discord.Embed(
            title=f"🟢 {server} is Online",
            color=discord.Color.green()
        )
        embed.add_field(name="Version", value=version, inline=True)
        embed.add_field(name="Players", value=f"{online_players}/{max_players}", inline=True)
        embed.add_field(name="MOTD", value=motd, inline=False)

        if data.get('icon'):
            icon_url = f"https://api.mcsrvstat.us/icon/{server}"
            embed.set_thumbnail(url=icon_url)

    else:
        embed = discord.Embed(
            title=f"🔴 {server} is Offline or Unreachable",
            color=discord.Color.red()
        )
    return embed


@bot.event
async def on_ready():
    global status_message
    print(f'Logged in as {bot.user}')
    await tree.sync()

    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print("❌ Could not find the channel. Check your CHANNEL_ID.")
        return

    load_config()
    data = fetch_server_status(config["server"])
    embed = create_embed(data, config["server"])
    status_message = await channel.send(embed=embed)

    update_status.start()


@tasks.loop(seconds=60)
async def update_status():
    global status_message
    if status_message is None:
        return

    load_config()  # always reload latest config
    server = config["server"]
    data = fetch_server_status(server)
    embed = create_embed(data, server)
    await status_message.edit(embed=embed)


@tree.command(name="setserver", description="Set the server to monitor")
async def setserver(interaction: discord.Interaction, server: str):
    global config

    await interaction.response.defer()

    data = fetch_server_status(server)
    if data is None:
        await interaction.followup.send("⚠️ Failed to fetch server info. Invalid server?")
        return

    config["server"] = server
    save_config()

    embed = create_embed(data, server)
    await status_message.edit(embed=embed)
    await interaction.followup.send(f"✅ Monitoring server `{server}` now.")
    

bot.run(DISCORD_BOT_TOKEN)
