import discord
import asyncio
import roles
import variables
from game import GameManager
from db import connect_to_database 

class QueueManager:
    def __init__(self, bot, game_manager: GameManager):
        self.bot = bot
        self.queue_timers = []
        self.queue = []
        self.ban_timers = []
        self.game_manager = game_manager
        self.connection = connect_to_database()
    
    def set_ban_manager(self, ban_manager):
        self.ban_manager = ban_manager

    async def register(self, interaction):
        discord_id = interaction.user.id
        nick = interaction.user.display_name
        try:
            with self.connection.cursor() as cursor:
                sql_check = "SELECT * FROM `test` WHERE `discord_id` = %s"
                cursor.execute(sql_check, (discord_id,))
                result = cursor.fetchone()

                if result:
                    await interaction.response.send_message("You are already registered.", ephemeral=True)
                else:
                    sql_insert = "INSERT INTO `test` (`discord_id`, `wins`, `losses`, `elo`) VALUES (%s, 0, 0, 100)"
                    cursor.execute(sql_insert, (discord_id,))
                    self.connection.commit()

        except Exception as e:
            print(f"Error during registration: {e}")

        await interaction.followup.send("Registered.", ephemeral=True)
        await interaction.user.edit(nick=f"[100]{nick}")

    async def join_queue(self, interaction):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(2)

        player = interaction.user.id

        if player in self.ban_manager.ban_timers:
            await interaction.followup.send("You are temporarily banned from joining games.")
            return

        # checking if the user is registered in the database
        with self.connection.cursor() as cursor:
            sql_check = "SELECT * FROM `test` WHERE `discord_id` = %s"
            cursor.execute(sql_check, (player))
            result = cursor.fetchone()

        if await self.check_registration(interaction):
            return

        if interaction.user in self.queue:
            await interaction.followup.send("You are already in the queue", ephemeral=True)
            return

        self.queue.append(interaction.user)

        join_embed = discord.Embed(
            description=f"{interaction.user.mention} joined queue `[{len(self.queue)}/10]`",
            color=0xFFFF00
        )
        join_embed.set_footer(
            text="MF 5S",
            icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png"
        )

        await interaction.followup.send(embed=join_embed, ephemeral=False)

        if len(self.queue) == 10:
            # queue full, matchmaking starts
            asyncio.create_task(self.game_manager.create_game(self.queue.copy()))
            self.queue.clear()

    async def check_registration(self, interaction):
        player = interaction.user.id
        # Check if the user is registered in the database
        with self.connection.cursor() as cursor:
            sql_check = "SELECT * FROM `test` WHERE `discord_id` = %s"
            cursor.execute(sql_check, (player))
            result = cursor.fetchone()

            if not result:
                await interaction.followup.send(
                    "You need to register to be able to play. Use `/register` to register.",
                    ephemeral=True
                )
                return True # user not registered
            return False # registered
    async def leave_queue(self, interaction):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(2)

        if interaction.user not in self.queue:
            await interaction.followup.send("You are not in the queue.")
            return

        self.queue.remove(interaction.user)

        leave_embed = discord.Embed(
            description=f"{interaction.user.display_name} left the queue **`[{len(self.queue)}/10]`**",
            color=0xFFFF00
        )
        leave_embed.set_footer(
            text="MF 5S",
            icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png"
        )

        await interaction.followup.send(embed=leave_embed, ephemeral=False)

    async def clear_queue(self, interaction):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(2)
        guild = self.bot.get_guild(variables.guild_id)
        member = await interaction.guild.fetch_member(int(interaction.user.id))
        captain_role = interaction.guild.get_role(roles.captain)
        clear_queue_embed = discord.Embed(title="", description=f"{member.mention} used clear queue.", color=0xFFFF00)
        
        if captain_role in member.roles:
            if self.queue:
                self.queue.clear()
                await interaction.followup.send(embed=clear_queue_embed)
            else:  
                await interaction.followup.send("No ongoing queue.") 

    async def display_queue(self, interaction):
        await interaction.response.defer(ephemeral=False)
        await asyncio.sleep(2)

        if len(self.queue) == 0:
            await interaction.followup.send("Queue is empty.\n/join to start a new queue.")
            return

        queue_embed = discord.Embed(
            title="5 v 5 queue",
            description=f"`[{len(self.queue)}/10]`\n\n" + "\n".join(f":white_check_mark: {player.display_name}" for player in self.queue),
            color=0xFFFF00
        )

        queue_embed.set_footer(
            text="MF 5S",
            icon_url="https://cdn.discordapp.com/attachments/1199571571510104179/1201139545236840528/misfitspic.png"
        )

        await interaction.followup.send(embed=queue_embed)
