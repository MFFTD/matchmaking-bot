import discord
import asyncio
import uuid
import variables
import roles
from db import connect_to_database
from managequeue import QueueManager

class BanManager:
    def __init__(self, bot, game_manager, queue_manager):
        self.bot = bot
        self.ban_timers = {}
        self.queue_manager = queue_manager 
        self.connection = connect_to_database()
        self.queue_manager = queue_manager 

    async def remove_ban_after_delay(self, user, hours):
        try:
            await asyncio.sleep(hours * 3600)
            await user.send(f"{user.mention} Your ban in Misfits 5S has expired. You are able to join games again.")
            del self.ban_timers[user.id]
        except asyncio.CancelledError:
            pass

    async def ban_player(self, interaction, player, hours, reason):
        ban_log_channel = self.bot.get_channel(variables.ban_log_id)
        ban_id = uuid.uuid4()
        hours_text = "hour" if hours == 1 else "hours"

        guild = self.bot.get_guild(variables.guild_id)
        member = await guild.fetch_member(int(interaction.user.id))

        captain_role = guild.get_role(roles.captain)

        if captain_role in member.roles:
            if player:
                # Remove player from the queue if they are in it
                if player in self.queue_manager.queue:
                    self.queue_manager.queue.remove(player)

                timer = asyncio.create_task(self.remove_ban_after_delay(player, hours))
                self.ban_timers[player.id] = timer

                public_ban_embed = discord.Embed(
                    description=f"{player.mention} has been banned from joining games for {hours} {hours_text}.",
                    color=0xFFFF00,
                )
                public_ban_embed.set_footer(text=f"BAN ID {ban_id}", icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png")

                ban_log_embed = discord.Embed(
                    title=f"{player.display_name}",
                    description=f"**TIME** `{hours} hours`\n**BAN AUTHOR** `{interaction.user}`\n**BAN ID** `{ban_id}`\n**REASON**\n```{reason}```",
                    color=0xFFFF00,
                )

                await interaction.response.send_message(embed=public_ban_embed)

                if await player.send(
                        f"{player.mention} You have been banned from joining games for {hours} hours by {interaction.user}.\n If you think the ban is unfair or not justified, contact any of the placeholders in the server and provide them with this ID: {ban_id}."):
                    pass
                else:
                    pass

                await ban_log_channel.send(embed=ban_log_embed)
            else:
                await interaction.response.send_message("Invalid user.", ephemeral=True)
        else:
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)

    async def unban(self, interaction, player):

        guild = self.bot.get_guild(variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))

        captain_role = interaction.guild.get_role(roles.captain)

        if captain_role in member.roles:
            if player:
                del self.ban_timers[player.id]
                print(self.ban_timers)
                await interaction.response.send_message("Player unbanned.", ephemeral=True)
            else:
                await interaction.response.send_message("Error unbanning.", ephemeral=True)
