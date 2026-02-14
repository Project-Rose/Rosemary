import discord
from discord.ext import commands
import json
import os
import re

STAR_FILE = "starboard_data.json"
STAR_THRESHOLD = 1  # Change how many ⭐ are required

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
        
        # 1. Reply context (grey embed) - if message is a reply
        if message.reference and message.reference.message_id:
            try:
                replied_msg = await message.channel.fetch_message(message.reference.message_id)
                reply_content = replied_msg.content[:100] if replied_msg.content else "*No text content*"
                if len(replied_msg.content) > 100:
                    reply_content += "..."
                
                reply_embed = discord.Embed(
                    description=f"***Replying to {replied_msg.author.mention}***\n{reply_content}",
                    color=discord.Color.greyple(),
                    timestamp=replied_msg.created_at
                )
                reply_embed.set_author(
                    name=f"{replied_msg.author.display_name} (@{replied_msg.author.name})",
                    icon_url=replied_msg.author.display_avatar.url
                )
                
                # Add first attachment as image (limit to showing 4 attachments total)
                if replied_msg.attachments:
                    reply_embed.set_image(url=replied_msg.attachments[0].url)
                
                # Add links to additional attachments (up to 4 total)
                if len(replied_msg.attachments) > 1:
                    attachment_links = []
                    for i, attachment in enumerate(replied_msg.attachments[1:5], start=2):  # Show attachments 2-5 (indices 1-4)
                        attachment_links.append(f"[Attachment {i}]({attachment.url})")
                    
                    if attachment_links:
                        reply_embed.add_field(
                            name="📎 Additional Attachments",
                            value=" • ".join(attachment_links),
                            inline=False
                        )
                
                # Add message ID to footer
                footer_text = f"Message ID: {replied_msg.id}"
                
                # Note if there are more than 4 attachments
                if len(replied_msg.attachments) > 4:
                    footer_text += f" • +{len(replied_msg.attachments) - 4} more attachment(s)"
                
                reply_embed.set_footer(text=footer_text)
                
                embeds.append(reply_embed)
                
                # Add replied message's link embeds as SEPARATE embeds AFTER the reply context (limit to 3)
                if replied_msg.embeds:
                    reply_link_count = 0
                    total_reply_embeds = sum(1 for e in replied_msg.embeds if e.type in ['link', 'image', 'video', 'gifv', 'article', 'rich'])
                    
                    for embed in replied_msg.embeds:
                        if embed.type in ['link', 'image', 'video', 'gifv', 'article', 'rich']:
                            if reply_link_count < 3:
                                reply_link_embed = discord.Embed(
                                    title=embed.title or None,
                                    description=embed.description or None,
                                    url=embed.url or None,
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
                    
                    # Add overflow indicator if there are more than 3 embeds
                    if total_reply_embeds > 3:
                        overflow_embed = discord.Embed(
                            title="Showing Top 3 Links",
                            description=f"*+{total_reply_embeds - 3} more link(s) not shown*",
                            color=discord.Color.greyple()
                        )
                        embeds.append(overflow_embed)
                        
            except Exception as e:
                print(f"Error processing reply context: {e}")
                pass
        
        # 2. Main starred message (yellow/gold embed) - BEFORE its link embeds
        main_embed = discord.Embed(
            description=message.content or "*No text content*",
            color=discord.Color.gold(),
            timestamp=message.created_at
        )
        main_embed.set_author(
            name=f"{message.author.display_name} (@{message.author.name})",
            icon_url=message.author.display_avatar.url
        )
        
        # Add first attachment as image (limit to showing 4 attachments total)
        if message.attachments:
            main_embed.set_image(url=message.attachments[0].url)
        
        # Add links to additional attachments (up to 4 total)
        if len(message.attachments) > 1:
            attachment_links = []
            for i, attachment in enumerate(message.attachments[1:5], start=2):  # Show attachments 2-5 (indices 1-4)
                attachment_links.append(f"[Attachment {i}]({attachment.url})")
            
            if attachment_links:
                main_embed.add_field(
                    name="📎 Additional Attachments",
                    value=" • ".join(attachment_links),
                    inline=False
                )
        
        # Add message ID to footer
        footer_text = f"Message ID: {message.id}"
        
        # Note if there are more than 4 attachments
        if len(message.attachments) > 4:
            footer_text += f" • +{len(message.attachments) - 4} more attachment(s)"
        
        main_embed.set_footer(text=footer_text)
        
        embeds.append(main_embed)
        
        # 3. Add link embeds from main message AFTER the starred post (YELLOW colored, limit to 3)
        if message.embeds:
            main_link_count = 0
            total_main_embeds = sum(1 for e in message.embeds if e.type in ['link', 'image', 'video', 'gifv', 'article', 'rich'])
            
            for embed in message.embeds:
                # Only include embeds that came from links (not rich content from bots)
                if embed.type in ['link', 'image', 'video', 'gifv', 'article', 'rich']:
                    if main_link_count < 3:
                        # Convert to YELLOW embed (same color as main starred post)
                        yellow_embed = discord.Embed(
                            title=embed.title or None,
                            description=embed.description or None,
                            url=embed.url or None,
                            color=discord.Color.gold()
                        )
                        if embed.author:
                            yellow_embed.set_author(name=embed.author.name, url=embed.author.url, icon_url=embed.author.icon_url)
                        if embed.thumbnail:
                            yellow_embed.set_thumbnail(url=embed.thumbnail.url)
                        if embed.image:
                            yellow_embed.set_image(url=embed.image.url)
                        if embed.footer:
                            yellow_embed.set_footer(text=embed.footer.text, icon_url=embed.footer.icon_url)
                        embeds.append(yellow_embed)
                        main_link_count += 1
            
            # Add overflow indicator if there are more than 3 embeds
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
                
                # Create new content string
                content = f"⭐ **{star_count}** - {original_msg.jump_url}"
                
                # Create embeds
                embeds = await self.create_starboard_embeds(original_msg)
                
                # Edit the message
                await starboard_msg.edit(content=content, embeds=embeds)
                
                # Update stored star count
                self.star_data[guild_id_str][message_id_str]["stars"] = star_count
                self.save_data()
        except discord.NotFound:
            # Starboard message was deleted, clean up data
            del self.star_data[guild_id_str][message_id_str]
            self.save_data()
        except Exception as e:
            print(f"Error updating starboard message: {e}")

    # ------------------------
    # Reaction Listeners
    # ------------------------
    @commands.Cog.listener()
    async def on_message(self, message):
        """Auto-add star to new starboard entries"""
        # Only auto-star messages in starboard channel that are from the bot
        if message.channel.name == "starboard" and message.author == self.bot.user:
            try:
                await message.add_reaction("⭐")
            except discord.Forbidden:
                pass
            except Exception as e:
                print(f"Error auto-adding star to starboard: {e}")

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent):
        if str(payload.emoji) != "⭐":
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        channel = guild.get_channel(payload.channel_id)
        if channel is None:
            return

        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        guild_id = str(guild.id)
        
        # Check if this is a reaction on a starboard message
        if channel.name == "starboard":
            # Find the original message this starboard post refers to
            original_message_id = None
            for msg_id, data in self.star_data.get(guild_id, {}).items():
                if data.get("starboard_message_id") == payload.message_id:
                    original_message_id = msg_id
                    break
            
            if original_message_id:
                # Get unique users from both original and starboard messages
                unique_users = await self.get_unique_starred_users(guild, guild_id, original_message_id)
                star_count = len(unique_users)
                
                # Update the starboard message
                await self.update_starboard_message(payload.guild_id, int(original_message_id), star_count)
            return

        # This is a reaction on the original message
        message_id = str(message.id)

        # Check if message is already on starboard
        if guild_id in self.star_data and message_id in self.star_data[guild_id]:
            # Get unique users from both original and starboard messages
            unique_users = await self.get_unique_starred_users(guild, guild_id, message_id)
            star_count = len(unique_users)
            
            # Update existing starboard message
            await self.update_starboard_message(payload.guild_id, payload.message_id, star_count)
            return

        # Count stars on original message for new starboard entries
        star_count = 0
        for reaction in message.reactions:
            if str(reaction.emoji) == "⭐":
                star_count = reaction.count
                break
        else:
            return

        # Check threshold for new messages
        if star_count < STAR_THRESHOLD:
            return

        # Get starboard channel
        starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
        if starboard_channel is None:
            return

        # Create content string (non-embed text)
        content = f"⭐ **{star_count}** - {message.jump_url}"
        
        # Create embeds
        embeds = await self.create_starboard_embeds(message)
        
        # Send to starboard
        sent = await starboard_channel.send(content=content, embeds=embeds)

        # Save to JSON
        if guild_id not in self.star_data:
            self.star_data[guild_id] = {}
        
        self.star_data[guild_id][message_id] = {
            "starboard_message_id": sent.id,
            "channel_id": channel.id,
            "stars": star_count,
            "starred_users": []  # Track users who have starred this message
        }
        self.save_data()
    
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

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent):
        """Handle when stars are removed"""
        if str(payload.emoji) != "⭐":
            return

        guild = self.bot.get_guild(payload.guild_id)
        if guild is None:
            return

        channel = guild.get_channel(payload.channel_id)
        if channel is None:
            return

        guild_id = str(guild.id)
        
        # Check if this is a reaction removal on a starboard message
        if channel.name == "starboard":
            # Find the original message this starboard post refers to
            original_message_id = None
            for msg_id, data in self.star_data.get(guild_id, {}).items():
                if data.get("starboard_message_id") == payload.message_id:
                    original_message_id = msg_id
                    break
            
            if original_message_id:
                # Get unique users from both original and starboard messages
                unique_users = await self.get_unique_starred_users(guild, guild_id, original_message_id)
                star_count = len(unique_users)
                
                if star_count >= STAR_THRESHOLD:
                    # Update the starboard message
                    await self.update_starboard_message(payload.guild_id, int(original_message_id), star_count)
                else:
                    # Remove from starboard if below threshold
                    try:
                        starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
                        if starboard_channel:
                            starboard_msg_id = self.star_data[guild_id][original_message_id]["starboard_message_id"]
                            starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                            await starboard_msg.delete()
                    except:
                        pass
                    
                    # Remove from data
                    del self.star_data[guild_id][original_message_id]
                    self.save_data()
            return

        # This is a reaction removal on the original message
        try:
            message = await channel.fetch_message(payload.message_id)
        except discord.NotFound:
            return

        message_id = str(message.id)

        # Update if message is on starboard
        if guild_id in self.star_data and message_id in self.star_data[guild_id]:
            # Get unique users from both original and starboard messages
            unique_users = await self.get_unique_starred_users(guild, guild_id, message_id)
            star_count = len(unique_users)
            
            if star_count >= STAR_THRESHOLD:
                await self.update_starboard_message(payload.guild_id, payload.message_id, star_count)
            else:
                # Remove from starboard if below threshold
                try:
                    starboard_channel = discord.utils.get(guild.text_channels, name="starboard")
                    if starboard_channel:
                        starboard_msg_id = self.star_data[guild_id][message_id]["starboard_message_id"]
                        starboard_msg = await starboard_channel.fetch_message(starboard_msg_id)
                        await starboard_msg.delete()
                except:
                    pass
                
                # Remove from data
                del self.star_data[guild_id][message_id]
                self.save_data()

async def setup(bot):
    await bot.add_cog(Starboard(bot))