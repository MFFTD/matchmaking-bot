import discord
import asyncio
import uuid
import random
import roles
import variables
from typing import List
from db import connect_to_database 

game_dict = {}

class GameManager:
    def __init__(self, bot):
        self.bot = bot
        self.connection = connect_to_database()
        GameManager.PlayersDropdown.game_manager = GameManager

    async def create_game(self, queue_copy: List[discord.Member]):
        global game_dict
        guild = self.bot.get_guild(variables.guild_id)

        game_id = uuid.uuid4()
        game_dict[game_id] = {
            "game_id": game_id,
            "captains": [],
            "team_1_captain": [],
            "team_2_captain": [],
            "players": queue_copy,
            "team_one": [],
            "team_two": [],
            "picking_phase": 1,
        }
        #everybody with captain discord role to captains
        game_dict[game_id]['captains'] = [player for player in game_dict[game_id]['players'] if discord.utils.get(player.roles, name="Captain")]
        #if no captains, get players elos and make the two highest elo players captains
        if not game_dict[game_id]['captains']:
            discord_ids = [str(player.id) for player in game_dict[game_id]['players']]
            with self.connection.cursor() as cursor:
                sql_get_elo = f"SELECT `discord_id`, `elo` FROM `test` WHERE `discord_id` in ({', '.join('%s' for _ in discord_ids)})"
                cursor.execute(sql_get_elo, discord_ids)
                elo_results = cursor.fetchall()

            elo_mapping = {result['discord_id']: result['elo'] for result in elo_results}
            sorted_elo_mapping = dict(sorted(elo_mapping.items(), key=lambda item: item[1], reverse=True))

            captains = list(map(int, sorted_elo_mapping.keys()))[:2]
            while True:
                team_1_captain_id = captains[0]
                team_2_captain_id = captains[1]
                if team_1_captain_id != team_2_captain_id:
                    team_1_captain = await guild.fetch_member(team_1_captain_id)
                    team_2_captain = await guild.fetch_member(team_2_captain_id)

                    game_dict[game_id]['team_1_captain'].append(team_1_captain)
                    game_dict[game_id]['team_2_captain'].append(team_2_captain)
                    game_dict[game_id]['players'].remove(team_1_captain)
                    game_dict[game_id]['players'].remove(team_2_captain)
                    break
        # if only 1 player with captain role
        elif len(game_dict[game_id]['captains']) == 1:
            discord_ids = [str(player.id) for player in game_dict[game_id]['players']]
            with self.connection.cursor() as cursor:
                sql_get_elo = f"SELECT `discord_id`, `elo` FROM `test` WHERE `discord_id` in ({', '.join('%s' for _ in discord_ids)})"
                cursor.execute(sql_get_elo, discord_ids)
                elo_results = cursor.fetchall()

            elo_mapping = {result['discord_id']: result['elo'] for result in elo_results}
            sorted_elo_mapping = dict(sorted(elo_mapping.items(), key=lambda item: item[1], reverse=True))

            captains = list(map(int, sorted_elo_mapping.keys()))[:1]
            while True:
                team_1_captain = game_dict[game_id]['captains'][0]
                team_2_captain_id = captains[0]
                team_2_captain = await guild.fetch_member(team_2_captain_id)

                if team_1_captain != team_2_captain:
                    game_dict[game_id]['team_1_captain'].append(team_1_captain)
                    game_dict[game_id]['team_2_captain'].append(team_2_captain)
                    game_dict[game_id]['players'].remove(team_1_captain)
                    game_dict[game_id]['players'].remove(team_2_captain)
                    break
        # else lets pick 2 captains who has captain role
        else:
            while True:
                team_1_captain, team_2_captain = random.sample(game_dict[game_id]['captains'], 2)
                if team_1_captain != team_2_captain:
                    game_dict[game_id]['team_1_captain'].append(team_1_captain)
                    game_dict[game_id]['team_2_captain'].append(team_2_captain)
                    game_dict[game_id]['players'].remove(team_1_captain)
                    game_dict[game_id]['players'].remove(team_2_captain)
                    break

        players = game_dict[game_id]['players']
        game_embed = discord.Embed(
            title="**:hourglass:MATCHMAKING HAS STARTED**:hourglass_flowing_sand:",
            description=f"**Remaining players** {', '.join(str(player) for player in players)}",
            color=0xFFFF00
        )

        await asyncio.sleep(0)
        
        # 0 is picking phase
        players_dropdown = GameManager.PlayersDropdown(game_id, 0, self)


        players_view = GameManager.PlayersView(players_dropdown)

        
        matchmaking_channel = self.bot.get_channel(variables.matchmaking_channel_id)
        message = await matchmaking_channel.send(embed=game_embed, view=players_view)
        game_dict[game_id]['message_id'] = message.id

        await self.update_game_embed(game_id)

    async def update_game_embed(self, game_id):
        global game_dict
        interaction_channel = self.bot.get_channel(variables.matchmaking_channel_id)
        players = game_dict[game_id]['players']
        mention_players = (
            f"{game_dict[game_id]['team_1_captain'][0].mention}{''.join(str(player.mention) for player in game_dict[game_id]['team_one'])}"
            f"{game_dict[game_id]['team_2_captain'][0].mention}{''.join(str(player.mention) for player in game_dict[game_id]['team_two'])}"
            f"{''.join(str(player.mention) for player in players)}\n"
        )
        game_embed = discord.Embed(
            title="**:hourglass:MATCHMAKING HAS STARTED**:hourglass_flowing_sand:",
            description=(
                "\nPicking order\n 1-2-2-2-1"
                f"\n\n**Team 1**\nCaptain {game_dict[game_id]['team_1_captain'][0].mention}\n"
                + '\n'.join(str(player.mention) for player in game_dict[game_id]['team_one']) + "\n"
                f"**Team 2**\nCaptain {game_dict[game_id]['team_2_captain'][0].mention}\n"
                + '\n'.join(str(player.mention) for player in game_dict[game_id]['team_two']) + "\n"
                f"**Remaining players:**\n"
                + '\n'.join(str(player.mention) for player in players)
            ),
            color=0xFFFF00
        )
        game_embed.set_footer(
            text=f"MF 5S\nGame ID: {game_id}",
            icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png",
        )
        message_id = game_dict[game_id]['message_id']
        message = await interaction_channel.fetch_message(message_id)
        await message.edit(content=mention_players, embed=game_embed)


    class PlayersDropdown(discord.ui.Select):
        def __init__(self, game_id, picking_phase, game_manager):
            self.game_id = game_id
            self.picking_phase = picking_phase
            self.game_manager = game_manager
            self.end_game_view = game_manager.EndGameView(game_id, game_manager)


            team_number = 1 if picking_phase % 4 in (0, 3) else 2
            self.current_captain = game_dict[self.game_id][f'team_{team_number}_captain'][0] if game_dict[self.game_id][f'team_{team_number}_captain'] else None
            options = [discord.SelectOption(label=str(player.display_name), value=int(player.id)) for player in game_dict[self.game_id]['players']]
            super().__init__(placeholder=f"{self.current_captain.display_name} turn to pick", options=options, min_values=(1 if self.picking_phase < 1 else 2), max_values=(1 if self.picking_phase < 1 else 2))

        async def callback(self, interaction: discord.Interaction):
            await interaction.response.defer()

            for value in self.values:
                player_id = int(value)
                player = discord.utils.find(lambda p: p.id == player_id, game_dict[self.game_id]['players'])

                if interaction.user.id == self.current_captain.id:
                    if self.current_captain in game_dict[self.game_id]['team_1_captain']:
                        game_dict[self.game_id]['team_one'].append(player)
                    else:
                        game_dict[self.game_id]['team_two'].append(player)

                    game_dict[self.game_id]['players'].remove(player)
                    self.picking_phase += 1

                    # recreating options list so it does not contain the picked player
                    self.options = [opt for opt in self.options if int(opt.value) != player_id]

                    # one last remaining player to team 1
                    if len(game_dict[self.game_id]['players']) == 1:
                        remaining_player = game_dict[self.game_id]['players'][0]
                        if len(game_dict[self.game_id]['team_one']) < len(game_dict[self.game_id]['team_two']):
                            game_dict[self.game_id]['team_one'].append(remaining_player)
                        else:
                            game_dict[self.game_id]['team_two'].append(remaining_player)

                        game_dict[self.game_id]['players'].remove(remaining_player)

                    # updating the PlayersView dropdown
                    players_dropdown = GameManager.PlayersDropdown(self.game_id, self.picking_phase, self.game_manager)
                    players_view = GameManager.PlayersView(players_dropdown)

                    # hiding dropdown menu when there is only 1 option left
                    if len(self.options) >= 2:
                        await interaction.message.edit(view=players_view)
                    else:
                        await interaction.message.edit(view=None)

                    # updating game_embed with the updated player list
                    await self.game_manager.update_game_embed(self.game_id)
                else:
                    await interaction.followup.send("Error: Player not found or invalid pick.", ephemeral=True)
            # teams are made, send game_embed and mention the players.
            if len(game_dict[self.game_id]['players']) == 0:

                mention_players = (
                    f"{game_dict[self.game_id]['team_1_captain'][0].mention}{''.join(str(player.mention) for player in game_dict[self.game_id]['team_one'])}\n"
                    f"{game_dict[self.game_id]['team_2_captain'][0].mention}{''.join(str(player.mention) for player in game_dict[self.game_id]['team_two'])}"
                )

                game_start_embed = discord.Embed(
                    title="⚔️ **GAME HAS STARTED** ⚔️",
                    description=(
                        f"**Team 1**\nCaptain {game_dict[self.game_id]['team_1_captain'][0].mention}\n"
                        + '\n'.join(str(player.mention) for player in game_dict[self.game_id]['team_one']) + "\n\n"
                        f"**Team 2**\nCaptain {game_dict[self.game_id]['team_2_captain'][0].mention}\n"
                        + '\n'.join(str(player.mention) for player in game_dict[self.game_id]['team_two']) + "\n"
                    ),
                    color=0xFFFF00
                )
                game_start_embed.set_footer(text=f"MF 5S\nGame ID: {self.game_id}", icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png")

                end_game_view = self.end_game_view
                await interaction.followup.send(content=mention_players, embed=game_start_embed, view=end_game_view)

    # method to delete matchmaking incase it needs to be deleted.            
    async def delete_game(self, interaction, game_id):
        global game_dict
        guild = self.bot.get_guild(variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))

        captain_role = interaction.guild.get_role(roles.captain)

        if captain_role in member.roles:
            try:
                if game_id in game_dict:
                    del game_dict[game_id]
                    print(game_dict)
                    await interaction.response.send_message("Game deleted successfully!", ephemeral=True)
                else:
                    await interaction.response.send_message("No game found with the provided id.", ephemeral=True)
            except Exception as e:
                await interaction.response.send_message(f"Error during game removal: {e}", ephemeral=True)
        else:
            await interaction.response.send_message("You do not have the required role to delete a game.", ephemeral=True)
    
    class EndGameView(discord.ui.View):
        def __init__(self, game_id, game_manager):
            super().__init__(timeout=None)
            self.game_id = game_id
            self.game_manager = game_manager

        @discord.ui.button(label="Team 1 Won", custom_id="team_one", style=discord.ButtonStyle.green)
        async def team1(self, interaction: discord.Interaction, Button: discord.ui.Button):
            # only the captain of the team is allowed to decide if their team won.
            if interaction.user.id == game_dict[self.game_id]['team_1_captain'][0].id:
                team = 1
                await self.score(team, interaction)
            else:
                await interaction.response.send_message("You are not the captain of Team 1.", ephemeral=True)

        @discord.ui.button(label="Team 2 Won", custom_id="team_two", style=discord.ButtonStyle.green)
        async def team2(self, interaction: discord.Interaction, Button: discord.ui.Button):
            if interaction.user.id == game_dict[self.game_id]['team_2_captain'][0].id:
                team = 2
                await self.score(team, interaction)
            else:
                await interaction.response.send_message("You are not the captain of Team 2.", ephemeral=True)
        
        async def score(self, team, interaction: discord.Interaction):
            guild = self.game_manager.bot.get_guild(variables.guild_id)
            team_one_ids = [str(player.id) for player in game_dict[self.game_id]["team_one"]]
            team_two_ids = [str(player.id) for player in game_dict[self.game_id]["team_two"]]
            team_one_ids.append(str(game_dict[self.game_id]['team_1_captain'][0].id))
            team_two_ids.append(str(game_dict[self.game_id]['team_2_captain'][0].id))

            with self.game_manager.connection.cursor() as cursor:
                # fetching elos from db to get accurate elos incase someone did something related to elos during a game.
                sql_get_elo_team_one = "SELECT `discord_id`, `elo` FROM `test` WHERE `discord_id` IN ({})".format(
                    ", ".join("%s" for _ in team_one_ids)
                )
                cursor.execute(sql_get_elo_team_one, team_one_ids)
                results_team_one = cursor.fetchall()
                elo_team_one_mapping = {
                    result["discord_id"]: result["elo"] for result in results_team_one
                }

                sql_get_elo_team_two = "SELECT `discord_id`, `elo` FROM `test` WHERE `discord_id` IN ({})".format(
                    ", ".join("%s" for _ in team_two_ids)
                )
                cursor.execute(sql_get_elo_team_two, team_two_ids)
                results_team_two = cursor.fetchall()
                elo_team_two_mapping = {
                    result["discord_id"]: result["elo"] for result in results_team_two
                }
            # creating copy because we need the old elo to show them in game result embed
            old_elo_team_one =  elo_team_one_mapping.copy()
            old_elo_team_two = elo_team_two_mapping.copy()

            if team == 1:
                winning_team_ids = elo_team_one_mapping
                losing_team_ids = elo_team_two_mapping
            elif team == 2:
                winning_team_ids = elo_team_two_mapping
                losing_team_ids = elo_team_one_mapping

            # iterating trough winning team dict to check elos and give elo points and fetching discord member object to edit their server nickname with the new elo
            for discord_id, current_elo in winning_team_ids.items():
                member = await interaction.guild.fetch_member(int(discord_id))

                if current_elo < 100:
                    elo_gain = 30
                    winning_team_ids[discord_id] += elo_gain

                elif 100 <= current_elo < 200:
                    elo_gain = 29
                    winning_team_ids[discord_id] += elo_gain

                elif 200 <= current_elo < 300:
                    elo_gain = 28
                    winning_team_ids[discord_id] += elo_gain

                elif 300 <= current_elo < 400:
                    elo_gain = 27
                    winning_team_ids[discord_id] += elo_gain

                elif 400 <= current_elo < 500:
                    elo_gain = 26
                    winning_team_ids[discord_id] += elo_gain

                elif 500 <= current_elo < 600:
                    elo_gain = 25
                    winning_team_ids[discord_id] += elo_gain

                elif 600 <= current_elo < 700:
                    elo_gain = 24
                    winning_team_ids[discord_id] += elo_gain

                elif 700 <= current_elo < 800:
                    elo_gain = 23
                    winning_team_ids[discord_id] += elo_gain

                elif 800 <= current_elo < 900:
                    elo_gain = 22
                    winning_team_ids[discord_id] += elo_gain

                elif 900 <= current_elo < 1000:
                    elo_gain = 21
                    winning_team_ids[discord_id] += elo_gain

                elif 1000 <= current_elo < 1100:
                    elo_gain = 20
                    winning_team_ids[discord_id] += elo_gain

                elif 1100 <= current_elo < 1200:
                    elo_gain = 19
                    winning_team_ids[discord_id] += elo_gain

                elif 1200 <= current_elo < 1300:
                    elo_gain = 18
                    winning_team_ids[discord_id] += elo_gain

                elif current_elo >= 1300:
                    elo_gain = 17
                    winning_team_ids[discord_id] += elo_gain

                nick = member.display_name
                await member.edit(nick=f"[{winning_team_ids[discord_id]}]{nick.split(']')[1]}")

                        
            for discord_id, current_elo in losing_team_ids.items():
                if current_elo < 100:
                    if current_elo <= 17:
                        elo_loss = current_elo
                    else:
                        elo_loss = 17
                    losing_team_ids[discord_id] -= elo_loss
                elif 100 <= current_elo < 200:
                    elo_loss = 18
                    losing_team_ids[discord_id] -= elo_loss

                elif 200 <= current_elo < 300:
                    elo_loss = 19
                    losing_team_ids[discord_id] -= elo_loss

                elif 300 <= current_elo < 400:
                    elo_loss = 20
                    losing_team_ids[discord_id] -= elo_loss

                elif 400 <= current_elo < 500:
                    elo_loss = 21
                    losing_team_ids[discord_id] -= elo_loss

                elif 500 <= current_elo < 600:
                    elo_loss = 22
                    losing_team_ids[discord_id] -= elo_loss

                elif 600 <= current_elo < 700:
                    elo_loss = 23
                    losing_team_ids[discord_id] -= elo_loss

                elif 700 <= current_elo < 800:
                    elo_loss = 24
                    losing_team_ids[discord_id] -= elo_loss

                elif 800 <= current_elo < 900:
                    elo_loss = 25
                    losing_team_ids[discord_id] -= elo_loss

                elif 900 <= current_elo < 1000:
                    elo_loss = 26
                    losing_team_ids[discord_id] -= elo_loss

                elif 1000 <= current_elo < 1100:
                    elo_loss = 27
                    losing_team_ids[discord_id] -= elo_loss

                elif 1100 <= current_elo < 1200:
                    elo_loss = 28
                    losing_team_ids[discord_id] -= elo_loss

                elif 1200 <= current_elo < 1300:
                    elo_loss = 29
                    losing_team_ids[discord_id] -= elo_loss

                elif current_elo >= 1300:
                    elo_loss = 30
                    losing_team_ids[discord_id] -= elo_loss

                member = await interaction.guild.fetch_member(int(discord_id))
                nick = member.display_name
                await member.edit(nick=f"[{losing_team_ids[discord_id]}]{nick.split(']')[1]}")
                
            # need to check if any discord roles needs to be changed after elo gain / loss
            await self.update_roles(winning_team_ids, losing_team_ids)

            # updating new elo to db
            for discord_id, new_elo in winning_team_ids.items():
                with self.game_manager.connection.cursor() as cursor:
                    sql_update_winning_team = "UPDATE `test` SET `elo` = %s, `wins` = `wins` + 1 WHERE `discord_id` = %s"
                    cursor.execute(sql_update_winning_team, (new_elo, discord_id))

            for discord_id, new_elo in losing_team_ids.items():
                with self.game_manager.connection.cursor() as cursor:
                    sql_update_losing_team = "UPDATE `test` SET `elo` = %s, `losses` = `losses` + 1 WHERE `discord_id` = %s"
                    cursor.execute(sql_update_losing_team, (new_elo, discord_id))

            self.game_manager.connection.commit()

            # building discord embed description with the winner and loser team with their new elos 
            if team == 1:
                winners_description = f"Winners :trophy:\n"
                for discord_id, new_elo in winning_team_ids.items():
                    old_elo = elo_team_one_mapping.get(discord_id, 0)  
                    winners_description += f"<@{discord_id}>: {old_elo} → {new_elo}\n"

                losers_description = f"Losers :x:\n"
                for discord_id, new_elo in losing_team_ids.items():
                    old_elo = elo_team_two_mapping.get(discord_id, 0)  
                    losers_description += f"<@{discord_id}>: {old_elo} → {new_elo}\n"
            
            if team == 2:
                winners_description = f"Winners :trophy:\n"
                for discord_id, new_elo in winning_team_ids.items():
                    old_elo = old_elo_team_two.get(discord_id, 0)  
                    winners_description += f"<@{discord_id}>: {old_elo} → {new_elo}\n"

                losers_description = f"Losers :x:\n"
                for discord_id, new_elo in losing_team_ids.items():
                    old_elo = old_elo_team_one.get(discord_id, 0)  
                    losers_description += f"<@{discord_id}>: {old_elo} → {new_elo}\n"

            game_result_embed = discord.Embed(
                title="Game result",
                description=f"{winners_description}\n{losers_description}",
                color=0xFFFF00
            )
            
            game_result_embed.set_footer(text=f"MF 5S\nGame ID: {self.game_id}", icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png")

            result_channel = guild.get_channel(variables.result_channel_id)
            await result_channel.send(embed=game_result_embed)
            
            # removing the game after it is scored.
            try:
                if self.game_id in game_dict:
                    del game_dict[self.game_id]
            except Exception as e:
                print(f"Error during game removal: {e}")
            
        async def update_roles(self, winning_team_ids, losing_team_ids):
            guild = self.game_manager.bot.get_guild(variables.guild_id)
            teams_combined = {**winning_team_ids, **losing_team_ids}

            for discord_id, new_elo in teams_combined.items():
                member = await guild.fetch_member(int(discord_id))

                role_to_add_id = None
                role_to_remove_ids = []

                if 0 <= new_elo < 200:
                    role_to_add_id = roles.Apprentice
                    role_to_remove_ids = [roles.Warrior]

                elif 200 <= new_elo < 300:
                    role_to_add_id = roles.Warrior
                    role_to_remove_ids = [roles.Apprentice, roles.Vanguard]

                elif 300 <= new_elo < 400:
                    role_to_add_id = roles.Vanguard
                    role_to_remove_ids = [roles.Warrior, roles.Sentinel]

                elif 400 <= new_elo < 500:
                    role_to_add_id = roles.Sentinel
                    role_to_remove_ids = [roles.Vanguard, roles.Guardian]

                elif 500 <= new_elo < 600:
                    role_to_add_id = roles.Guardian
                    role_to_remove_ids = [roles.Sentinel, roles.Paladin]

                elif 600 <= new_elo < 700:
                    role_to_add_id = roles.Paladin
                    role_to_remove_ids = [roles.Guardian, roles.Champion]

                elif 700 <= new_elo < 800:
                    role_to_add_id = roles.Champion
                    role_to_remove_ids = [roles.Paladin, roles.Elite]

                elif 800 <= new_elo < 900:
                    role_to_add_id = roles.Elite
                    role_to_remove_ids = [roles.Champion, roles.Commander]

                elif 900 <= new_elo < 1000:
                    role_to_add_id = roles.Commander
                    role_to_remove_ids = [roles.Elite, roles.General]

                elif 1000 <= new_elo < 1100:
                    role_to_add_id = roles.General
                    role_to_remove_ids = [roles.General, roles.Warlord]

                elif 1100 <= new_elo < 1200:
                    role_to_add_id = roles.Warlord
                    role_to_remove_ids = [roles.General, roles.Legend]

                elif 1200 <= new_elo < 1300:
                    role_to_add_id = roles.Legend
                    role_to_remove_ids = [roles.Warlord, roles.Hero]

                elif 1300 <= new_elo < 1400:
                    role_to_add_id = roles.Hero
                    role_to_remove_ids = [roles.Legend, roles.Overlord]

                elif new_elo >= 1400:
                    role_to_add_id = roles.Overlord
                    role_to_remove_ids = [roles.Hero]

                if role_to_add_id:
                    role_to_add = guild.get_role(role_to_add_id)
                    if role_to_add not in member.roles:
                        await member.add_roles(role_to_add)

                for role_to_remove_id in role_to_remove_ids:
                    role_to_remove = guild.get_role(role_to_remove_id)
                    if role_to_remove in member.roles:
                        await member.remove_roles(role_to_remove)

    class PlayersView(discord.ui.View):
        def __init__(self, players_dropdown):
            super().__init__(timeout=None) 
            self.add_item(players_dropdown)

