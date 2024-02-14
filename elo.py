import discord
import asyncio
import roles
import variables
from db import connect_to_database 

class EloManager:
    def __init__(self, bot):
        self.bot = bot
        self.connection = connect_to_database()

    async def display_stats(self, interaction: discord.Interaction, player: discord.User = None):
        def calculate_wlr(wins, losses):

            if losses == 0:
                return wins
            else:
                return wins / losses

        if player:
            discord_id = player.id
            player_name = player.display_name
        else:
            discord_id = interaction.user.id
            player_name = interaction.user.display_name
        
        with self.connection.cursor() as cursor:
            sql_get_stats = "SELECT `elo`, `wins`, `losses` FROM `test` WHERE `discord_id` = %s"
            cursor.execute(sql_get_stats, (discord_id))
            result = cursor.fetchone()
        
        if result:
            elo = result["elo"]
            wins = result["wins"]
            losses = result["losses"]
            wlr = calculate_wlr(wins, losses)
            #these are to color text in embed
            ansi_wins = f"```ansi\n[2;31m[2;32m[1;32m{wins}[0m[2;32m[0m[2;31m[0m\n```"
            ansi_losses = f"```ansi\n[2;31m[1;31m{losses}[0m[2;31m[0m\n```"
            ansi_elo = f"```ansi\n[1;2m[1;33m{elo}[0m[0m\n```"
            ansi_wlr = f"```ansi\n[2;36m[1;36m{wlr:.2f}[0m[2;36m[0m\n```"
            
            stats_embed = discord.Embed(
                title=f"Stats for {player_name}",
                description=f"**Elo** {ansi_elo}\n**Wins** {ansi_wins}\n**Losses** {ansi_losses}\n**Win-Loss Ratio** {ansi_wlr}\n\n",
                color=0xFFFF00,
            )
            stats_embed.set_footer(text=f"Misfits5s", icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png")
            stats_embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/1007243398119436390/1202013799159431188/misfits.gif?ex=65cbe996&is=65b97496&hm=1397ca9f1d0b1c5afe32adeb2ad2b53fd8c35adc08fe371443a0543c202bcd62&")
            
            await interaction.response.send_message(embed=stats_embed, ephemeral=False)
        else:
            await interaction.response.send_message("Player is not registered.", ephemeral=True)
    
    async def serve_penalty(self, interaction: discord.Interaction, player: discord.User, reason: str):
        penalty = 90
        guild = self.bot.get_guild(variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))

        captain_role = interaction.guild.get_role(roles.captain)

        if captain_role in member.roles:
            if player:
                discord_id = player.id
            else:
                await interaction.response.send_message("Error serving a penalty for the user.", ephemeral=True)
                return  

            try:
                with self.connection.cursor() as cursor:
                    sql_get_elo = "SELECT `elo` FROM `test` WHERE `discord_id` = %s"
                    cursor.execute(sql_get_elo, (discord_id))
                    result = cursor.fetchone()

                    if result:
                        current_elo = result["elo"]
                        if current_elo <= penalty:
                            new_elo = 0
                        else:
                            new_elo = current_elo - penalty

                        sql_update_elo = "UPDATE `test` SET `elo` = %s WHERE `discord_id` = %s"
                        cursor.execute(sql_update_elo, (new_elo, discord_id))
                        self.connection.commit()

                        display_name = player.display_name.split(']')[1]
                        new_nick = f"[{new_elo}]{display_name}"
                        await player.edit(nick=new_nick)

                        penalty_log_channel = guild.get_channel(variables.penalty_log_id)

                        await penalty_log_channel.send(f"```Current elo[{current_elo}] - penalty[{penalty}]\n=New elo[{new_elo}]\n\nPenalty served for user {player.display_name} by {interaction.user.display_name}\n\nReason:\n{reason}```")

                        
                        await interaction.response.send_message("Penalty served successfully.", ephemeral=True)
                    else:
                        await interaction.response.send_message("Error serving a penalty for the user.", ephemeral=True)
            except Exception as e:
                print(f"An error occurred: {e}")
                await interaction.response.send_message("An error occurred while serving the penalty.", ephemeral=True)
        
    async def add_elo(self, interaction: discord.Interaction, player: discord.Member, amount: int):
        discord_id = player.id
        guild = self.bot.get_guild(variables.guild_id)    
        elo_add_log_channel = self.bot.get_channel(variables.elo_add_log_id) 
        # fetching discord user object so we can check it for their roles
        member = await interaction.guild.fetch_member(int(interaction.user.id))
        captain_role = interaction.guild.get_role(roles.captain)

        if amount < 0:
            await interaction.response.send_message("Amount must be a positive number.", ephemeral=True)
            return

        if captain_role in member.roles:
            try:
                if self.connection:
                    with self.connection.cursor() as cursor:
                        # need to fetch their current elo because we need it for editing the test display name
                        sql_get_elo = "SELECT `elo` FROM `test` WHERE `discord_id` = %s"
                        cursor.execute(sql_get_elo, (discord_id))
                        result = cursor.fetchone()

                        if result:
                            current_elo = result["elo"]

                        sql_update = "UPDATE test SET elo = elo + %s WHERE discord_id = %s"
                        cursor.execute(sql_update, (amount, discord_id))
                        self.connection.commit()

            except Exception as e:
                await interaction.response.send_message(f"Error adding elo: {e}", ephemeral=True)
            
            new_elo = current_elo + amount
            display_name = player.display_name.split(']')[1]
            new_nick = f"[{new_elo}]{display_name}"
            await player.edit(nick=new_nick)
            await interaction.response.send_message("Elo added successfully.", ephemeral=True)
            await elo_add_log_channel.send(f"{amount} Elo added to player {player} by {interaction.user.display_name}")

    async def subtract_elo(self, interaction: discord.Interaction, player: discord.User, amount: int, reason: str):
        guild = self.bot.get_guild(variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))
        captain_role = interaction.guild.get_role(roles.captain)

        if captain_role in member.roles:
            # checking if player still exists
            if player:
                discord_id = player.id
            else:
                await interaction.response.send_message("Error serving a penalty for the user.", ephemeral=True)
                return

            try:
                with self.connection.cursor() as cursor:
                    sql_get_elo = "SELECT `elo` FROM `test` WHERE `discord_id` = %s"
                    cursor.execute(sql_get_elo, (discord_id))
                    result = cursor.fetchone()

                    if result:
                        current_elo = result["elo"]
                        # amount is what the user gave as a param
                        if current_elo <= amount:
                            new_elo = 0
                        else:
                            new_elo = current_elo - amount

                        sql_update_elo = "UPDATE `test` SET `elo` = %s WHERE `discord_id` = %s"
                        cursor.execute(sql_update_elo, (new_elo, discord_id))
                        self.connection.commit()

                        display_name = player.display_name.split(']')[1]
                        new_nick = f"[{new_elo}]{display_name}"
                        await player.edit(nick=new_nick)

                        penalty_log_channel = guild.get_channel(variables.penalty_log_id)
                        await penalty_log_channel.send(f"```Current elo[{current_elo}] - penalty[{penalty}]\n=New elo[{new_elo}]\n\nPenalty served for user {player.display_name} by {interaction.user.display_name}\n\nReason:\n{reason}```")
                        
                        await interaction.response.send_message("Penalty served successfully.", ephemeral=True)
                    else:
                        await interaction.response.send_message("Error serving a penalty for the user.", ephemeral=True)
            except Exception as e:
                print(f"An error occurred: {e}")
                await interaction.response.send_message("An error occurred while serving the penalty.", ephemeral=True)
