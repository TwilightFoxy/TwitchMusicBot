import subprocess
import sys

# Список зависимостей
dependencies = [
    "twitchio",
    "pytube",
    "requests"
]

# Функция для установки зависимостей
def install_dependencies():
    for package in dependencies:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

# Установка зависимостей
install_dependencies()

# Остальной код бота
import json
import random
import asyncio
from twitchio.ext import commands
from collections import defaultdict
from pytube import YouTube

# Конфигурация Twitch можно получить на сайте https://twitchtokengenerator.com.
# Чтобы не париться просто выдайте все права (или только на чтение-отправку сообщений)
TWITCH_TOKEN = 'oauth:XXX' #ACCESS TOKEN
CLIENT_ID = 'XXX' #CLIENT ID
TWITCH_CHANNEL = 'XXX'#Название канала
STAT_FILE = 'stats.json'

with open('links.txt', 'r') as file: #В этот файл загрузить ссылки на ютуб музыку
    links = file.read().splitlines()
    total_tracks = len(links)


class Bot(commands.Bot):

    def __init__(self):
        super().__init__(token=TWITCH_TOKEN, prefix='!', initial_channels=[TWITCH_CHANNEL])
        self.track_requests = defaultdict(int)
        self.user_requests = defaultdict(int)
        self.load_stats()

    def load_stats(self):
        try:
            with open(STAT_FILE, 'r') as f:
                data = json.load(f)
                self.track_requests.update(data.get('track_requests', {}))
                self.user_requests.update(data.get('user_requests', {}))
        except FileNotFoundError:
            print("Stat file not found. Starting with empty stats.")

    def save_stats(self):
        with open(STAT_FILE, 'w') as f:
            json.dump({
                'track_requests': self.track_requests,
                'user_requests': self.user_requests
            }, f)

    async def event_ready(self):
        print(f'Logged in as {self.nick}')
        print(f'Connected to channel: {TWITCH_CHANNEL}')
        await self.get_channel(TWITCH_CHANNEL).send('Bot has connected!')

    async def event_message(self, message):
        if message.author is not None and message.content is not None:
            print(f'Received message: {message.content} from {message.author.name}')
            await self.handle_commands(message)

    async def sr(self, ctx):
        link = random.choice(links)
        print(f'Selected link: {link}')
        try:
            yt = YouTube(link)
            title = yt.title
            print(f'Video title: {title}')
            self.track_requests[title] += 1
            self.user_requests[ctx.author.name] += 1
            self.save_stats()
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
        print("Received command: статистика")
        top_tracks = sorted(self.track_requests.items(), key=lambda x: x[1], reverse=True)[:5]
        top_users = sorted(self.user_requests.items(), key=lambda x: x[1], reverse=True)[:5]
        unlocked_tracks = len([count for count in self.track_requests.values() if count > 0])

        top_tracks_msg = "Топ 5 треков: " + " | ".join([f"{track}: {count}" for track, count in top_tracks])
        top_users_msg = "Топ 5 пользователей: " + " | ".join([f"{user}: {count}" for user, count in top_users])
        unlocked_tracks_msg = f"Треков разблокировано: {unlocked_tracks} / {total_tracks}"

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
        print("Unlocked tracks sent to chat")

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
    print("Validating token...")
    validate_token(TWITCH_TOKEN.split('oauth:')[1])
    print("Starting bot...")
    bot = Bot()
    bot.run()
    print("Bot started")
