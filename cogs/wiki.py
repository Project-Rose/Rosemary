from discord.ext import commands
from db.models import WikiPage
from asgiref.sync import sync_to_async
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
    
    async def show_page(self, short_name):
        page = await self._get_wiki_page(short_name)
        if page:
            embed = discord.Embed(color=discord.Color.blue(), title=page.name, description=page.content)
            embed.set_footer(text=f"Last modified: {time.strftime("%d/%m/%Y %H:%M:%S", page.last_modified.timetuple())}")
        else:
            embed = discord.Embed(color=discord.Color.red(), title="Page not found", description="Could not find wiki page with short name "+short_name+".")
        return embed

    wiki = discord.SlashCommandGroup("wiki", "Wiki commands")

    @wiki.command(name="show", description="Show a wiki page.")
    async def wiki_show(self, ctx, short_name: discord.Option(str)):
        embed = await self.show_page(short_name)
        await ctx.respond(embed=embed)
    
    @wiki.command(name="list", description="List of wiki pages")
    async def wiki_list(self, ctx):
        pages = await self._get_all_wiki_pages()
        embed = discord.Embed(color=discord.Color.blue(), title="List of wiki pages", description="Use /wiki show (short name) or .h (short name) to show a wiki page.")
        for page in pages:
            embed.add_field(name=page.short_name, value=page.name, inline=False)
        await ctx.respond(embed=embed)

    @commands.Cog.listener()
    async def on_message(self, ctx: discord.Message):
        if ctx.author.id != self.bot.user.id:
            if ctx.content.startswith(".h"):
                message = ctx.content.split(" ")
                try:
                    embed = await self.show_page(message[1])
                    await ctx.reply(embed=embed, mention_author=False)
                except IndexError:
                    await ctx.channel.send("Not enough arguments.")

def setup(bot):
    bot.add_cog(Wiki(bot))