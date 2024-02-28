import aiosqlite
import asyncio

class AsyncSQLiteDB:
    def __init__(self, db_path='database.db'):
        self.db_path = db_path

    async def connect(self):
        try:
            connection = await aiosqlite.connect(self.db_path)
            return connection
        except aiosqlite.Error as e:
            print(f"Error connecting to the database: {e}")

    async def close(self, connection):
        try:
            if connection:
                await connection.close()
        except aiosqlite.Error as e:
            print(f"Error closing the database connection: {e}")

    async def execute_query(self, query, params=None, fetchall=False):
        connection = await self.connect()
        try:
            async with connection.cursor() as cursor:
                await cursor.execute(query, params)
                if fetchall:
                    return await cursor.fetchall()
                else:
                    await connection.commit()
        except aiosqlite.Error as e:
            print(f"Error executing query: {e}")
        finally:
            await self.close(connection)
