# q.py
import discord
import asyncio
from discord import app_commands
from discord.ext import commands
from managers.game import GameManager
from variables import BotVariables as Variables
import roles
class Queue(commands.Cog, Variables):
    def __init__(self, bot: commands.Bot) -> None:
        self.bot = bot
        self.queue_timers = []
        self.queue = []
        self.game_manager = GameManager(bot)

    class FivesQueueButtons(discord.ui.View):
        def __init__(self, cog, bot: commands.Bot):
            super().__init__(timeout=None)
            self.cog = cog
            self.bot = bot
            self.game_manager = GameManager(bot)

        @discord.ui.button(label="Join", custom_id="join", style=discord.ButtonStyle.green)
        async def join_fives_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
            await asyncio.sleep(1)

            # checking if user still exists in game_dict dictionary. Previous game should be scored and result posted before joining a new game.
            if self.game_manager.game_dict:
                for game_id, game_data in self.game_manager.game_dict.items():
                    keys_to_check = ['players', 'team_one', 'team_two', 'team_1_captain', 'team_2_captain']

                    for key in keys_to_check:
                        if key in game_data:
                            if interaction.user.id in [player.id for player in game_data[key]]:
                                result_channel = self.bot.get_channel(Variables.result_channel_id)
                                await interaction.response.send_message(f"Please wait for the current game to be scored and for the result to be sent in {result_channel.mention} channel before creating a new queue.\nThis may take a minute.", ephemeral=True)
                                return
                        else:
                            pass

            ban_manager_instance = self.bot.get_cog("BanManager")
            register_instance = self.bot.get_cog("Register")

            await interaction.response.defer()

            is_registered = await register_instance.check_registration(interaction.user.id)

            if not is_registered:
                await interaction.followup.send("You need to register in order to join queues. Use `/register`.", ephemeral=True)
                return

            if interaction.user.id in ban_manager_instance.ban_timers:
                await interaction.followup.send("You are temporarily banned from joining games.", ephemeral=True)
                return

            if len(self.cog.queue) >= 10:
                return

            if interaction.user not in self.cog.queue:
                self.cog.queue.append(interaction.user)

                await self.cog.update_queue_message()

                queue_fives_channel = self.bot.get_channel(Variables.queue_fives_channel_id)
                lobby_channel = self.bot.get_channel(Variables.lobby_channel_id)

                await asyncio.sleep(1)

                join_embed = discord.Embed(
                    description = f"{interaction.user.mention} joined queue in {queue_fives_channel.mention}.",
                    color=0xFFFF00,
                )

                await lobby_channel.send(embed=join_embed)

        @discord.ui.button(label="Leave", custom_id="leave", style=discord.ButtonStyle.red)
        async def leave_fives_queue(self, interaction: discord.Interaction, button: discord.ui.Button):
            await asyncio.sleep(1)
            await interaction.response.defer()

            if interaction.user in self.cog.queue:
                self.cog.queue.remove(interaction.user)
                await self.cog.update_queue_message()


                queue_fives_channel = self.bot.get_channel(Variables.queue_fives_channel_id)
                lobby_channel = self.bot.get_channel(Variables.lobby_channel_id)

                await asyncio.sleep(1)

                leave_embed = discord.Embed(
                    description = f"{interaction.user.mention} left the queue in {queue_fives_channel.mention}.",
                    color=0xFFFF00,
                )

                await lobby_channel.send(embed=leave_embed)

    @app_commands.command(name="create_queue", description="Create a new queue")
    async def create_queue(self, interaction: discord.Interaction):

        # checking if user still exists in game_dict dictionary. Previous game should be scored and result posted before creating a new game.
        if self.game_manager.game_dict:
            for game_id, game_data in self.game_manager.game_dict.items():
                keys_to_check = ['players', 'team_one', 'team_two', 'team_1_captain', 'team_2_captain']

                for key in keys_to_check:
                    if key in game_data:
                        if interaction.user.id in [player.id for player in game_data[key]]:
                            result_channel = self.bot.get_channel(Variables.result_channel_id)
                            await interaction.response.send_message(f"Please wait for the current game to be scored and for the result to be sent in {result_channel.mention} channel before creating a new queue.\nThis may take a minute.", ephemeral=True)
                            return
                    else:
                        pass

        queue_fives_channel = self.bot.get_channel(Variables.queue_fives_channel_id)

        register_instance = self.bot.get_cog("Register")
        ban_manager_instance = self.bot.get_cog("BanManager")

        is_registered = await register_instance.check_registration(interaction.user.id)
        if not is_registered:
            await interaction.response.send_message("You need to register in order to join queues. Use `/register`.", ephemeral=True)
            return

        if interaction.user.id in ban_manager_instance.ban_timers:
            await interaction.response.send_message("Restricted from creating queues whilist ban persists.", ephemeral=True)
            return

        if self.queue:
            await interaction.response.send_message(f"There is an ongoing queue in {queue_fives_channel.mention}", ephemeral=True)
            return

        self.queue.append(interaction.user)

        fives_embed = discord.Embed(
            title="5 v 5 queue",
            description=f"`[{len(self.queue)}/10]`\n\n" + "\n".join(f":white_check_mark: {player.mention}" for player in self.queue),
            color=0xFFFF00
        )

        fives_embed.set_footer(
            text="MF 5S",
            icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png"
        )

        fives_queue_buttons = self.FivesQueueButtons(self, self.bot)

        #queue_fives_channel = self.bot.get_channel(Variables.queue_fives_channel_id)
        initial_message = await queue_fives_channel.send(embed=fives_embed, view=fives_queue_buttons)

        self.queue_message_id = initial_message.id

        new_fives_notify = discord.Embed(
            title="",
            description=f"New queue created by {interaction.user.mention} in {queue_fives_channel.mention}",
            color=0xFFFF00
        )

        await interaction.response.send_message(embed=new_fives_notify)

    async def update_queue_message(self):

        queue_fives_channel = self.bot.get_channel(Variables.queue_fives_channel_id)

        await asyncio.sleep(1)

        initial_message = await queue_fives_channel.fetch_message(self.queue_message_id)

        if not initial_message:
            return

        if not self.queue:
            await initial_message.delete()
            return

        fives_embed = discord.Embed(
            title="5 v 5 queue",
            description=f"`[{len(self.queue)}/10]`\n\n" + "\n".join(f":white_check_mark: {player.mention}" for player in self.queue),
            color=0xFFFF00
        )

        fives_embed.set_footer(
            text="MF 5S",
            icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png"
        )

        fives_queue_buttons = self.FivesQueueButtons(self, self.bot)

        # disable buttons and execute create_game method
        if len(self.queue) == 10:
            join_button = fives_queue_buttons.children[0]
            if join_button:
                await asyncio.sleep(1)
                join_button.disabled = True

            leave_button = fives_queue_buttons.children[1]
            if leave_button:
                await asyncio.sleep(1)
                leave_button.disabled = True

            await self.game_manager.create_game(self.queue.copy())
            self.queue.clear()

        await initial_message.edit(embed=fives_embed, view=fives_queue_buttons)


    @app_commands.command(name="clear_queue", description="Clear an ongoing queue")
    async def clear_queue(self, interaction: discord.Interaction):

        guild = self.bot.get_guild(Variables.guild_id)
        member = await interaction.guild.fetch_member(interaction.user.id)
        captain_role = interaction.guild.get_role(roles.captain)

        clear_queue_embed = discord.Embed(
            title="",
            description=f"{member.mention} used clear queue.",
            color=0xFFFF00
        )

        if captain_role not in member.roles:
            await interaction.response.send_message("You do not have the required permissions to clear the queue.", ephemeral=True)
            return

        if self.queue:
            self.queue.clear()
            queue_fives_channel = self.bot.get_channel(Variables.queue_fives_channel_id)
            initial_message = await queue_fives_channel.fetch_message(self.queue_message_id)
            await initial_message.delete()
            await interaction.response.send_message(embed=clear_queue_embed)
        else:
            await interaction.response.send_message("No ongoing queue.")

    @app_commands.command(name="queue", description="Display current players in the queue")
    async def display_queue(self, interaction: discord.Interaction):

        if not self.queue:
            await interaction.response.send_message("Queue is empty.\nUse `/create_queue` to start a new queue.")
            return

        queue_embed = discord.Embed(
            title="5 v 5 queue",
            description=f"`[{len(self.queue)}/10]`\n\n" + "\n".join(f":white_check_mark: {player.mention}" for player in self.queue),
            color=0xFFFF00
        )

        queue_embed.set_footer(
            text="MF 5S",
            icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png"
        )

        await interaction.response.send_message(embed=queue_embed)

    @app_commands.command(name="remove_afk_player", description="Queue: Remove player. Remove an afk player from the current queue.")
    async def remove_player_from_queue(self, interaction: discord.Interaction, player: discord.User):

        guild = self.bot.get_guild(Variables.guild_id)
        member = await interaction.guild.fetch_member(interaction.user.id)
        captain_role = interaction.guild.get_role(roles.captain)

        if captain_role not in member.roles:
            await interaction.response.send_message("You do not have the required permissions to remove players from queues.", ephemeral=True)
            return

        if not self.queue:
            await interaction.response.send_message("No ongoing queue.", ephemeral=True)
            return

        if player not in self.queue:
            await interaction.response.send_message("Player not in queue.", ephemeral=True)
            return

        if member == player:
            await interaction.response.send_message("Use the Leave button to remove yourself from queue.", ephemeral=True)
            return

        if player:
            self.queue.remove(player)
            asyncio.ensure_future(self.update_queue_message())
            await interaction.response.send_message(f"{player} removed from queue")
        else:
            await interaction.response.send_message("Looks like the player has left the server. If that is the case, suggesting to remove the queue and start a new one.", ephemeral=True)

async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(
        Queue(bot),
        guilds = [discord.Object(id = Variables.guild_id )])
