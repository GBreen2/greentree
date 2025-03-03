from flask import Flask, request, jsonify
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.json_format import MessageToJson
import binascii
import aiohttp
import json
import like_pb2
import like_count_pb2
import uid_generator_pb2
from google.protobuf.message import DecodeError
import os
from functools import lru_cache

app = Flask(__name__)

# কনফিগারেশন
CONFIG = {
    "TOKEN_FILES": {
        "IND": "token_ind.json",
        "BR": "token_br.json",
        "US": "token_br.json",
        "SAC": "token_br.json",
        "NA": "token_br.json",
        "default": "token_bd.json"
    },
    "API_URLS": {
        "IND": {
            "like": "https://client.ind.freefiremobile.com/LikeProfile",
            "info": "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        },
        "BR": {
            "like": "https://client.us.freefiremobile.com/LikeProfile",
            "info": "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
        },
        "default": {
            "like": "https://clientbp.ggblueshark.com/LikeProfile",
            "info": "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"
        }
    },
    "ENCRYPTION_KEY": os.getenv("ENCRYPTION_KEY", "Yg&tc%DEuh6%Zc^8").encode(),
    "ENCRYPTION_IV": os.getenv("ENCRYPTION_IV", "6oyZDr22E3ychjM%").encode()
}

# টোকেন লোড করার ফাংশন (ক্যাশিং সহ)
@lru_cache(maxsize=5)
def load_tokens(server_name):
    try:
        token_file = CONFIG["TOKEN_FILES"].get(server_name, CONFIG["TOKEN_FILES"]["default"])
        with open(token_file, "r") as f:
            return json.load(f)
    except Exception as e:
        app.logger.error(f"Error loading tokens for server {server_name}: {e}")
        return None

# এনক্রিপশন ফাংশন
def encrypt_message(plaintext):
    try:
        cipher = AES.new(CONFIG["ENCRYPTION_KEY"], AES.MODE_CBC, CONFIG["ENCRYPTION_IV"])
        padded_message = pad(plaintext, AES.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Error encrypting message: {e}")
        return None

# প্রোটোবাফ মেসেজ তৈরি করার ফাংশন
def create_protobuf_message(user_id, region):
    try:
        message = like_pb2.like()
        message.uid = int(user_id)
        message.region = region
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating protobuf message: {e}")
        return None

# UID প্রোটোবাফ তৈরি করার ফাংশন
def create_protobuf(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.saturn_ = int(uid)
        message.garena = 1
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating uid protobuf: {e}")
        return None

# UID এনক্রিপ্ট করার ফাংশন
def enc(uid):
    protobuf_data = create_protobuf(uid)
    if protobuf_data is None:
        return None
    return encrypt_message(protobuf_data)

# API রিকোয়েস্ট পাঠানোর ফাংশন
async def send_request(encrypted_uid, token, url):
    try:
        edata = bytes.fromhex(encrypted_uid)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB48"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=edata, headers=headers) as response:
                if response.status != 200:
                    app.logger.error(f"Request failed with status code: {response.status}")
                    return response.status
                return await response.text()
    except Exception as e:
        app.logger.error(f"Exception in send_request: {e}")
        return None

# একাধিক রিকোয়েস্ট পাঠানোর ফাংশন
async def send_multiple_requests(uid, server_name, url):
    try:
        region = server_name
        protobuf_message = create_protobuf_message(uid, region)
        if protobuf_message is None:
            app.logger.error("Failed to create protobuf message.")
            return None
        encrypted_uid = encrypt_message(protobuf_message)
        if encrypted_uid is None:
            app.logger.error("Encryption failed.")
            return None
        tokens = load_tokens(server_name)
        if tokens is None:
            app.logger.error("Failed to load tokens.")
            return None
        tasks = [send_request(encrypted_uid, tokens[i % len(tokens)]["token"], url) for i in range(100)]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    except Exception as e:
        app.logger.error(f"Exception in send_multiple_requests: {e}")
        return None

# প্রোটোবাফ ডিকোড করার ফাংশন
def decode_protobuf(binary):
    try:
        items = like_count_pb2.Info()
        items.ParseFromString(binary)
        return items
    except DecodeError as e:
        app.logger.error(f"Error decoding Protobuf data: {e}")
        return None
    except Exception as e:
        app.logger.error(f"Unexpected error during protobuf decoding: {e}")
        return None

# প্লেয়ার ইনফো রিকোয়েস্ট করার ফাংশন
async def make_request(encrypted_uid, server_name, token):
    try:
        url = CONFIG["API_URLS"].get(server_name, CONFIG["API_URLS"]["default"])["info"]
        edata = bytes.fromhex(encrypted_uid)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB48"
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(url, data=edata, headers=headers) as response:
                if response.status != 200:
                    app.logger.error(f"Request failed with status code: {response.status}")
                    return None
                binary = await response.read()
                return decode_protobuf(binary)
    except Exception as e:
        app.logger.error(f"Error in make_request: {e}")
        return None

# লাইক রিকোয়েস্ট হ্যান্ডলার
@app.route('/like', methods=['GET'])
async def handle_requests():
    uid = request.args.get("uid")
    server_name = request.args.get("server_name", "").upper()
    if not uid or not server_name:
        return jsonify({"error": "UID and server_name are required"}), 400

    try:
        tokens = load_tokens(server_name)
        if tokens is None:
            raise Exception("Failed to load tokens.")
        token = tokens[0]['token']
        encrypted_uid = enc(uid)
        if encrypted_uid is None:
            raise Exception("Encryption of UID failed.")

        # প্লেয়ার ইনফো প্রাপ্তি (লাইক করার আগে)
        before = await make_request(encrypted_uid, server_name, token)
        if before is None:
            raise Exception("Failed to retrieve initial player info.")
        data_before = json.loads(MessageToJson(before))
        before_like = int(data_before.get('AccountInfo', {}).get('Likes', 0))
        app.logger.info(f"Likes before command: {before_like}")

        # লাইক রিকোয়েস্ট URL
        url = CONFIG["API_URLS"].get(server_name, CONFIG["API_URLS"]["default"])["like"]

        # একাধিক লাইক রিকোয়েস্ট পাঠানো
        await send_multiple_requests(uid, server_name, url)

        # প্লেয়ার ইনফো প্রাপ্তি (লাইক করার পরে)
        after = await make_request(encrypted_uid, server_name, token)
        if after is None:
            raise Exception("Failed to retrieve player info after like requests.")
        data_after = json.loads(MessageToJson(after))
        after_like = int(data_after.get('AccountInfo', {}).get('Likes', 0))
        player_uid = int(data_after.get('AccountInfo', {}).get('UID', 0))
        player_name = str(data_after.get('AccountInfo', {}).get('PlayerNickname', ''))
        like_given = after_like - before_like
        status = 1 if like_given != 0 else 2

        result = {
            "LikesGivenByAPI": like_given,
            "LikesafterCommand": after_like,
            "LikesbeforeCommand": before_like,
            "PlayerNickname": player_name,
            "UID": player_uid,
            "status": status
        }
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
