#!/usr/bin/env python3
"""
Strava Captain Haddock Transformer

Fetches your latest Strava activity and rewrites the title and description
in Captain Haddock's voice using Claude.

Usage:
    python haddock.py              # Transform latest activity
    python haddock.py --dry-run    # Preview without updating Strava
    python haddock.py --activity ID  # Transform specific activity
    python haddock.py --activities N  # Transform last N activities
"""

import os
import argparse
import requests
from datetime import datetime
from dotenv import load_dotenv, set_key
import anthropic

load_dotenv()

# Strava API
STRAVA_CLIENT_ID = os.getenv("STRAVA_CLIENT_ID")
STRAVA_CLIENT_SECRET = os.getenv("STRAVA_CLIENT_SECRET")
STRAVA_ACCESS_TOKEN = os.getenv("STRAVA_ACCESS_TOKEN")
STRAVA_REFRESH_TOKEN = os.getenv("STRAVA_REFRESH_TOKEN")

# Anthropic
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

STRAVA_API_BASE = "https://www.strava.com/api/v3"


def refresh_access_token():
    """Refresh the Strava access token if expired."""
    response = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id": STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "grant_type": "refresh_token",
            "refresh_token": STRAVA_REFRESH_TOKEN,
        },
    )
    response.raise_for_status()
    tokens = response.json()
    
    # Update .env with new tokens
    env_path = os.path.join(os.path.dirname(__file__), ".env")
    set_key(env_path, "STRAVA_ACCESS_TOKEN", tokens["access_token"])
    set_key(env_path, "STRAVA_REFRESH_TOKEN", tokens["refresh_token"])
    
    return tokens["access_token"]


def strava_request(method, endpoint, **kwargs):
    """Make a Strava API request, handling token refresh if needed."""
    global STRAVA_ACCESS_TOKEN
    
    headers = {"Authorization": f"Bearer {STRAVA_ACCESS_TOKEN}"}
    url = f"{STRAVA_API_BASE}{endpoint}"
    
    response = requests.request(method, url, headers=headers, **kwargs)
    
    # Token expired - refresh and retry
    if response.status_code == 401:
        print("Token expired, refreshing...")
        STRAVA_ACCESS_TOKEN = refresh_access_token()
        headers = {"Authorization": f"Bearer {STRAVA_ACCESS_TOKEN}"}
        response = requests.request(method, url, headers=headers, **kwargs)
    
    response.raise_for_status()
    return response.json()

def get_last_N_activities(last_n):
    activities = strava_request("GET", "/athlete/activities", params={"per_page": last_n})
    if not activities:
        return None
    return activities

def get_latest_activity():
    """Fetch the most recent activity."""
    activities = strava_request("GET", "/athlete/activities", params={"per_page": 1})
    if not activities:
        return None
    return activities[0]


def get_activity(activity_id):
    """Fetch a specific activity by ID."""
    return strava_request("GET", f"/activities/{activity_id}")


def format_pace(meters_per_second):
    """Convert m/s to min/mi pace string."""
    if not meters_per_second or meters_per_second == 0:
        return "N/A"
    
    seconds_per_mile = 1609.34 / meters_per_second
    minutes = int(seconds_per_mile // 60)
    seconds = int(seconds_per_mile % 60)
    return f"{minutes}:{seconds:02d} /mi"


def format_distance(meters):
    """Convert meters to miles."""
    miles = meters / 1609.34
    return f"{miles:.2f} mi"


def format_duration(seconds):
    """Format seconds as Xh Ym Zs."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    parts = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    
    return " ".join(parts)


def build_workout_summary(activity):
    """Build a text summary of the workout for Claude to transform."""
    lines = []
    
    # Basic info
    lines.append(f"Activity Type: {activity.get('type', 'Workout')}")
    lines.append(f"Original Title: {activity.get('name', 'Untitled')}")
    
    # Duration
    elapsed = activity.get("elapsed_time", 0)
    lines.append(f"Duration: {format_duration(elapsed)}")
    
    # Distance (if applicable)
    distance = activity.get("distance", 0)
    if distance:
        lines.append(f"Distance: {format_distance(distance)}")
    
    # Pace (for runs)
    avg_speed = activity.get("average_speed", 0)
    if avg_speed and activity.get("type") in ["Run", "VirtualRun"]:
        lines.append(f"Pace: {format_pace(avg_speed)}")
    
    # Heart rate
    avg_hr = activity.get("average_heartrate")
    max_hr = activity.get("max_heartrate")
    if avg_hr:
        lines.append(f"Average Heart Rate: {avg_hr:.0f} bpm")
    if max_hr:
        lines.append(f"Max Heart Rate: {max_hr:.0f} bpm")
    
    # Calories
    calories = activity.get("calories")
    if calories:
        lines.append(f"Calories: {calories:.0f}")
    
    # Elevation
    elevation = activity.get("total_elevation_gain", 0)
    if elevation:
        lines.append(f"Elevation Gain: {elevation * 3.28084:.0f} ft")
    
    # Peloton-specific: check description for extra data
    description = activity.get("description", "")
    if description:
        lines.append(f"Original Description: {description}")
    
    return "\n".join(lines)


def haddockify(workout_summary):
    """Use Claude to rewrite the workout in Captain Haddock's voice."""
    
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    
    prompt = f"""You are Captain Haddock from the Tintin comics. You've just completed a workout and need to log it in your exercise journal.

Rewrite this workout summary in your authentic voice with the following guidelines:

VARIETY IN OPENING:
- Vary your narrative approach each time - don't always start with an exclamation
- Options: Start with action ("Dragged myself..."), reflection ("Well, that was..."), boastful statement ("Another conquest..."), or grumbling ("Of all the...")
- Let the workout performance guide your mood

NATURAL EXCLAMATIONS:
- Tie exclamations to specific moments or metrics, not scattered randomly
- Example: "My heart reached 185 bpm - thundering typhoons!" or "8 miles through this blasted heat - blistering barnacles!"
- Use 1-2 exclamations maximum - make them count
- Vary intensity: save big multi-word ones ("Ten thousand thundering typhoons!") for impressive achievements
- Classic options: blistering barnacles, thundering typhoons, billions of blue blistering barnacles, by Neptune's beard, by Lucifer's whiskers

TONE GUIDANCE:
- Fast pace or long distance → proud, boastful
- Struggled or slow → grumbling but determined
- High heart rate → dramatic concern
- Easy workout → casual, dismissive

Keep it concise - a punchy title (under 10 words) and description (2-4 sentences). The humor comes from contrasting mundane fitness metrics with your dramatic seafaring personality.

WORKOUT DATA:
{workout_summary}

Respond in this exact format:
TITLE: [your haddock-style title]
DESCRIPTION: [your haddock-style description]"""

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    
    response_text = message.content[0].text
    
    # Parse the response
    title = ""
    description = ""
    
    for line in response_text.split("\n"):
        if line.startswith("TITLE:"):
            title = line.replace("TITLE:", "").strip()
        elif line.startswith("DESCRIPTION:"):
            description = line.replace("DESCRIPTION:", "").strip()
    
    # Handle multi-line descriptions
    if "DESCRIPTION:" in response_text:
        desc_start = response_text.find("DESCRIPTION:") + len("DESCRIPTION:")
        description = response_text[desc_start:].strip()
    
    return title, description


def update_activity(activity_id, title, description):
    """Update the activity on Strava."""
    return strava_request(
        "PUT",
        f"/activities/{activity_id}",
        json={"name": title, "description": description},
    )


def main():
    parser = argparse.ArgumentParser(
        description="Transform Strava activities into Captain Haddock's voice"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the transformation without updating Strava",
    )
    parser.add_argument(
        "--activity",
        type=int,
        help="Specific activity ID to transform (default: latest)",
    )
    parser.add_argument(
        "--activities",
        type=int,
        help="Specify last N activities to Haddockify",
    )
    args = parser.parse_args()
    
    # Validate credentials
    if not STRAVA_ACCESS_TOKEN:
        print("ERROR: No Strava access token. Run 'python auth.py' first.")
        return
    
    if not ANTHROPIC_API_KEY or ANTHROPIC_API_KEY == "your_anthropic_api_key_here":
        print("ERROR: Set ANTHROPIC_API_KEY in .env file")
        print("Get your key from: https://console.anthropic.com/")
        return
    
    # Fetch activity
    print("Fetching activity from Strava...")
    activities = []    
    if args.activity:
        activity = get_activity(args.activity)
        activities.append(activity)
    elif args.activities:
        activities = get_last_N_activities(args.activities)
    else:
        activity = get_latest_activity()
        activities.append(activity)
    
    if not activities:
        print("No activities found!")
        return
    
    for activity in activities:
        activity_id = activity["id"]
        original_title = activity.get("name", "Untitled")
    
        print(f"\nOriginal Activity: {original_title}")
        print(f"ID: {activity_id}")
        print(f"Type: {activity.get('type')}")
        print(f"Date: {activity.get('start_date_local', '')[:10]}")
        
        # Build summary and transform
        print("\nGenerating Captain Haddock version...")
        summary = build_workout_summary(activity)
        
        try:
            new_title, new_description = haddockify(summary)
        except anthropic.APIError as e:
            print(f"Error calling Claude API: {e}")
            return
        
        print("\n" + "=" * 50)
        print("HADDOCK VERSION:")
        print("=" * 50)
        print(f"Title: {new_title}")
        print(f"Description: {new_description}")
        print("=" * 50)
        
        if args.dry_run:
            print("\n[DRY RUN - No changes made to Strava]")
        else:
            print("\nUpdating Strava...")
            update_activity(activity_id, new_title, new_description)
            print("Done! Activity updated.")
            print(f"\nView it at: https://www.strava.com/activities/{activity_id}")


if __name__ == "__main__":
    main()
