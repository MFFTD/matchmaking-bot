import discord
import asyncio
import uuid
import variables
import roles
from discord import app_commands
from discord.ext import commands
from variables import BotVariables as Variables

class BanManager(commands.Cog, Variables):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.ban_timers = {}

    async def remove_ban_after_delay(self, user, hours):
        try:
            await asyncio.sleep(hours * 3600)
            if user.id in self.ban_timers:
                del self.ban_timers[user.id]
                try:
                    await user.send(f"{user.mention} Your ban in Misfits 5S has expired. You are able to join games again.")
                except discord.Forbidden:
                    print(f"Unable to send a message to {user.display_name}. They may have disabled direct messages or blocked the bot.")
            else:
                pass
        except asyncio.CancelledError:
            pass

    @app_commands.command(name="ban", description="Ban player from joining games for a set amount of time")
    async def ban(self, interaction: discord.Interaction, player: discord.User, hours: int, reason: str):
        
        if not player.display_name.startswith("["):
            await interaction.response.send_message("Player is not registered.", ephemeral=True)
            return
            
        queue_instance = self.bot.get_cog("Queue")
    
        ban_id = uuid.uuid4()
        hours_text = "hour" if hours == 1 else "hours"

        guild = self.bot.get_guild(Variables.guild_id)
        member = await guild.fetch_member(int(interaction.user.id))

        captain_role = guild.get_role(roles.captain)

        if captain_role not in member.roles:
            await interaction.response.send_message("You do not have the required role to use this command.", ephemeral=True)
            return
            
        if player is None:
            await interaction.response.send_message("Player not found.", ephemeral=True)
            return

        if player in queue_instance.queue:
            queue_instance.queue.remove(player)

        timer = asyncio.create_task(self.remove_ban_after_delay(player, hours))
        self.ban_timers[player.id] = timer

        public_ban_embed = discord.Embed(
            description=f"{player.mention} has been banned from joining games for {hours} {hours_text}.",
            color=0xFFFF00,
        )

        public_ban_embed.set_footer(text=f"BAN ID {ban_id}", icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png")
        ban_log_embed = discord.Embed(
            title=f"Player banned: {player}",
            description=f"Time: `{hours} hours`\nBan author: `{interaction.user}`\nBan ID: `{ban_id}`\nReason: \n```{reason}```",
            color=0xFFFF00,
        )
        await interaction.response.send_message(embed=public_ban_embed)
        try:
            await player.send(
                f"{player.mention} You have been banned from joining games for {hours} hours by {interaction.user}.\n If you think the ban is unfair or not justified, contact any of the staff in the server and provide them with this ID: {ban_id}."
            )
        except discord.Forbidden:
            pass

        ban_log_channel = self.bot.get_channel(Variables.ban_log_id)
        await ban_log_channel.send(embed=ban_log_embed)

    @app_commands.command(name="unban", description="Unban player")
    async def unban(self, interaction: discord.Interaction, player: discord.User):
        guild = self.bot.get_guild(Variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))

        captain_role = interaction.guild.get_role(roles.captain)

        if captain_role in member.roles:
            if player:
                if player.id in self.ban_timers:
                    del self.ban_timers[player.id]
                    try:
                        await player.send(f'{player.mention} You have been unbanned in Misfits 5S. You are now able to join games again.')
                    except discord.Forbidden:
                        pass
                    await interaction.response.send_message("Player unbanned. User notified.", ephemeral=True)
                else:
                    await interaction.response.send_message("Player is not banned.", ephemeral=True)
            else:
                await interaction.response.send_message("Error unbanning.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        BanManager(bot),
        guilds = [discord.Object(id = Variables.guild_id )])     
