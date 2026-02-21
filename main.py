from discord.ext import commands
from pathlib import Path
import os
import discord
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rosemary.settings')

django.setup()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))

intents = discord.Intents.default()
intents.members = True # Example for member access
intents.message_content = True
intents.presences = True
bot = commands.Bot(
    status=discord.Status.online,
    intents=intents
)

@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user}')

cogs = bot.create_group("cogs", "Manage cogs", guild_ids=[GUILD_ID])

@cogs.command(description="Load a cog")
@discord.default_permissions(administrator=True)
async def load(ctx, cog_name: discord.Option(str)):
    try:
        bot.load_extension(f"cogs.{cog_name}")
        await ctx.respond(f"Successfully loaded cog `{cog_name}`.")
    except:
        await ctx.respond(f"Unable to load cog `{cog_name}`.")

@cogs.command(description="Unload a cog")
@discord.default_permissions(administrator=True)
async def unload(ctx, cog_name: discord.Option(str)):
    try:
        bot.unload_extension(f"cogs.{cog_name}")
        await ctx.respond(f"Successfully unloaded cog `{cog_name}`.")
    except:
        await ctx.respond(f"Unable to unload cog `{cog_name}`.")

@cogs.command(description="Reload a cog")
@discord.default_permissions(administrator=True)
async def reload(ctx, cog_name: discord.Option(str)):
    try:
        bot.unload_extension(f"cogs.{cog_name}")
        bot.load_extension(f"cogs.{cog_name}")
        await ctx.respond(f"Successfully reloaded cog `{cog_name}`.")
    except:
        await ctx.respond(f"Unable to reload cog `{cog_name}`.")

@bot.slash_command(description="Shutdown the bot", guild_ids=[GUILD_ID])
@discord.default_permissions(administrator=True)
async def shutdown(ctx):
    await ctx.respond("Shutting down!")
    await bot.close()

for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        cog = filename[:-3]
        print(f'Loading cog: {cog}')
        bot.load_extension(f'cogs.{cog}')

bot.run(TOKEN)