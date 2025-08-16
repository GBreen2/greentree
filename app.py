import urllib3
import requests
from flask import Flask, request, jsonify
import json
import binascii
import asyncio
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad
from google.protobuf.message import DecodeError
from google.protobuf.json_format import MessageToJson
import like_pb2
import like_count_pb2
import uid_generator_pb2

# Disable SSL verification warning
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

# Load tokens based on server name
def load_tokens(server_name):
    try:
        if server_name == "ME":
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

# Encrypt message using AES
def encrypt_message(plaintext):
    try:
        key = b'Yg&tc%DEuh6%Zc^8'
        iv = b'6oyZDr22E3ychjM%'
        cipher = AES.new(key, AES.MODE_CBC, iv)
        padded_message = pad(plaintext, AES.block_size)
        encrypted_message = cipher.encrypt(padded_message)
        return binascii.hexlify(encrypted_message).decode('utf-8')
    except Exception as e:
        app.logger.error(f"Error encrypting message: {e}")
        return None

# Create protobuf message for like request
def create_protobuf(uid, region):
    try:
        message = like_pb2.like()
        message.uid = int(uid)
        message.region = region
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating protobuf message: {e}")
        return None

# Send an asynchronous HTTP request
async def send_request(encrypted_uid, token, url):
    try:
        edata = bytes.fromhex(encrypted_uid)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 10; ASUS_Z01QD Build/Release)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2019.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB50"
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

# Send multiple requests with multiple tokens
async def send_multiple_requests(uid, server_name, url, total_requests=100):
    try:
        region = server_name
        protobuf_message = create_protobuf(uid, region)
        if protobuf_message is None:
            return None
        encrypted_uid = encrypt_message(protobuf_message)
        if encrypted_uid is None:
            return None
        tokens = load_tokens(server_name)
        if tokens is None:
            return None

        tasks = []
        for i in range(total_requests):
            token = tokens[i % len(tokens)]["token"]
            tasks.append(send_request(encrypted_uid, token, url))
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results
    except Exception as e:
        app.logger.error(f"Exception in send_multiple_requests: {e}")
        return None

# Create UID protobuf message
def create_uid_protobuf(uid):
    try:
        message = uid_generator_pb2.uid_generator()
        message.saturn_ = int(uid)
        message.garena = 1  # Make sure this field exists in your .proto file
        return message.SerializeToString()
    except Exception as e:
        app.logger.error(f"Error creating uid protobuf: {e}")
        return None

# Encrypt UID protobuf message
def encrypt_uid(uid):
    protobuf_data = create_uid_protobuf(uid)
    if protobuf_data is None:
        return None
    return encrypt_message(protobuf_data)

# Make the HTTP request to the game server
def make_request(encrypted_uid, server_name, token):
    try:
        url_map = {
            "ME": "https://clientbp.ggblueshark.com/GetPlayerPersonalShow",
            "BR": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
            "US": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
            "SAC": "https://client.us.freefiremobile.com/GetPlayerPersonalShow",
            "NA": "https://client.us.freefiremobile.com/GetPlayerPersonalShow"
        }
        url = url_map.get(server_name, "https://clientbp.ggblueshark.com/GetPlayerPersonalShow")
        edata = bytes.fromhex(encrypted_uid)
        headers = {
            'User-Agent': "Dalvik/2.1.0 (Linux; U; Android 10; ASUS_Z01QD Build/Release)",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/x-www-form-urlencoded",
            'Expect': "100-continue",
            'X-Unity-Version': "2019.4.11f1",
            'X-GA': "v1 1",
            'ReleaseVersion': "OB50"
        }
        response = requests.post(url, data=edata, headers=headers, verify=False)

        # Check if response is incomplete
        if len(response.content) < 50:
            app.logger.error(f"Incomplete response received: {response.content}")
            return None
        
        return decode_protobuf(response.content.hex())
    except Exception as e:
        app.logger.error(f"Error in make_request: {e}")
        return None

# Decode Protobuf data
def decode_protobuf(binary):
    try:
        items = like_count_pb2.Info()
        items.ParseFromString(bytes.fromhex(binary))
        return items
    except DecodeError as e:
        app.logger.error(f"Error decoding Protobuf data: {e}")
        app.logger.error(f"Binary data: {binary[:100]}")  # Log first 100 bytes for debugging
        return None

@app.route('/like', methods=['GET'])
def handle_requests():
    uid = request.args.get("uid")
    server_name = request.args.get("server_name", "").upper()
    if not uid or not server_name:
        return jsonify({"error": "UID and server_name are required"}), 400

    try:
        tokens = load_tokens(server_name)
        if tokens is None:
            raise Exception("Failed to load tokens.")
        
        token = tokens[0]['token']
        encrypted_uid = encrypt_uid(uid)
        if encrypted_uid is None:
            raise Exception("Encryption of UID failed.")

        before = make_request(encrypted_uid, server_name, token)
        if before is None:
            raise Exception("Failed to retrieve initial player info.")
        
        before_like = int(json.loads(MessageToJson(before)).get('AccountInfo', {}).get('Likes', 0))

        # Your logic here
        url_map = {
            "ME": "https://clientbp.ggblueshark.com/LikeProfile",
            "BR": "https://client.us.freefiremobile.com/LikeProfile",
            "US": "https://client.us.freefiremobile.com/LikeProfile",
            "SAC": "https://client.us.freefiremobile.com/LikeProfile",
            "NA": "https://client.us.freefiremobile.com/LikeProfile"
        }
        url = url_map.get(server_name, "https://clientbp.ggblueshark.com/LikeProfile")

        # Send multiple requests using all tokens
        asyncio.run(send_multiple_requests(uid, server_name, url, total_requests=len(tokens)))

        after = make_request(encrypted_uid, server_name, token)
        if after is None:
            raise Exception("Failed to retrieve player info after like requests.")

        jsone_after = MessageToJson(after)
        data_after = json.loads(jsone_after)
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
