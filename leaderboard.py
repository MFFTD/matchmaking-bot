import discord
from discord.ui import View
import pymysql.cursors
from db import connect_to_database 

class Pagination(View):
    def __init__(self, interaction: discord.Interaction, get_page):
        self.interaction = interaction
        self.get_page = get_page
        self.total_pages = None
        self.index = 1
        self.connection = connect_to_database()
        super().__init__(timeout=None)

    async def navigate(self):
        emb, self.total_pages = await self.get_page(self.index)
        if self.total_pages == 1:
            await self.interaction.response.send_message(embed=emb)
        elif self.total_pages > 1:
            self.update_buttons()
            await self.interaction.response.send_message(embed=emb, view=self)

    async def edit_page(self, interaction: discord.Interaction):
        emb, self.total_pages = await self.get_page(self.index)
        self.update_buttons()
        await interaction.response.edit_message(embed=emb, view=self)

    def update_buttons(self):
        if self.index > self.total_pages // 2:
            self.children[2].emoji = "⏮️"
        else:
            self.children[2].emoji = "⏭️"
        self.children[0].disabled = self.index == 1
        self.children[1].disabled = self.index == self.total_pages

    @discord.ui.button(emoji="◀️", style=discord.ButtonStyle.blurple)
    async def previous(self, interaction: discord.Interaction, button: discord.Button):
        self.index -= 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="▶️", style=discord.ButtonStyle.blurple)
    async def next(self, interaction: discord.Interaction, button: discord.Button):
        self.index += 1
        await self.edit_page(interaction)

    @discord.ui.button(emoji="⏭️", style=discord.ButtonStyle.blurple)
    async def end(self, interaction: discord.Interaction, button: discord.Button):
        if self.index <= self.total_pages // 2:
            self.index = self.total_pages
        else:
            self.index = 1
        await self.edit_page(interaction)

    async def on_timeout(self):
        # remove buttons on timeout
        message = await self.interaction.original_response()
        await message.edit(view=None)

    @staticmethod
    def compute_total_pages(total_results: int, results_per_page: int) -> int:
        return ((total_results - 1) // results_per_page) + 1


class EloLeaderboard:
    def __init__(self, bot):
        self.bot = bot
        self.connection = connect_to_database()

    async def lb(self, interaction):
        async def get_page(page):
            cursor = self.connection.cursor()
            cursor.execute("SELECT discord_id, elo FROM users ORDER BY elo DESC")
            results = cursor.fetchall()
            cursor.close()

            emb = discord.Embed(title=f"Leaderboard - Page {page}", color=0xFFFF00)
            chunk_size = 10
            offset = (page - 1) * chunk_size
            for user in results[offset:offset + chunk_size]:
                emb.add_field(name="", value=f"<@{user['discord_id']}> Elo `{user['elo']}`", inline=False)



            n = Pagination.compute_total_pages(len(results), chunk_size)
            emb.set_footer(text=f"Page {page} from {n}")
            return emb, n

        pagination_view = Pagination(interaction, get_page)
        await pagination_view.navigate()
