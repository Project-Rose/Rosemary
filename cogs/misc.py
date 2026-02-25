from discord.ext import commands
from random import choice, randint
from db.models import User
from asgiref.sync import sync_to_async
import discord
import asyncio
import json
import os

GUILD_ID = int(os.getenv("GUILD_ID"))

class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
        self.random_messages = json.load(open("data/random_messages.json", "r"))
    
    @sync_to_async
    def _find_user(self, discord_id):
        try:
            user = User.objects.get(discord_id=discord_id)
            return user
        except User.DoesNotExist:
            return None
    
    @sync_to_async
    def _set_active(self, user):
        user.is_active = True
        user.save()

    @commands.Cog.listener()
    async def on_message(self, ctx):
        if self.bot.user.id == ctx.author.id:
            return
        if randint(0,512)==268:
            await ctx.channel.send(choice(self.random_messages))
        
    @commands.Cog.listener()
    async def on_ready(self):
        wiiu_games = json.load(open("data/wiiu_games.json", "r"))
        while True:
            await self.bot.change_presence(activity=discord.Game(choice(wiiu_games)))
            await asyncio.sleep(300)

    @commands.slash_command(description="Returns the bot's latency in milliseconds")
    async def ping(self, ctx):
        latency = self.bot.latency * 1000
        await ctx.respond(f"Pong! `{latency:.2f} ms` 🏓")
    
    @commands.slash_command(description="Activate your account on the web frontend", guild_ids=[GUILD_ID])
    @discord.default_permissions(administrator=True)
    async def activate(self, ctx, code: discord.Option(str)):
        user = await self._find_user(str(ctx.author.id))
        if user:
            if user.code == code:
                if not user.is_active:
                    await self._set_active(user)
                    await ctx.respond("Your account was successfully activated.", ephemeral=True)
                else:
                    await ctx.respond("This account was already activated!", ephemeral=True)
            else:
                await ctx.respond("Invalid code.", ephemeral=True)
        else:
            await ctx.respond("No account associated with this discord account exists.", ephemeral=True)

def setup(bot):
    bot.add_cog(Miscellaneous(bot))
