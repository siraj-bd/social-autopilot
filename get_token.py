import urllib.request
import urllib.parse
import json

data = urllib.parse.urlencode({
    'grant_type': 'authorization_code',
    'code': 'AQSvsGGpgH0xd4qK4faGmX61G5mTQvqFbDZu1K6_w3r2oKZceMX65zOduC0abqZSq6nTbDc4eWOL7qUkyKS90r6U8frxaeUpJwO-9n-Bzm6GQMitl9sRaGVm4M3jEu3EsvoNZmCWY6qBj22AZcmIAfCu60jbgR0nTWlS1lXwHQX9i3YcZarxEx9g_B-_V6eKUNknh4KXz6gys-LV3u0',
    'client_id': '86qcf8nn6915b5',
    'client_secret': 'WPL_AP1.2bQ5IUGJGvzDvzGU.z1nskw==',
    'redirect_uri': 'https://localhost'
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
