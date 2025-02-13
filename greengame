import os
import requests
from telegram import Bot
from telegram.ext import Application, CommandHandler, MessageHandler, filters
import re
from fastapi import FastAPI
from starlette.requests import Request
import asyncio

# YouTube API Key and Telegram Bot API Token as environment variables
YOUTUBE_API_KEY = os.getenv('AIzaSyBLJlVmrVnTu4JYUwltLuqtji65EyxdP5s')
TELEGRAM_BOT_TOKEN = os.getenv('7652906604:AAG4JGjSy0TTMkr0V0xlSxGMi7aQtJA_2io')

# FastAPI instance for Vercel to handle HTTP requests
app = FastAPI()

# YouTube Data API Endpoint for Video Information
async def get_youtube_video_info(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        return "Invalid YouTube URL! Please provide a valid URL.", None

    video_api_url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={YOUTUBE_API_KEY}'
    response = requests.get(video_api_url)
    data = response.json()

    if 'items' in data and len(data['items']) > 0:
        video = data['items'][0]
        video_title = video['snippet']['title']
        video_description = video['snippet']['description']
        video_views = video['statistics'].get('viewCount', 'N/A')
        video_likes = video['statistics'].get('likeCount', 'N/A')
        video_comments = video['statistics'].get('commentCount', 'N/A')
        video_thumbnail = video['snippet']['thumbnails']['high']['url']

        video_info = (
            f"```\n\n"
            f"🚨 Just Send A YouTube Video Link 🚨\n\n"
            "———————————————\n"
            f"🪪 Video ID: {video_id}\n"
            "———————————————\n\n"
            f"🎬 Title: {video_title}\n\n"
            f"📊 Views: {video_views}\n\n"
            f"👍 Likes: {video_likes}\n\n"
            f"💬 Comments: {video_comments}\n\n"
            f"📝 Description: {video_description}\n\n"
            "———————————————\n"
            f"```"
        )
        return video_info, video_thumbnail
    else:
        return "Video information could not be retrieved. Please check the video URL.", None

# Function to extract video ID from the URL
def extract_video_id(url):
    video_id_regex = r'(?:https?://)?(?:www\.)?(?:youtube\.com/shorts/|youtube\.com/watch\?v=|youtu\.be/)([a-zA-Z0-9_-]+)'
    match = re.search(video_id_regex, url)
    return match.group(1) if match else None

# Function to handle the message from Telegram bot
async def handle_message(update, context):
    video_url = update.message.text
    video_info, video_thumbnail = await get_youtube_video_info(video_url)

    if video_thumbnail:
        await update.message.reply_text(video_info, parse_mode='Markdown')
        await update.message.reply_photo(photo=video_thumbnail)
    else:
        await update.message.reply_text(video_info, parse_mode='Markdown')
    
    # Delete the user's input message after processing
    await update.message.delete()

# Command to start the bot
async def start_command(update, context):
    user = update.effective_user
    await update.message.reply_text(
        f"```\n"
        f"👋 Hello, [{user.first_name}](tg://user?id={user.id})! \n\n"
        f"🙂 Welcome Our VoolPe Bot. I Can Fetch YouTube Video Stats For You. Just Send A YouTube Video Link.\n\n"
        f"☺️ Thank You For Use Our Bot.\n\n"
        f"```"
        f"🖥️ Power By: Md Rasel",
        parse_mode="Markdown"
    )

# Command to show help message
async def help_command(update, context):
    user = update.effective_user
    await update.message.reply_text(
        f"```\n"
        f"🕵️ Help Menu  \n\n"
        f"🔎 What Can I Do?\n"
        f" > Fetch YouTube Video Stats Including Video Title, Views, Likes, Comments & Description.\n\n"
        f"🙋 How to Use?\n"
        f" > Just Send A YouTube Video Link.\n\n"
        f"🗺️ Dear > [{user.first_name}](tg://user?id={user.id}), Have A Great Time With This Bot.\n\n"
        f"```"
        f"🖥️ Power By: Md Rasel",
        parse_mode="Markdown"
    )

# Function to set up the Telegram bot
def setup_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.run_polling()

# HTTP endpoint for Vercel
@app.get("/")
async def root(request: Request):
    return {"message": "Hello, welcome to the YouTube Stats Bot!"}

# Vercel entry point
@app.on_event("startup")
async def on_startup():
    # Run the bot in a background task when the app starts
    loop = asyncio.get_event_loop()
    loop.create_task(setup_bot())
