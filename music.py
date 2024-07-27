import json
import random
import asyncio
import sqlite3
import requests
import logging
from twitchio.ext import commands
from pytube import YouTube

# Настройка логирования для подавления ошибок в консоли
logging.basicConfig(level=logging.INFO)

# Конфигурация Twitch
TWITCH_TOKEN = 'oauth:XXX'
CLIENT_ID = 'XXX'
TWITCH_CHANNEL = 'XXX'
DATABASE_FILE = 'stats.db'

# Загрузка ссылок из файла
LINKS_FILE = 'links.txt'


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(token=TWITCH_TOKEN, prefix='!', initial_channels=[TWITCH_CHANNEL])
        self.database = None
        self.loop = asyncio.get_event_loop()

    def create_tables(self):
        with self.database:
            self.database.execute('''
                CREATE TABLE IF NOT EXISTS user_stats (
                    username TEXT PRIMARY KEY,
                    points INTEGER DEFAULT 0,
                    level INTEGER DEFAULT 1
                )
            ''')

            self.database.execute('''
                CREATE TABLE IF NOT EXISTS track_requests (
                    username TEXT,
                    track TEXT,
                    UNIQUE (username, track)
                )
            ''')

            self.database.execute('''
                CREATE TABLE IF NOT EXISTS tracks (
                    track TEXT PRIMARY KEY
                )
            ''')

    def load_stats(self):
        self.database = sqlite3.connect(DATABASE_FILE)
        self.create_tables()
        self.load_links()

    def load_links(self):
        with self.database:
            db_links = {row[0] for row in self.database.execute('SELECT track FROM tracks')}

        with open(LINKS_FILE, 'r') as file:
            file_links = {line.strip() for line in file.readlines()}

        new_links = file_links - db_links

        with self.database:
            self.database.executemany('INSERT OR IGNORE INTO tracks (track) VALUES (?)',
                                      [(link,) for link in new_links])

    def save_user_stats(self, user, points, level):
        with self.database:
            self.database.execute('''
                INSERT INTO user_stats (username, points, level)
                VALUES (?, ?, ?)
                ON CONFLICT(username) DO UPDATE SET
                    points=excluded.points,
                    level=excluded.level
            ''', (user, points, level))

    def save_track_request(self, user, track):
        with self.database:
            self.database.execute('''
                INSERT OR IGNORE INTO track_requests (username, track)
                VALUES (?, ?)
            ''', (user, track))

    def update_user_stats(self, user, track):
        with self.database:
            row = self.database.execute('SELECT points, level FROM user_stats WHERE username = ?', (user,)).fetchone()
            if row:
                points, level = row
            else:
                points, level = 0, 1

        points += 10
        if points >= level * 100:
            points -= level * 100
            level += 1

        self.save_user_stats(user, points, level)
        self.save_track_request(user, track)

    def get_user_stats(self, user):
        with self.database:
            return self.database.execute('SELECT points, level FROM user_stats WHERE username = ?', (user,)).fetchone()

    def get_user_tracks(self, user):
        with self.database:
            row = self.database.execute('SELECT COUNT(DISTINCT track) FROM track_requests WHERE username = ?',
                                        (user,)).fetchone()
            return row[0] if row else 0

    def get_top_tracks(self):
        with self.database:
            return self.database.execute(
                'SELECT track, COUNT(*) as count FROM track_requests GROUP BY track ORDER BY count DESC LIMIT 5').fetchall()

    def get_top_users(self):
        with self.database:
            return self.database.execute(
                'SELECT username, COUNT(*) as count FROM track_requests GROUP BY username ORDER BY count DESC LIMIT 5').fetchall()

    def get_total_tracks(self):
        with self.database:
            row = self.database.execute('SELECT COUNT(*) FROM tracks').fetchone()
            return row[0] if row else 0

    async def event_ready(self):
        print(f'Logged in as {self.nick}')
        print(f'Connected to channel: {TWITCH_CHANNEL}')
        await self.loop.run_in_executor(None, self.load_stats)
        await self.get_channel(TWITCH_CHANNEL).send('Bot has connected!')

    async def event_message(self, message):
        if message.author is not None and message.content is not None:
            print(f'Received message: {message.content} from {message.author.name}')
            await self.handle_commands(message)

    async def sr(self, ctx):
        row = await self.loop.run_in_executor(None, lambda: self.database.execute(
            'SELECT track FROM tracks ORDER BY RANDOM() LIMIT 1').fetchone())
        link = row[0] if row else None

        if not link:
            await ctx.send("No tracks available.")
            return

        print(f'Selected link: {link}')
        try:
            yt = YouTube(link)
            title = yt.title
            print(f'Video title: {title}')
            await self.loop.run_in_executor(None, self.update_user_stats, ctx.author.name, title)
            print("Attempting to send video title to chat...")
            await ctx.send(f'Название видео: {title}')
            print("Video title sent to chat")
            await asyncio.sleep(3)
            print("Attempting to send SR command to chat...")
            await ctx.send(f'!sr {link}')
            print("SR command sent to chat")
        except Exception as e:
            print(f'Error fetching video title: {str(e)}')
            await ctx.send(f'Не удалось получить название видео: {str(e)}')

    @commands.command(name='фоксимузыку')
    async def command_foksimuzyku(self, ctx):
        print("Received command: фоксимузыку")
        await self.sr(ctx)

    @commands.command(name='музыка')
    async def command_muzika(self, ctx):
        print("Received command: музыка")
        await self.sr(ctx)

    @commands.command(name='твайлижги')
    async def command_twilight(self, ctx):
        print("Received command: твайлижги")
        await self.sr(ctx)

    @commands.command(name='опенинг')
    async def command_opening(self, ctx):
        print("Received command: опенинг")
        await self.sr(ctx)

    @commands.command(name='статистика')
    async def command_stats(self, ctx):
        top_tracks = await self.loop.run_in_executor(None, self.get_top_tracks)
        top_users = await self.loop.run_in_executor(None, self.get_top_users)
        user_stats = await self.loop.run_in_executor(None, self.get_user_stats, ctx.author.name)
        user_unlocked_tracks = await self.loop.run_in_executor(None, self.get_user_tracks, ctx.author.name)
        total_tracks = await self.loop.run_in_executor(None, self.get_total_tracks)

        top_tracks_msg = "Топ 5 популярных треков: " + " | ".join([f"{track}: {count}" for track, count in top_tracks])
        top_users_msg = "Топ 5 активных пользователей: " + " | ".join([f"{user}: {count}" for user, count in top_users])
        unlocked_tracks_msg = f"Всего треков разблокировано: {user_unlocked_tracks} / {total_tracks}"
        user_unlocked_tracks_msg = f"{ctx.author.name} разблокировал: {user_unlocked_tracks} / {total_tracks}"

        await asyncio.sleep(3)
        print("Attempting to send top tracks to chat...")
        await ctx.send(top_tracks_msg)
        print("Top tracks sent to chat")
        await asyncio.sleep(3)
        print("Attempting to send top users to chat...")
        await ctx.send(top_users_msg)
        print("Top users sent to chat")
        await asyncio.sleep(3)
        print("Attempting to send unlocked tracks to chat...")
        await ctx.send(unlocked_tracks_msg)
        await asyncio.sleep(3)
        await ctx.send(user_unlocked_tracks_msg)
        print("Unlocked tracks sent to chat")

    @commands.command(name='уровень')
    async def command_level(self, ctx):
        user_stats = await self.loop.run_in_executor(None, self.get_user_stats, ctx.author.name)
        if user_stats:
            points, level = user_stats
            level_msg = f"{ctx.author.name}, ваш уровень: {level}, очки: {points}"
        else:
            level_msg = f"{ctx.author.name}, у вас пока нет очков и уровней."
        await ctx.send(level_msg)

    async def shutdown(self):
        await self.get_channel(TWITCH_CHANNEL).send('Bot has been stopped!')
        self.database.close()
        await self.close()


async def main():
    print("Validating token...")
    validate_token(TWITCH_TOKEN.split('oauth:')[1])
    print("Starting bot...")
    bot = Bot()

    try:
        await bot.start()
    except KeyboardInterrupt:
        await bot.shutdown()


def validate_token(token):
    headers = {
        'Authorization': f'OAuth {token}'
    }
    response = requests.get('https://id.twitch.tv/oauth2/validate', headers=headers)
    if response.status_code == 200:
        print("Token is valid")
        print(response.json())
    else:
        print("Token is invalid")
        print(response.status_code, response.text)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        logging.error(f"Error running the bot: {e}")

    print("Bot started")
