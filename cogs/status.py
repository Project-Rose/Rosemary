from discord.ext import commands
from asgiref.sync import sync_to_async
from db.models import StatusMonitor
from datetime import datetime
from django.utils import timezone
from urllib.parse import urlparse
import discord, asyncio, os, aiohttp, humanize, http, time

GUILD_ID = int(os.getenv("GUILD_ID"))
STATUS_MONITOR_REFRESH = int(os.getenv("STATUS_MONITOR_REFRESH"))

class Status(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @sync_to_async
    def _get_monitor(self, name: str):
        try:
            return StatusMonitor.objects.get(name=name)
        except StatusMonitor.DoesNotExist:
            return None
        
    @sync_to_async
    def _update_monitor(self, monitor: StatusMonitor, new_name: str, url: str):
        if new_name:
            monitor.name = new_name
        if url:
            monitor.url = url
        monitor.save()

    @sync_to_async
    def _monitor_go_down(self, monitor: StatusMonitor):
        monitor.is_down = True
        monitor.downtime_start = timezone.now()
        monitor.save()
    
    @sync_to_async
    def _monitor_up(self, monitor: StatusMonitor):
        monitor.is_down = False
        monitor.save()
    
    @sync_to_async
    def _create_monitor(self, name: str, url: str):
        return StatusMonitor.objects.create(name=name, url=url, is_down=False, downtime_start=timezone.now())
    
    @sync_to_async
    def _delete_monitor(self, monitor: StatusMonitor):
        monitor.delete()

    @sync_to_async
    def _get_all_monitors(self):
        return list(StatusMonitor.objects.all())
    
    async def _update_monitors(self, status_channel):
        monitors = await self._get_all_monitors()
        for monitor in monitors:
            async with aiohttp.ClientSession() as session:
                try:
                    async with session.get(monitor.url) as response:
                        if str(response.status).startswith("5") or str(response.status).startswith("4"):
                            if not monitor.is_down:
                                embed = discord.Embed(color=discord.Color.red(), title=f"{monitor.name} is down!", description=f"Request failed with status code: {response.status} ({http.HTTPStatus(response.status).phrase})")
                                embed.set_footer(text=f"Last downtime: {humanize.naturaldelta(timezone.now() - monitor.downtime_start)} ago ({time.strftime("%d/%m/%Y %H:%M:%S", monitor.downtime_start.timetuple())})")
                                embed.set_thumbnail(url="attachment://offline.png")
                                offline_file = discord.File("images/offline.png", filename="offline.png")
                                await status_channel.send(embed=embed, files=[offline_file])
                                await self._monitor_go_down(monitor)
                        else:
                            if monitor.is_down:
                                embed = discord.Embed(color=discord.Color.green(), title=f"{monitor.name} is up!", description=f"Downtime duration: {humanize.naturaldelta(timezone.now() - monitor.downtime_start)}")
                                embed.set_thumbnail(url="attachment://online.png")
                                online_file = discord.File("images/online.png", filename="online.png")
                                await self._monitor_up(monitor)
                                await status_channel.send(embed=embed, files=[online_file])
                except Exception as e:
                    if not monitor.is_down:
                        embed = discord.Embed(color=discord.Color.red(), title=f"{monitor.name} is down!", description=f"Request failed with exception: {e}")
                        embed.set_footer(text=f"Last downtime: {humanize.naturaldelta(timezone.now() - monitor.downtime_start)} ago ({time.strftime("%d/%m/%Y %H:%M:%S", monitor.downtime_start.timetuple())})")
                        embed.set_thumbnail(url="attachment://offline.png")
                        offline_file = discord.File("images/offline.png", filename="offline.png")
                        await status_channel.send(embed=embed, files=[offline_file])
                        await self._monitor_go_down(monitor)


    status_monitor = discord.SlashCommandGroup("status_monitor", "Status Monitor commands", guild_ids=[GUILD_ID])

    @status_monitor.command(name="add", description="Add a status monitor")
    @discord.default_permissions(administrator=True)
    async def add_status_monitor(self, ctx, name: discord.Option(str), url: discord.Option(str)):
        parsed = urlparse(url)
        if not parsed.netloc or not parsed.scheme:
            await ctx.respond("You have not set a valid URL.")
            return
        if await self._get_monitor(name):
            await ctx.respond(f"A status monitor with the name `{name}` already exists.")
            return
        await self._create_monitor(name, url)
        await ctx.respond(f"Succesfully created monitor `{name}`.")
    
    @status_monitor.command(name="edit", description="Edit a status monitor")
    @discord.default_permissions(administrator=True)
    async def edit_status_monitor(self, ctx, monitor_name: discord.Option(str), new_name: discord.Option(str, required=False), url: discord.Option(str, required=False)):
        if not new_name and not url:
            await ctx.respond("Nothing to change.")
            return
        monitor = await self._get_monitor(monitor_name)
        if not monitor:
            await ctx.respond(f"No monitor exists with the name `{monitor_name}`.")
            return
        if url:
            parsed = urlparse(url)
            if not parsed.netloc or not parsed.scheme:
                await ctx.respond("You have not set a valid URL.")
                return
        await self._update_monitor(monitor, new_name, url)
        await ctx.respond(f"Updated monitor `{monitor_name}`.")
    
    @status_monitor.command(name="delete", description="Delete a status monitor")
    @discord.default_permissions(administrator=True)
    async def remove_status_monitor(self, ctx, monitor_name: discord.Option(str)):
        monitor = await self._get_monitor(monitor_name)
        if not monitor:
            await ctx.respond(f"No monitor exists with the name `{monitor_name}`.")
            return
        await self._delete_monitor(monitor)
        await ctx.respond(f"Successfully deleted monitor `{monitor_name}`.")
    
    @status_monitor.command(name="list", description="List all status monitors")
    @discord.default_permissions(administrator=True)
    async def list_status_monitor(self, ctx):
        monitors = await self._get_all_monitors()
        embed = discord.Embed(title="List of monitors")
        for monitor in monitors:
            embed.add_field(name=monitor.name, value=monitor.url, inline=False)
        await ctx.respond(embed=embed)
    
    @status_monitor.command(name="update", description="Manually update all status monitors")
    @discord.default_permissions(administrator=True)
    async def update_status_monitor(self, ctx):
        guild = self.bot.get_guild(GUILD_ID)
        status_channel = discord.utils.get(guild.text_channels, name="rose-server-status")
        if not status_channel:
            await ctx.respond("No status channel found.")
        await ctx.defer()
        await self._update_monitors(status_channel)
        await ctx.respond("Manually updated all status monitors.")
    
    @commands.Cog.listener()
    async def on_ready(self):
        guild = self.bot.get_guild(GUILD_ID)
        status_channel = discord.utils.get(guild.text_channels, name="rose-server-status")
        if not status_channel:
            return
        while True:
            await asyncio.sleep(STATUS_MONITOR_REFRESH)
            await self._update_monitors(status_channel)
    
def setup(bot):
    bot.add_cog(Status(bot))