from flask import Flask, request, jsonify
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
import binascii
import aiohttp
import json
import like_pb2
import like_count_pb2
import uid_generator_pb2
from google.protobuf.message import DecodeError

app = Flask(__name__)

# Token লোড করার ফাংশন
def load_tokens(server_name):
    try:
        if server_name == "IND":
            with open("token_ind.json", "r") as f:
                tokens = json.load(f)
        elif server_name in {"BR", "US", "SAC", "NA"}:
            with open("token_br.json", "r") as f:
                tokens = json.load(f)
        else:
            with open("token_bd.json", "r") as f:
                tokens = json.load(f)
        return tokens
    except Exception as e:
        app.logger.error(f"Error loading tokens for server {server_name}: {e}")
        return None

# Message এনক্রিপশন ফাংশন
def encrypt_message(uid):
    try:
        # Encrypted key and iv setup
        key = b'Yg&tc%DEuh6%Zc^8'  # 16 bytes key
        iv = b'6oyZDr22E3ychjM%'  # 16 bytes IV
        
        # Ensure that the UID is a string and then encode it to bytes
        uid_bytes = str(uid).encode('utf-8')
        
        # Pad the message to make sure it's a multiple of AES block size (16 bytes)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(uid_bytes, AES.block_size)
        
        # Encrypt the padded message
        encrypted_message = cipher.encrypt(padded_message)
        
        # Return the encrypted message as a hex string
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Error encrypting message: {e}")
        return None

# Protobuf Message তৈরি
def create_protobuf_message(user_id, region):
    try:
        message = like_pb2.like()
        message.uid = int(user_id)
        message.region = region
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating protobuf message: {e}")
        return None

# Asynchronous HTTP Request পাঠানোর ফাংশন
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
            'ReleaseVersion': "OB47"
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

# Flask রুট
@app.route('/like', methods=['GET'])
def handle_requests():
    uid = request.args.get("uid")
    server_name = request.args.get("server_name", "").upper()
    if not uid or not server_name:
        return jsonify({"error": "UID and server_name are required"}), 400

    try:
        def process_request():
            tokens = load_tokens(server_name)
            if tokens is None:
                raise Exception("Failed to load tokens.")
            token = tokens[0]['token']
            encrypted_uid = encrypt_message(uid)
            if encrypted_uid is None:
                raise Exception("Encryption of UID failed.")

            # Pre-like Data
            before = make_request(encrypted_uid, server_name, token)
            if before is None:
                raise Exception("Failed to retrieve initial player info.")
            before_like = int(before.get('AccountInfo', {}).get('Likes', 0))

            # Like Command
            if server_name == "IND":
                url = "https://client.ind.freefiremobile.com/LikeProfile"
            else:
                url = "https://client.us.freefiremobile.com/LikeProfile"

            # Send asynchronous requests to simulate likes
            asyncio.run(send_request(encrypted_uid, token, url))

            # Post-like Data
            after = make_request(encrypted_uid, server_name, token)
            if after is None:
                raise Exception("Failed to retrieve player info after like requests.")
            after_like = int(after.get('AccountInfo', {}).get('Likes', 0))

            like_given = after_like - before_like
            status = 1 if like_given != 0 else 2
            result = {
                "LikesGivenByAPI": like_given,
                "LikesafterCommand": after_like,
                "LikesbeforeCommand": before_like,
                "status": status
            }
            return result

        result = process_request()
        return jsonify(result)
    except Exception as e:
        app.logger.error(f"Error processing request: {e}")
        return jsonify({"error": str(e)}), 500

# Player info রিকোয়েস্ট করার জন্য ফাংশন
def make_request(encrypt, server_name, token):
    try:
        if server_name == "IND":
            url = "https://client.ind.freefiremobile.com/GetPlayerPersonalShow"
        elif server_name in {"BR", "US", "SAC", "NA"}:
            url = "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
        else:
            url = "https://clientbp.ggblueshark.com/GetPlayerPersonalShow"
        edata = bytes.fromhex(encrypt)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 9; ASUS_Z01QD Build/PI)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2018.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB47"
        }
        response = requests.post(url, data=edata, headers=headers, verify=False)
        hex_data = response.content.hex()
        binary = bytes.fromhex(hex_data)
        decode = decode_protobuf(binary)
        if decode is None:
            app.logger.error("Protobuf decoding returned None.")
        return decode
    except Exception as e:
        app.logger.error(f"Error in make_request: {e}")
        return None

# Protobuf ডিকোড করার ফাংশন
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

if __name__ == '__main__':
    app.run(debug=True, use_reloader=False)
