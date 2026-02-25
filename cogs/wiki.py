from discord.ext import commands
from db.models import WikiPage
from asgiref.sync import sync_to_async
from django.utils import timezone
import discord
import time

class Wiki(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
    
    @sync_to_async
    def _get_wiki_page(self, short_name):
        try:
            page = WikiPage.objects.get(short_name=short_name)
            return page
        except WikiPage.DoesNotExist:
            return None
    
    @sync_to_async
    def _get_all_wiki_pages(self):
        return list(WikiPage.objects.all())
    
    async def show_page(self, short_name, show_not_found):
        page = await self._get_wiki_page(short_name)
        if page:
            embed = discord.Embed(color=discord.Color.blue(), title=page.name, description=page.content)
            embed.set_footer(text=f"Last modified: {time.strftime("%d/%m/%Y %H:%M:%S", page.last_modified.timetuple())} ({timezone.get_current_timezone_name()})")
        elif show_not_found:
            embed = discord.Embed(color=discord.Color.red(), title="Page not found", description=f"Could not find wiki page with short name {short_name}.")
        else:
            return None
        return embed

    wiki = discord.SlashCommandGroup("wiki", "Wiki commands")

    @wiki.command(name="show", description="Show a wiki page.")
    async def wiki_show(self, ctx, short_name: discord.Option(str)):
        embed = await self.show_page(short_name, True)
        await ctx.respond(embed=embed)
    
    @wiki.command(name="list", description="List of wiki pages")
    async def wiki_list(self, ctx):
        pages = await self._get_all_wiki_pages()
        embed = discord.Embed(color=discord.Color.blue(), title="List of wiki pages", description="Use /wiki show (short name) or !(short name) to show a wiki page.")
        for page in pages:
            embed.add_field(name=page.short_name, value=page.name, inline=False)
        await ctx.respond(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, ctx: discord.Message):
        if ctx.author.id != self.bot.user.id:
            if ctx.content.startswith("!"):
                message = ctx.content.split(" ")
                if len(message) > 1:
                    # avoid accidental commands
                    return
                embed = await self.show_page(message[0].replace("!", ""), False)
                if embed:
                    await ctx.reply(embed=embed, mention_author=False)

def setup(bot):
    bot.add_cog(Wiki(bot))