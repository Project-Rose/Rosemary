import discord
from discord.ext import commands
import json
import os

STAR_FILE = "starboard_data.json"
STAR_THRESHOLD = 5  # Change how many ⭐ are required

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.star_data = self.load_data()

    # ------------------------
    # JSON Persistence
    # ------------------------
    def load_data(self):
        if not os.path.exists(STAR_FILE):
            return {}
        with open(STAR_FILE, "r") as f:
            return json.load(f)

    def save_data(self):
        with open(STAR_FILE, "w") as f:
            json.dump(self.star_data, f, indent=4)

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

    async def update_starboard_message(self, guild_id, message_id, star_count):
        """Update an existing starboard message with new star count"""
        guild_id_str = str(guild_id)
        message_id_str = str(message_id)

        if guild_id_str not in self.star_data or message_id_str not in self.star_data[guild_id_str]:
            return

        starboard_msg_id = self.star_data[guild_id_str][message_id_str]["starboard_message_id"]
        
        guild = self.bot.get_guild(guild_id)
        if not guild:
            return

        starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
        if not starboard_channel:
            return

        try:
            starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
            original_channel = guild.get_channel(int(self.star_data[guild_id_str][message_id_str].get("channel_id", 0)))
            
            if original_channel:
                original_msg = await original_channel.fetch_message(int(message_id_str))
                
                content = f"⭐ **{star_count}** - {original_msg.jump_url}"
                embeds = await self.create_starboard_embeds(original_msg)
                
                await starboard_msg.edit(content=content, embeds=embeds)
                
                self.star_data[guild_id_str][message_id_str]["stars"] = star_count
                self.save_data()
        except discord.NotFound:
            del self.star_data[guild_id_str][message_id_str]
            self.save_data()
        except Exception as e:
            print(f"Error updating starboard message: {e}")

    async def get_unique_starred_users(self, guild, guild_id, message_id):
        """Get unique users who starred from both original and starboard messages"""
        unique_users = set()
        
        guild_id_str = str(guild_id)
        message_id_str = str(message_id)
        
        if guild_id_str not in self.star_data or message_id_str not in self.star_data[guild_id_str]:
            return unique_users
        
        data = self.star_data[guild_id_str][message_id_str]
        
        # Get stars from original message
        try:
            original_channel = guild.get_channel(data.get("channel_id"))
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
                starboard_msg_id = data.get("starboard_message_id")
                if starboard_msg_id:
                    starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
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
        if not guild:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        guild_id = str(guild.id)
        
        # Check if reaction is on starboard message
        if channel.name == "starboard":
            original_message_id = None
            for msg_id, data in self.star_data.get(guild_id, {}).items():
                if data.get("starboard_message_id") == payload.message_id:
                    original_message_id = msg_id
                    break
            
            if original_message_id:
                unique_users = await self.get_unique_starred_users(guild, guild_id, original_message_id)
                star_count = len(unique_users)
                await self.update_starboard_message(payload.guild_id, int(original_message_id), star_count)
            return

        message_id = str(message.id)

        # Check if already on starboard
        if guild_id in self.star_data and message_id in self.star_data[guild_id]:
            unique_users = await self.get_unique_starred_users(guild, guild_id, message_id)
            star_count = len(unique_users)
            await self.update_starboard_message(payload.guild_id, payload.message_id, star_count)
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

        if guild_id not in self.star_data:
            self.star_data[guild_id] = {}
        
        self.star_data[guild_id][message_id] = {
            "starboard_message_id": sent.id,
            "channel_id": channel.id,
            "stars": star_count
        }
        self.save_data()

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "⭐":
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        channel = guild.get_channel(payload.channel_id)
        if not channel:
            return

        guild_id = str(guild.id)
        
        # Check if removal is on starboard message
        if channel.name == "starboard":
            original_message_id = None
            for msg_id, data in self.star_data.get(guild_id, {}).items():
                if data.get("starboard_message_id") == payload.message_id:
                    original_message_id = msg_id
                    break
            
            if original_message_id:
                unique_users = await self.get_unique_starred_users(guild, guild_id, original_message_id)
                star_count = len(unique_users)
                
                if star_count >= STAR_THRESHOLD:
                    await self.update_starboard_message(payload.guild_id, int(original_message_id), star_count)
                else:
                    try:
                        starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
                        if starboard_channel:
                            starboard_msg_id = self.star_data[guild_id][original_message_id]["starboard_message_id"]
                            starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                            await starboard_msg.delete()
                    except:
                        pass
                    
                    del self.star_data[guild_id][original_message_id]
                    self.save_data()
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        message_id = str(message.id)

        if guild_id in self.star_data and message_id in self.star_data[guild_id]:
            unique_users = await self.get_unique_starred_users(guild, guild_id, message_id)
            star_count = len(unique_users)
            
            if star_count >= STAR_THRESHOLD:
                await self.update_starboard_message(payload.guild_id, payload.message_id, star_count)
            else:
                try:
                    starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
                    if starboard_channel:
                        starboard_msg_id = self.star_data[guild_id][message_id]["starboard_message_id"]
                        starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                        await starboard_msg.delete()
                except:
                    pass
                
                del self.star_data[guild_id][message_id]
                self.save_data()

async def setup(bot):
    await bot.add_cog(Starboard(bot))
