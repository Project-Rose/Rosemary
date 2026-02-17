import discord
from discord.ext import commands
from asgiref.sync import sync_to_async
from db.models import BannedPhrase
import logging
import os

GUILD_ID = int(os.getenv("GUILD_ID"))

class Filter(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.logger = logging.getLogger(__name__)

    @sync_to_async
    def _get_phrases(self):
        return list(BannedPhrase.objects.values_list('phrase', flat=True))

    @sync_to_async
    def _add_phrase(self, phrase, user_id):
        return BannedPhrase.objects.get_or_create(phrase=phrase.lower(), added_by=str(user_id))

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.id == self.bot.user.id:
            return


        banned_phrases = await self._get_phrases()
        
        content = message.content.lower()
        if any(phrase in content for phrase in banned_phrases):
            try:
                await message.delete()
            except discord.Forbidden:
                self.logger.warning(f"Missing permissions to delete message in {message.channel.id}")


    @discord.slash_command(description="Add a phrase to the word filter", guild_ids=[GUILD_ID])
    @discord.default_permissions(administrator=True)
    async def filter_add(self, ctx, phrase: str):
        await self._add_phrase(phrase, ctx.author.id)
        await ctx.respond(f"Added `{phrase}` to the filter.")

def setup(bot):
    bot.add_cog(Filter(bot))
