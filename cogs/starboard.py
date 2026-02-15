import discord
from discord.ext import commands
import os
from asgiref.sync import sync_to_async
from pathlib import Path
from db.models import StarboardMessage

STAR_THRESHOLD = int(os.getenv("STAR_THRESHOLD"))  # Change how many ⭐ are required
GUILD_ID = int(os.getenv("GUILD_ID"))

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ------------------------
    # Database Helper Methods
    # ------------------------
    @sync_to_async
    def _get_starboard_entry(self, message_id):
        """Get a starboard entry from the database"""
        try:
            return StarboardMessage.objects.get(message_id=message_id)
        except StarboardMessage.DoesNotExist:
            return None

    @sync_to_async
    def _get_starboard_entry_by_starboard_id(self, starboard_message_id):
        """Get a starboard entry by its starboard message ID"""
        try:
            return StarboardMessage.objects.filter(starboard_message_id=starboard_message_id).first()
        except:
            return None

    @sync_to_async
    def _create_starboard_entry(self, message_id, starboard_message_id, channel_id, stars):
        """Create a new starboard entry"""
        return StarboardMessage.objects.create(
            message_id=message_id,
            starboard_message_id=starboard_message_id,
            channel_id=channel_id,
            stars=stars
        )

    @sync_to_async
    def _update_starboard_entry(self, message_id, stars):
        """Update a starboard entry's star count"""
        try:
            entry = StarboardMessage.objects.get(message_id=message_id)
            entry.stars = stars
            entry.save()
            return entry
        except StarboardMessage.DoesNotExist:
            return None

    @sync_to_async
    def _delete_starboard_entry(self, message_id):
        """Delete a starboard entry"""
        try:
            StarboardMessage.objects.get(message_id=message_id).delete()
            return True
        except StarboardMessage.DoesNotExist:
            return False

    # ------------------------
    # Helper Functions
    # ------------------------
    async def create_starboard_embeds(self, message):
        """Create all embeds for starboard message in proper order"""
        embeds = []
        
        # 1. Reply context (grey embed) - ONLY for actual replies
        # Replies have type MessageType.reply, forwards have type MessageType.default
        is_reply = (message.reference and 
                   message.reference.message_id and 
                   message.type == discord.MessageType.reply)
        
        if is_reply:
            try:
                replied_msg = await message.channel.fetch_message(message.reference.message_id)
                
                reply_content = replied_msg.content[:100] if replied_msg.content else ""
                if reply_content and len(replied_msg.content) > 100:
                    reply_content += "..."
                if not reply_content and not replied_msg.attachments:
                    reply_content = "*No text content*"
                
                description = f"***Replying to {replied_msg.author.mention}***\n{reply_content}" if reply_content else f"***Replying to {replied_msg.author.mention}***"
                
                reply_embed = discord.Embed(
                    description=description,
                    color=discord.Color.greyple(),
                    timestamp=replied_msg.created_at
                )
                reply_embed.set_author(
                    name=f"{replied_msg.author.display_name} (@{replied_msg.author.name})",
                    icon_url=replied_msg.author.display_avatar.url
                )
                
                # Add attachment
                if replied_msg.attachments:
                    first_attachment = replied_msg.attachments[0]
                    if first_attachment.content_type and first_attachment.content_type.startswith('video/'):
                        reply_embed.description = f"{description}\n\n[📹 Video]({first_attachment.url})"
                    else:
                        reply_embed.set_image(url=first_attachment.url)
                
                # Additional attachments
                if len(replied_msg.attachments) > 1:
                    attachment_links = []
                    for i, attachment in enumerate(replied_msg.attachments[1:5], start=2):
                        name = f"Attachment {i}"
                        if attachment.filename.lower().endswith('.gif'):
                            name += " (GIF)"
                        elif attachment.content_type and attachment.content_type.startswith('video/'):
                            name += " (Video)"
                        attachment_links.append(f"[{name}]({attachment.url})")
                    
                    if attachment_links:
                        reply_embed.add_field(name="📎 Additional Attachments", value=" • ".join(attachment_links), inline=False)
                
                footer_text = f"Message ID: {replied_msg.id}"
                if len(replied_msg.attachments) > 4:
                    footer_text += f" • +{len(replied_msg.attachments) - 4} more attachment(s)"
                reply_embed.set_footer(text=footer_text)
                
                embeds.append(reply_embed)
                
                # Reply link embeds (limit 3)
                if replied_msg.embeds:
                    reply_link_count = 0
                    total_reply_embeds = sum(1 for e in replied_msg.embeds if e.type in ['link', 'image', 'video', 'gifv', 'article', 'rich'])
                    
                    for embed in replied_msg.embeds:
                        if embed.type in ['link', 'image', 'video', 'gifv', 'article', 'rich'] and reply_link_count < 3:
                            reply_link_embed = discord.Embed(
                                title=embed.title,
                                description=embed.description,
                                url=embed.url,
                                color=discord.Color.greyple()
                            )
                            if embed.author:
                                reply_link_embed.set_author(name=embed.author.name, url=embed.author.url, icon_url=embed.author.icon_url)
                            if embed.thumbnail:
                                reply_link_embed.set_thumbnail(url=embed.thumbnail.url)
                            if embed.image:
                                reply_link_embed.set_image(url=embed.image.url)
                            if embed.footer:
                                reply_link_embed.set_footer(text=embed.footer.text, icon_url=embed.footer.icon_url)
                            embeds.append(reply_link_embed)
                            reply_link_count += 1
                    
                    if total_reply_embeds > 3:
                        overflow_embed = discord.Embed(
                            title="Showing Top 3 Links",
                            description=f"*+{total_reply_embeds - 3} more link(s) not shown*",
                            color=discord.Color.greyple()
                        )
                        embeds.append(overflow_embed)
                        
            except discord.NotFound:
                pass
            except Exception as e:
                print(f"Error processing reply: {e}")
        
        # 2. Main starred message (yellow/gold embed)
        message_text = message.content if message.content else ""
        
        # Check if this is a forwarded message (has reference but is NOT a reply type)
        is_forward = (message.reference and 
                     message.reference.message_id and 
                     message.type != discord.MessageType.reply)
        
        if is_forward:
            # Add jump link to the forwarded message
            forward_link = f"https://discord.com/channels/{message.guild.id}/{message.reference.channel_id}/{message.reference.message_id}"
            if message_text:
                message_text = f"***[Forwarded message]({forward_link})***\n{message_text}"
            else:
                message_text = f"***[Forwarded message]({forward_link})***"
        
        # If no content and no attachments, show "No text content"
        if not message_text and not message.attachments:
            message_text = "*No text content*"
        
        main_embed = discord.Embed(
            description=message_text if message_text else None,
            color=discord.Color.gold(),
            timestamp=message.created_at
        )
        main_embed.set_author(
            name=f"{message.author.display_name} (@{message.author.name})",
            icon_url=message.author.display_avatar.url
        )
        
        # Add first attachment
        if message.attachments:
            first_attachment = message.attachments[0]
            if first_attachment.content_type and first_attachment.content_type.startswith('video/'):
                if message_text and message_text != "*No text content*":
                    main_embed.description = f"{message_text}\n\n[📹 Video]({first_attachment.url})"
                else:
                    main_embed.description = f"[📹 Video]({first_attachment.url})"
            else:
                main_embed.set_image(url=first_attachment.url)
        
        # Additional attachments
        if len(message.attachments) > 1:
            attachment_links = []
            for i, attachment in enumerate(message.attachments[1:5], start=2):
                name = f"Attachment {i}"
                if attachment.filename.lower().endswith('.gif'):
                    name += " (GIF)"
                elif attachment.content_type and attachment.content_type.startswith('video/'):
                    name += " (Video)"
                attachment_links.append(f"[{name}]({attachment.url})")
            
            if attachment_links:
                main_embed.add_field(name="📎 Additional Attachments", value=" • ".join(attachment_links), inline=False)
        
        footer_text = f"Message ID: {message.id}"
        if len(message.attachments) > 4:
            footer_text += f" • +{len(message.attachments) - 4} more attachment(s)"
        main_embed.set_footer(text=footer_text)
        
        embeds.append(main_embed)
        
        # 3. Main link embeds (yellow, limit 3)
        if message.embeds:
            main_link_count = 0
            total_main_embeds = sum(1 for e in message.embeds if e.type in ['link', 'image', 'video', 'gifv', 'article', 'rich'])
            
            for embed in message.embeds:
                if embed.type in ['link', 'image', 'video', 'gifv', 'article', 'rich'] and main_link_count < 3:
                    main_link_embed = discord.Embed(
                        title=embed.title,
                        description=embed.description,
                        url=embed.url,
                        color=discord.Color.gold()
                    )
                    if embed.author:
                        main_link_embed.set_author(name=embed.author.name, url=embed.author.url, icon_url=embed.author.icon_url)
                    if embed.thumbnail:
                        main_link_embed.set_thumbnail(url=embed.thumbnail.url)
                    if embed.image:
                        main_link_embed.set_image(url=embed.image.url)
                    if embed.footer:
                        main_link_embed.set_footer(text=embed.footer.text, icon_url=embed.footer.icon_url)
                    embeds.append(main_link_embed)
                    main_link_count += 1
            
            if total_main_embeds > 3:
                overflow_embed = discord.Embed(
                    title="Showing Top 3 Links",
                    description=f"*+{total_main_embeds - 3} more link(s) not shown*",
                    color=discord.Color.gold()
                )
                embeds.append(overflow_embed)
        
        return embeds

    async def update_starboard_message(self, message_id, star_count):
        """Update an existing starboard message with new star count"""
        message_id_str = str(message_id)

        starboard_entry = await self._get_starboard_entry(message_id_str)
        if not starboard_entry:
            return

        starboard_msg_id = starboard_entry.starboard_message_id
        
        guild = self.bot.get_guild(GUILD_ID)
        if not guild:
            return

        starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
        if not starboard_channel:
            return

        try:
            starboard_msg = await starboard_channel.fetch_message(int(starboard_msg_id))
            original_channel = guild.get_channel(int(starboard_entry.channel_id))
            
            if original_channel:
                original_msg = await original_channel.fetch_message(int(message_id_str))
                
                content = f"⭐ **{star_count}** - {original_msg.jump_url}"
                embeds = await self.create_starboard_embeds(original_msg)
                
                await starboard_msg.edit(content=content, embeds=embeds)
                
                await self._update_starboard_entry(message_id_str, star_count)
        except discord.NotFound:
            await self._delete_starboard_entry(message_id_str)
        except Exception as e:
            print(f"Error updating starboard message: {e}")

    async def get_unique_starred_users(self, guild, message_id):
        """Get unique users who starred from both original and starboard messages"""
        unique_users = set()
        
        message_id_str = str(message_id)
        
        starboard_entry = await self._get_starboard_entry(message_id_str)
        if not starboard_entry:
            return unique_users
        
        # Get stars from original message
        try:
            original_channel = guild.get_channel(int(starboard_entry.channel_id))
            if original_channel:
                original_msg = await original_channel.fetch_message(int(message_id_str))
                for reaction in original_msg.reactions:
                    if str(reaction.emoji) == "⭐":
                        async for user in reaction.users():
                            if not user.bot:
                                unique_users.add(user.id)
        except:
            pass
        
        # Get stars from starboard message
        try:
            starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
            if starboard_channel:
                starboard_msg_id = starboard_entry.starboard_message_id
                if starboard_msg_id:
                    starboard_msg = await starboard_channel.fetch_message(int(starboard_msg_id))
                    for reaction in starboard_msg.reactions:
                        if str(reaction.emoji) == "⭐":
                            async for user in reaction.users():
                                if not user.bot:
                                    unique_users.add(user.id)
        except:
            pass
        
        return unique_users

    # ------------------------
    # Reaction Listeners
    # ------------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        """Auto-add star to new starboard entries"""
        if message.channel.name == "starboard" and message.author == self.bot.user:
            try:
                await message.add_reaction("⭐")
            except:
                pass

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "⭐":
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild or payload.guild_id != GUILD_ID:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return
        
        # Check if reaction is on starboard message
        if channel.name == "starboard":
            starboard_entry = await self._get_starboard_entry_by_starboard_id(str(payload.message_id))
            
            if starboard_entry:
                original_message_id = starboard_entry.message_id
                unique_users = await self.get_unique_starred_users(guild, int(original_message_id))
                star_count = len(unique_users)
                await self.update_starboard_message(int(original_message_id), star_count)
            return

        message_id = str(message.id)

        # Check if already on starboard
        starboard_entry = await self._get_starboard_entry(message_id)
        if starboard_entry:
            unique_users = await self.get_unique_starred_users(guild, int(message_id))
            star_count = len(unique_users)
            await self.update_starboard_message(payload.message_id, star_count)
            return

        # New starboard entry
        star_count = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == "⭐":
                star_count = reaction.count
                break
        else:
            return

        if star_count < STAR_THRESHOLD:
            return

        starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
        if not starboard_channel:
            return
        content = f"⭐ **{star_count}** - {message.jump_url}"
        embeds = await self.create_starboard_embeds(message)
        
        sent = await starboard_channel.send(content=content, embeds=embeds)

        await self._create_starboard_entry(
            message_id=message_id,
            starboard_message_id=str(sent.id),
            channel_id=str(channel.id),
            stars=star_count
        )

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "⭐":
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild or payload.guild_id != GUILD_ID:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return
        
        # Check if removal is on starboard message
        if channel.name == "starboard":
            starboard_entry = await self._get_starboard_entry_by_starboard_id(str(payload.message_id))
            
            if starboard_entry:
                original_message_id = starboard_entry.message_id
                unique_users = await self.get_unique_starred_users(guild, int(original_message_id))
                star_count = len(unique_users)
                
                if star_count >= STAR_THRESHOLD:
                    await self.update_starboard_message(int(original_message_id), star_count)
                else:
                    try:
                        starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
                        if starboard_channel:
                            starboard_msg_id = starboard_entry.starboard_message_id
                            starboard_msg = await starboard_channel.fetch_message(int(starboard_msg_id))
                            await starboard_msg.delete()
                    except:
                        pass
                    
                    await self._delete_starboard_entry(original_message_id)
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        message_id = str(message.id)

        starboard_entry = await self._get_starboard_entry(message_id)
        if not starboard_entry:
            return

        unique_users = await self.get_unique_starred_users(guild, int(message_id))
        star_count = len(unique_users)
        
        if star_count >= STAR_THRESHOLD:
            await self.update_starboard_message(payload.message_id, star_count)
        else:
            try:
                starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
                if starboard_channel:
                    starboard_msg_id = starboard_entry.starboard_message_id
                    starboard_msg = await starboard_channel.fetch_message(int(starboard_msg_id))
                    await starboard_msg.delete()
            except:
                pass
            
            await self._delete_starboard_entry(message_id)

def setup(bot):
    bot.add_cog(Starboard(bot))