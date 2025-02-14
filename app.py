import os
import re
import httpx
from fastapi import FastAPI, Request
from telegram import Bot
from telegram.error import TelegramError
from telegram import Update
from telegram.ext import CommandHandler, MessageHandler, Filters, Application
import uvicorn

# YouTube API Key
YOUTUBE_API_KEY = os.getenv('AIzaSyBLJlVmrVnTu4JYUwltLuqtji65EyxdP5s')

# Telegram Bot API Token
TELEGRAM_BOT_TOKEN = os.getenv('7652906604:AAG4JGjSy0TTMkr0V0xlSxGMi7aQtJA_2io')

# FastAPI instance for Vercel to handle HTTP requests
app = FastAPI()

# YouTube Data API Endpoint for Video Information
async def get_youtube_video_info(video_url):
    video_id = extract_video_id(video_url)
    if not video_id:
        return "Invalid YouTube URL! Please provide a valid URL.", None

    video_api_url = f'https://www.googleapis.com/youtube/v3/videos?part=snippet,statistics&id={video_id}&key={YOUTUBE_API_KEY}'
    async with httpx.AsyncClient() as client:
        response = await client.get(video_api_url)
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

# Webhook endpoint for Vercel
@app.post("/webhook")
async def webhook(request: Request):
    data = await request.json()
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    
    # Extract user chat ID from incoming data
    chat_id = data.get('message', {}).get('chat', {}).get('id')
    if chat_id:
        video_url = data.get('message', {}).get('text')
        video_info, video_thumbnail = await get_youtube_video_info(video_url)

        try:
            if video_thumbnail:
                bot.send_message(chat_id=chat_id, text=video_info, parse_mode='Markdown')
                bot.send_photo(chat_id=chat_id, photo=video_thumbnail)
            else:
                bot.send_message(chat_id=chat_id, text=video_info, parse_mode='Markdown')
            
            # Delete the user's input message after processing
            bot.delete_message(chat_id=chat_id, message_id=data.get('message', {}).get('message_id'))

        except TelegramError as e:
            print(f"Error while sending message: {e}")
            return {"status": "error", "message": str(e)}

    return {"status": "ok"}

# Command to start the bot
async def start_command(update, context):
    user = update.effective_user
    await update.message.reply_text(
        f"```\n"
        f"👋 Hello, [{user.first_name}](tg://user?id={user.id})! \n\n"
        f"🙂 Welcome to our VoolPe Bot. I can fetch YouTube video stats for you. Just send a YouTube video link.\n\n"
        f"☺️ Thank you for using our bot.\n\n"
        f"```"
        f"🖥️ Power by: Md Rasel",
        parse_mode="Markdown"
    )

# Command to show help message
async def help_command(update, context):
    user = update.effective_user
    await update.message.reply_text(
        f"```\n"
        f"🕵️ Help Menu \n\n"
        f"🔎 What can I do?\n"
        f" > Fetch YouTube Video stats including video title, views, likes, comments & description.\n\n"
        f"🙋 How to use?\n"
        f" > Just send a YouTube video link.\n\n"
        f"🗺️ Dear [{user.first_name}](tg://user?id={user.id}), have a great time with this bot.\n\n"
        f"```"
        f"🖥️ Power by: Md Rasel",
        parse_mode="Markdown"
    )

# Function to set up the Telegram bot
def setup_bot():
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    application.add_handler(CommandHandler('start', start_command))
    application.add_handler(CommandHandler('help', help_command))
    application.add_handler(MessageHandler(Filters.TEXT & ~Filters.COMMAND, handle_message))
    application.run_polling()

# Vercel entry point
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
    
