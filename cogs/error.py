from discord.ext import commands
from db.models import Error
from asgiref.sync import sync_to_async
import discord

class ErrorDatabase(commands.Cog):
    def __init__(self, bot):
        self.bot: discord.Bot = bot
    
    @sync_to_async
    def _get_error(self, error_code):
        try:
            error = Error.objects.get(code=error_code)
            return error
        except Error.DoesNotExist:
            return None      

    @commands.slash_command(description="Search for an error in the error database")
    async def error(self, ctx, error_code: discord.Option(str)):
        error = await self._get_error(error_code)
        if error:
            color_list = {"R": discord.Color.green(), "T": discord.Color.dark_red()}
            embed = discord.Embed(color=color_list[error.type], title=f"{error_code} ({error.get_type_display()})")
            embed.add_field(name="Name", value=f"`{error.name}`", inline=False)
            embed.add_field(name="Description", value=error.description, inline=False)
            embed.add_field(name="Solutions", value=error.solution, inline=False)
        else:
            embed = discord.Embed(color=discord.Color.red(), title="Error not found", description=f"Could not find any info about error {error_code}.")
        await ctx.respond(embed=embed)

    
def setup(bot):
    bot.add_cog(ErrorDatabase(bot))