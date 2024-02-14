import discord
from discord.ext import commands
import uuid
import asyncio
import random
import pymysql.cursors
import roles
import variables
import config
from managequeue import QueueManager
from leaderboard import EloLeaderboard
from game import GameManager
from ban import BanManager
from elo import EloManager

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=".", intents=intents)

game_manager = GameManager(bot)
queue_manager = QueueManager(bot, game_manager)
ban_manager = BanManager(bot, game_manager, queue_manager)
elo_manager = EloManager(bot)
leaderboard = EloLeaderboard(bot)

queue_manager.set_ban_manager(ban_manager)

@bot.tree.command(name="delete_game", description="Dismiss ongoing matchmaking")
async def delete_game_command(interaction: discord.Interaction, game_id: str):
    await game_manager.delete_game(interaction, game_id)

@bot.tree.command(name="ban", description="Ban player from joining games for a set amount of hours")
async def ban_player_command(interaction: discord.Interaction, player: discord.User, hours: int, reason: str):
    await ban_manager.ban_player(interaction, player, hours, reason)

@bot.tree.command(name="unban", description="Unban a player")
async def unban_command(interaction: discord.Interaction, player: discord.User):
    await ban_manager.unban(interaction, player)

@bot.tree.command(name="join", description="Join the queue")
async def join_command(interaction: discord.Interaction):
    await queue_manager.join_queue(interaction)

@bot.tree.command(name="leave", description="Leave the queue")
async def leave_command(interaction: discord.Interaction):
    await queue_manager.leave_queue(interaction)

@bot.tree.command(name="clear_queue", description="Clear an ongoing queue")
async def clear_queue_command(interaction: discord.Interaction):
    await queue_manager.clear_queue(interaction)

@bot.tree.command(name="queue", description="Display current players in queue")
async def display_queue_command(interaction: discord.Interaction):
    await queue_manager.display_queue(interaction)

@bot.tree.command(name="stats", description="Display statistics")
async def stats_command(interaction: discord.Interaction, player: discord.User = None):
    await elo_manager.display_stats(interaction, player)

@bot.tree.command(name="penalty", description="Serve a penalty for a player. (-90 elo)")
async def penalty_command(interaction: discord.Interaction, player: discord.User, reason: str):
    await elo_manager.serve_penalty(interaction, player, reason)

@bot.tree.command(name="add_elo", description="Add custom amount of elo to a player.")
async def add_elo_command(interaction: discord.Interaction, player: discord.Member, amount: int):
    await elo_manager.add_elo(interaction, player, amount)

@bot.tree.command(name="subtract_elo", description="Subtract custom amount of elo from a player.")
async def subtract_elo_command(interaction: discord.Interaction, player: discord.User, amount: int, reason: str):
    await elo_manager.subtract_elo(interaction, player, amount, reason)

@bot.tree.command(name="register", description="Register to be able to play")
async def register_command(interaction: discord.Interaction):
    await queue_manager.register(interaction)

@bot.tree.command(name="leaderboard", description="Display leaderboard")
async def lb_command(interaction: discord.Interaction):
    await leaderboard.lb(interaction)
       
bot.run(config.TOKEN) 

