#!/usr/bin/env python3
"""
Strava OAuth Authentication Helper

Run this script once to get your access and refresh tokens with the correct scopes.
It will:
1. Generate an authorization URL for you to visit
2. Start a local server to catch the callback
3. Exchange the code for tokens
4. Save them to your .env file
"""

import os
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import requests
from dotenv import load_dotenv, set_key

load_dotenv()

CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
REDIRECT_URI = "http://localhost:8000/callback"
SCOPES = "read,activity:read_all,activity:write"

# Store the auth code when received
auth_code = None


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        
        parsed = urlparse(self.path)
        if parsed.path == "/callback":
            params = parse_qs(parsed.query)
            
            if "code" in params:
                auth_code = params["code"][0]
                self.send_response(200)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                self.wfile.write(b"""
                    <html><body style="font-family: sans-serif; text-align: center; padding-top: 50px;">
                    <h1>Authorization Successful!</h1>
                    <p>You can close this window and return to the terminal.</p>
                    </body></html>
                """)
            elif "error" in params:
                self.send_response(400)
                self.send_header("Content-type", "text/html")
                self.end_headers()
                error = params.get("error", ["Unknown"])[0]
                self.wfile.write(f"<html><body><h1>Error: {error}</h1></body></html>".encode())
            else:
                self.send_response(404)
                self.end_headers()
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logging


def get_auth_url():
    """Generate the Strava authorization URL."""
    return (
        f"https://www.strava.com/oauth/authorize"
        f"?client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
        f"&response_type=code"
        f"&scope={SCOPES}"
    )


def exchange_code_for_tokens(code):
    """Exchange the authorization code for access and refresh tokens."""
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
        },
    )
    response.raise_for_status()
    return response.json()


def main():
    if not CLIENT_ID or not CLIENT_SECRET or CLIENT_SECRET == "your_client_secret_here":
        print("ERROR: Please set STRAVA_CLIENT_ID and STRAVA_CLIENT_SECRET in .env file")
        print("Copy .env.example to .env and fill in your credentials.")
        return

    print("=" * 60)
    print("Strava OAuth Authentication")
    print("=" * 60)
    print()
    print("This will open your browser to authorize the app.")
    print("Requesting scopes:", SCOPES)
    print()
    
    auth_url = get_auth_url()
    print("If browser doesn't open, visit this URL:")
    print(auth_url)
    print()
    
    # Start local server
    server = HTTPServer(("localhost", 8000), CallbackHandler)
    
    # Open browser
    webbrowser.open(auth_url)
    
    print("Waiting for authorization...")
    
    # Handle one request (the callback)
    while auth_code is None:
        server.handle_request()
    
    server.server_close()
    
    print()
    print("Got authorization code, exchanging for tokens...")
    
    try:
        tokens = exchange_code_for_tokens(auth_code)
        
        access_token = tokens["access_token"]
        refresh_token = tokens["refresh_token"]
        athlete = tokens.get("athlete", {})
        
        print()
        print("Success! Authenticated as:", athlete.get("firstname", ""), athlete.get("lastname", ""))
        print()
        
        # Save to .env
        env_path = os.path.join(os.path.dirname(__file__), ".env")
        set_key(env_path, "STRAVA_ACCESS_TOKEN", access_token)
        set_key(env_path, "STRAVA_REFRESH_TOKEN", refresh_token)
        
        print("Tokens saved to .env file!")
        print()
        print("You can now run: python haddock.py")
        
    except requests.exceptions.HTTPError as e:
        print(f"Error exchanging code: {e}")
        print(e.response.text)


if __name__ == "__main__":
    main()
