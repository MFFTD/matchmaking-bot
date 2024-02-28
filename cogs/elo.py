import discord
import asyncio
import roles
from discord import app_commands
from discord.ext import commands
from utils.db import AsyncSQLiteDB
from variables import BotVariables as Variables
#from db import connect_to_database 

class Statistics(commands.Cog, Variables):
    def __init__(self, bot):
        self.bot = bot
        self.db = AsyncSQLiteDB()
        asyncio.create_task(self.db.connect())

    @app_commands.command(name="stats", description="Display statistics")
    async def display_stats(self, interaction: discord.Interaction, player: discord.User):

        def calculate_wlr(wins, losses):
            if losses == 0:
                return wins
            else:
                return wins / losses

        if player:
            discord_id = player.id
            try:
                sql_get_stats = "SELECT `elo`, `wins`, `losses` FROM `users` WHERE `discord_id` = ?"
                params = (discord_id,)
                result = await self.db.execute_query(sql_get_stats, params, fetchall=True)
            except Exception as e:
                print(f"Error in fetching {player} statistics: {e}.")

        if result:
            elo = result[0][0]
            wins = result[0][1]  
            losses = result[0][2] 
            wlr = calculate_wlr(wins, losses)
            # These are to color text in embed
            ansi_wins = f"```ansi\n[2;31m[2;32m[1;32m{wins}[0m[2;32m[0m[2;31m[0m\n```"
            ansi_losses = f"```ansi\n[2;31m[1;31m{losses}[0m[2;31m[0m\n```"
            ansi_elo = f"```ansi\n[1;2m[1;33m{elo}[0m[0m\n```"
            ansi_wlr = f"```ansi\n[2;36m[1;36m{wlr:.2f}[0m[2;36m[0m\n```"
            
            stats_embed = discord.Embed(
                title=f"Stats for {player.display_name}",
                description=f"**Elo** {ansi_elo}\n**Wins** {ansi_wins}\n**Losses** {ansi_losses}\n**Win-Loss Ratio** {ansi_wlr}\n\n",
                color=0xFFFF00,
            )
            stats_embed.set_footer(text=f"Misfits5s", icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png")
            stats_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1007243398119436390/1202013799159431188/misfits.gif?ex=65cbe996&is=65b97496&hm=1397ca9f1d0b1c5afe32adeb2ad2b53fd8c35adc08fe371443a0543c202bcd62&")
            
            await interaction.response.send_message(embed=stats_embed, ephemeral=False)
        else:
            await interaction.response.send_message("Player is not registered.", ephemeral=True)
    
    @app_commands.command(name="add_elo", description="Add custom amount of elo to a player")
    async def add_elo(self, interaction: discord.Interaction, player: discord.Member, amount: int):

        discord_id = player.id
        member = await interaction.guild.fetch_member(int(interaction.user.id)) 
        captain_role = interaction.guild.get_role(roles.captain)

        if not captain_role in member.roles:
            await interaction.response.send_message("You do not have the required permissions to serve penalties.", ephemeral=True)
            return

        if amount <= 0:
            await interaction.response.send_message("Amount must be a positive number.\nUse `/substract_elo` if you need to `-` Elo from a player.", ephemeral=True)
            return
        
        if player is None:
            await interaction.response.send_message("Player is not in this Discord server.", ephemeral=True)
            return

        try:
            sql_update_elo = "UPDATE `users` SET elo = elo + ? WHERE discord_id = ?"
            params = amount, discord_id
            await self.db.execute_query(sql_update_elo, params)
            
            display_name_without_elo = player.display_name.split(']')[1]
            current_elo = int(player.display_name.split(']')[0][1:])
            new_elo = max(0, current_elo + amount)

            await player.edit(nick=f"[{new_elo}]{display_name_without_elo}")

            guild = self.bot.get_guild(Variables.guild_id)    
            elo_add_log_channel = self.bot.get_channel(Variables.elo_add_log_id) 
            await elo_add_log_channel.send(f"```Current elo[{current_elo}] + Added elo[{amount}]\n=New elo[{new_elo}]\n\nElo added to {player} by {interaction.user}```")
            await interaction.response.send_message(f"{amount} Elo added successfully to player {player}.", ephemeral=True)
        except Exception as e: 
            print("Interaction not found. This might be due to a timeout.")
            
    @app_commands.command(name="substract_elo", description="Substract custom amount of elo from a player")
    async def substract_elo(self, interaction: discord.Interaction, player: discord.Member, amount: int):

        discord_id = player.id
        guild = self.bot.get_guild(Variables.guild_id)    
        penalty_log_channel = self.bot.get_channel(Variables.penalty_log_id) 
        member = await interaction.guild.fetch_member(int(interaction.user.id)) 
        captain_role = interaction.guild.get_role(roles.captain)

        if not captain_role in member.roles:
            await interaction.response.send_message("You do not have the required permissions to serve penalties.")
            return

        if amount <= 0:
            await interaction.response.send_message("Enter the number as a positive. It is still going to be a substraction of Elo.\nFor example enter 10 as an amount if you want to remove 10 elo from a player.", ephemeral=True)
            return

        if not player.display_name.startswith("["):
            await interaction.response.send_message("Player is not registered.", ephemeral=True)
            return

        try:
            sql_update_elo = """
                UPDATE `users` 
                SET `elo` = CASE WHEN `elo` <= ? THEN 0
                ELSE `elo` - ? END 
                WHERE `discord_id` = ?
            """
            params = (amount, amount, discord_id)
            await self.db.execute_query(sql_update_elo, params)
            
            display_name_without_elo = player.display_name.split(']')[1]
            current_elo = int(player.display_name.split(']')[0][1:])
            new_elo = max(0, current_elo - amount)

            await player.edit(nick=f"[{new_elo}]{display_name_without_elo}")
            await interaction.response.send_message(f"{amount} Elo removed successfully.", ephemeral=True)
            await penalty_log_channel.send(f"{amount} Elo removed to player {player} by {interaction.user.display_name}")
        except Exception as e:
            await interaction.response.send_message(f"Error subtracting elo: {e}", ephemeral=True)
        
    
    @app_commands.command(name="penalty", description="Serve a penalty to a player (-30 Elo)")
    async def serve_penalty(self, interaction: discord.Interaction, player: discord.User, reason: str):
        penalty = 30
        discord_id = player.id
        guild = self.bot.get_guild(Variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))

        captain_role = interaction.guild.get_role(roles.captain)

        if captain_role not in member.roles:
            await interaction.response.send_message("You do not have the required permissions to serve penalties.", ephemeral=True)
            return

        if player is None:
            await interaction.response.send_message("Player is not in this Discord server.", ephemeral=True)
            return

        try:
            sql_update_elo = "UPDATE `users` SET `elo` = `elo` - ? WHERE `discord_id` = ?"
            params = (penalty, discord_id)
            await self.db.execute_query(sql_update_elo, params)

            display_name_without_elo = player.display_name.split(']')[1]
            current_elo = int(player.display_name.split(']')[0][1:])
            new_elo = max(0, current_elo - penalty)

            await player.edit(nick=f"[{new_elo}]{display_name_without_elo}")

            penalty_log_channel = guild.get_channel(Variables.penalty_log_id)
            await penalty_log_channel.send(f"```Current elo[{current_elo}] - penalty[{penalty}]\n=New elo[{new_elo}]\n\nPenalty served for user {player} by {interaction.user}\n\nReason:\n{reason}```")
            await interaction.response.send_message(f"Penalty served successfully to {player}.")
        except Exception as e:
            print(f"An error occurred: {e}")
            await interaction.response.send_message("An error occurred while serving the penalty.", ephemeral=True)

    @app_commands.command(name="add_win", description="Example Usecase: If captain scored for the wrong team, give wins to the actual winning team players")
    async def add_win(
        self, 
        interaction: discord.Interaction, 
        player: discord.User,
        player2: discord.User = None,
        player3: discord.User = None,
        player4: discord.User = None,
        player5: discord.User = None,          
        ):
        
        discord_ids = [player.id]
        players = [player.display_name]

        for p in [player2, player3, player4, player5]:
            if p and p.id not in discord_ids:
                discord_ids.append(p.id)
                players.append(p.display_name)
        
        guild = self.bot.get_guild(Variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))

        captain_role = interaction.guild.get_role(roles.captain)

        if captain_role not in member.roles:
            await interaction.response.send_message("You do not have the required permissions to update wins.", ephemeral=True)
            return

        if player is None:
            await interaction.response.send_message("Player not found.", ephemeral=True)
            return
        
        try:
            placeholders = ', '.join('?'for _ in discord_ids)
            sql_add_a_win = f"UPDATE `users` SET `wins` = `wins` + 1 WHERE `discord_id` IN {placeholders}"
            params = (discord_ids)
            await self.db.execute_query(sql_add_a_win, params)

            player_text = "players" if len(players) > 1 else "player"
            players_string = ', '.join(players)
            await interaction.response.send_message(f"Win added to `{len(players)}` {player_text}: `{players_string}`.", ephemeral=True) 
        except Exception as e:
            print(f"Error{e} adding a win(s)")

    @app_commands.command(name="add_loss", description="Example Usecase: If captain scored for the wrong team, give loss to the actual losing team players")
    async def add_loss(
        self, 
        interaction: discord.Interaction, 
        player: discord.User,
        player2: discord.User = None,
        player3: discord.User = None,
        player4: discord.User = None,
        player5: discord.User = None,          
        ):

        discord_ids = [player.id]
        players = [player.display_name]

        for p in [player2, player3, player4, player5]:
            if p and p.id not in discord_ids:
                discord_ids.append(p.id)
                players.append(p.display_name)
        
        guild = self.bot.get_guild(Variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))

        captain_role = interaction.guild.get_role(roles.captain)

        if not captain_role in member.roles:
            await interaction.response.send_message("You do not have the required permissions to update losses.", ephemeral=True)
            return

        if player is None:
            await interaction.response.send_message("Player not found.", ephemeral=True)
            return
        
        try:
            placeholders = ', '.join('?'for _ in discord_ids)
            sql_add_a_loss = f"UPDATE `users` SET `losses` = `losses` + 1 WHERE `discord_id` IN ({placeholders})"
            params = (discord_ids)
            await self.db.execute_query(sql_add_a_loss, params)

            player_text = "players" if len(players) > 1 else "player"
            players_string = ', '.join(players)
            await interaction.response.send_message(f"Loss added to `{len(players)}` {player_text}: `{players_string}`.", ephemeral=True) 
        except Exception as e:
            print(f"Error{e} adding a win to player {player}.")

    @app_commands.command(name="substract_win", description="Example Usecase: If captain scored for the wrong team, take the wins back from the wrong team")
    async def substract_win(
        self, 
        interaction: discord.Interaction, 
        player: discord.User,
        player2: discord.User = None,
        player3: discord.User = None,
        player4: discord.User = None,
        player5: discord.User = None,          
        ):
        
        discord_ids = [player.id]
        players = [player.display_name]

        for p in [player2, player3, player4, player5]:
            if p and p.id not in discord_ids:
                discord_ids.append(p.id)
                players.append(p.display_name)
        
        guild = self.bot.get_guild(Variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))

        captain_role = interaction.guild.get_role(roles.captain)

        if captain_role not in member.roles:
            await interaction.response.send_message("You do not have the required permissions to update wins.", ephemeral=True)
            return

        if player is None:
            await interaction.response.send_message("Player not found.", ephemeral=True)
            return
        
        try:
            placeholders = ', '.join('?'for _ in discord_ids)
            sql_substract_a_win = f"UPDATE `users` SET `wins` = `wins` - 1 WHERE `discord_id` IN {placeholders}"
            params = (discord_ids)
            await self.db.execute_query(sql_substract_a_win, params)

            player_text = "players" if len(players) > 1 else "player"
            players_string = ', '.join(players)
            await interaction.response.send_message(f"Win substracted from `{len(players)}` {player_text}: `{players_string}`.", ephemeral=True) 
        except Exception as e:
            print(f"Error{e} substracting win(s)")

    @app_commands.command(name="substract_loss", description="Example Usecase: If captain scored a win for wrong team, take the losses back from the wrong team")
    async def add_loss(
        self, 
        interaction: discord.Interaction, 
        player: discord.User,
        player2: discord.User = None,
        player3: discord.User = None,
        player4: discord.User = None,
        player5: discord.User = None,          
        ):

        discord_ids = [player.id]
        players = [player.display_name]

        for p in [player2, player3, player4, player5]:
            if p and p.id not in discord_ids:
                discord_ids.append(p.id)
                players.append(p.display_name)
        
        guild = self.bot.get_guild(Variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))

        captain_role = interaction.guild.get_role(roles.captain)

        if not captain_role in member.roles:
            await interaction.response.send_message("You do not have the required permissions to update losses.", ephemeral=True)
            return

        if player is None:
            await interaction.response.send_message("Player not found.", ephemeral=True)
            return
        
        try:
            placeholders = ', '.join('?'for _ in discord_ids)
            sql_substract_a_loss = f"UPDATE `users` SET `losses` = `losses` - 1 WHERE `discord_id` IN ({placeholders})"
            params = (discord_ids)
            await self.db.execute_query(sql_substract_a_loss, params)

            player_text = "players" if len(players) > 1 else "player"
            players_string = ', '.join(players)
            await interaction.response.send_message(f"Loss substracted from `{len(players)}` {player_text}: `{players_string}`.", ephemeral=True) 
        except Exception as e:
            print(f"Error{e} substracting a win.")
                    
async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Statistics(bot),
        guilds = [discord.Object(id = Variables.guild_id )])     

