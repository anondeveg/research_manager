import discord
from discord.ext import commands
import os
from dotenv import load_dotenv

load_dotenv()
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
TOKEN = os.environ.get("token")


@bot.event
async def on_ready():
    print("bot is up and ready!!")
    await bot.load_extension("modules.demands")
    await bot.load_extension("modules.resources")

    try:
        await bot.tree.sync()
        print(f"✅ Commands synced. Logged in as {bot.user}")
    except Exception as e:
        print(f"❌ Failed to sync commands: {e}")


bot.run(token=TOKEN)
