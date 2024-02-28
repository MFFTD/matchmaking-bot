import discord
import asyncio
from uuid import UUID
import roles
from discord.ext import commands
from discord import app_commands
from managers.game import GameManager, game_dict  # Import game_dict
from variables import BotVariables as Variables

class DeleteFives(commands.Cog, Variables):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.game_manager = GameManager(bot)  # Create an instance of GameManager
    
    @app_commands.command(name="delete_game", description="Delete a matchmaking. Usecase: For example if people did not show up to the game.")
    async def delete_fives_matchmaking(self, interaction: discord.Integration, game_id: str):
        print("game_dict:", game_dict)
        guild = self.bot.get_guild(Variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))

        captain_role = interaction.guild.get_role(roles.captain)

        if captain_role not in member.roles:
            await interaction.response.send_message("You do not have the required permissions to delete games.", ephemeral=True)
            return

        try:
            del game_dict[UUID(game_id)]
            print(game_dict)
            await interaction.response.send_message("Game deleted successfully!", ephemeral=True)
        except KeyError:
            await interaction.response.send_message("Game not found with the provided game ID.", ephemeral=True)


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        DeleteFives(bot),
        guilds=[discord.Object(id=Variables.guild_id)])



