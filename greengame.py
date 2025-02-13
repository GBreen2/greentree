import os
import requests
from fastapi import FastAPI, Request
import re
from telegram import Bot
import uvicorn

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

        if video_thumbnail:
            bot.send_message(chat_id=chat_id, text=video_info, parse_mode='Markdown')
            bot.send_photo(chat_id=chat_id, photo=video_thumbnail)
        else:
            bot.send_message(chat_id=chat_id, text=video_info, parse_mode='Markdown')

    return {"status": "ok"}

# HTTP endpoint for Vercel
@app.get("/")
async def root(request: Request):
    return {"message": "Hello, welcome to the YouTube Stats Bot!"}

# Vercel entry point
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.getenv("PORT", 8080)))
