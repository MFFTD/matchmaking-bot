import discord
from discord.ext import commands
import os
import config
import logging

# Configure logging to a file
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w')
logging.basicConfig(level=logging.INFO, handlers=[handler])

class MyBot(commands.Bot):

    def __init__(self):
        super().__init__(command_prefix='$', intents=discord.Intents.all(), application_id=1211706737845997659)
        self.initial_extensions = [
            'cogs.register',
            'cogs.q',
            'cogs.ban',
            'cogs.leaderboard',
            'cogs.elo',
            'cogs.delete'
        ]

    async def setup_hook(self):
        for ext in self.initial_extensions:
            await self.load_extension(ext)
        """
        await bot.tree.sync(guild=discord.Object(id=1201918611590221896))
        """
bot = MyBot()
bot.run(config.TOKEN)
