from discord.ext import commands
from random import choice, randint

class Miscellaneous(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
    
    @commands.Cog.listener()
    async def on_message(self, ctx):
        if self.bot.user.id == ctx.author.id:
            return
        if randint(0,512)==268:
            messages = ["david j sosa best developer on the planet.", "use tvii", "67", "it's 10 pm do you know where your tvii is?", "What the fuck", "I hate my job", "use roséverse", "mods can we ban this guy?", "god I wish I was a Wii U sometimes"]
            await ctx.channel.send(choice(messages))

def setup(bot):
    bot.add_cog(Miscellaneous(bot))