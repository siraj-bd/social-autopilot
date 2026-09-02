import os
import sys
import json
import urllib.request
import urllib.parse
from dotenv import load_dotenv

load_dotenv()

client_id = os.getenv("LINKEDIN_CLIENT_ID", "").strip()
client_secret = os.getenv("LINKEDIN_CLIENT_SECRET", "").strip()
redirect_uri = os.getenv("LINKEDIN_REDIRECT_URI", "https://localhost").strip()
code = os.getenv("LINKEDIN_AUTH_CODE", "").strip()

if not client_id or not client_secret or not code:
    print("\n--- LinkedIn Token Exchange Helper ---")
    print("ব্যবহার বিধি:")
    print("1. আপনার .env ফাইলে নিচের ভ্যারিয়েবলগুলো সেট করুন:")
    print("   LINKEDIN_CLIENT_ID=your_client_id")
    print("   LINKEDIN_CLIENT_SECRET=your_client_secret")
    print("   LINKEDIN_REDIRECT_URI=https://localhost")
    print("   LINKEDIN_AUTH_CODE=your_authorization_code")
    print("2. তারপর পুনরায় রান করুন: python get_token.py\n")
    sys.exit(0)

data = urllib.parse.urlencode({
    'grant_type': 'authorization_code',
    'code': code,
    'client_id': client_id,
    'client_secret': client_secret,
    'redirect_uri': redirect_uri
}).encode('utf-8')

req = urllib.request.Request(
    'https://www.linkedin.com/oauth/v2/accessToken',
    data=data,
    headers={'Content-Type': 'application/x-www-form-urlencoded'}
)

try:
    with urllib.request.urlopen(req) as response:
        result = json.loads(response.read().decode('utf-8'))
        token = result.get('access_token')
        print("\n================ SUCCESS ================")
        print(f"LINKEDIN_ACCESS_TOKEN:\n{token}")
        
        user_req = urllib.request.Request('https://api.linkedin.com/v2/userinfo', headers={'Authorization': f'Bearer {token}'})
        with urllib.request.urlopen(user_req) as user_res:
            user_data = json.loads(user_res.read().decode('utf-8'))
            print(f"\nLINKEDIN_AUTHOR_URN:\nurn:li:person:{user_data.get('sub')}")
        print("=========================================\n")
except urllib.error.HTTPError as e:
    print("\n--- ERROR ---")
    print(e.read().decode('utf-8'))
