# register.py
import discord
import asyncio
from discord.ext import commands
from discord import app_commands
from variables import BotVariables as Variables
from utils.db import AsyncSQLiteDB

class Register(commands.Cog):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.db = AsyncSQLiteDB()
        asyncio.create_task(self.db.connect())

    async def check_registration(self, discord_id):
        try:
            check_query = 'SELECT * from `users` WHERE `discord_id` = ?'
            params = (discord_id,)
            result = await self.db.execute_query(check_query, params, fetchall=True)
            return bool(result)
        except Exception as e:
            print(f"Error during registration check: {e}")
            return False 

    @app_commands.command(name="register", description="Register to be able to start playing")
    async def register(self, interaction: discord.Interaction):
        
        discord_id = interaction.user.id
        nick = interaction.user.display_name

        try:
            if await self.check_registration(discord_id):
                await interaction.response.send_message("You are already registered.", ephemeral=True)
                return

            insert_query = 'INSERT INTO users (discord_id, wins, losses, elo) VALUES (?, ?, ?, ?);'
            insert_params = (discord_id, 0, 0, 100)
            await self.db.execute_query(insert_query, insert_params)
            await interaction.user.edit(nick=f"[100]{nick}")
            await interaction.response.send_message("Registration successful!", ephemeral=True)
        except Exception as e:
            print(f"Error during registration: {e}")

async def setup(bot: commands.Bot) -> None:

    await bot.add_cog(
        Register(bot),
        guilds= [discord.Object(id = Variables.guild_id)])