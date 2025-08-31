from dotenv import load_dotenv
from flask import Flask, render_template
import requests

from datetime import datetime, timedelta, timezone
import os

from db.db import Database

load_dotenv()
discord_token = os.getenv("DISCORD_TOKEN")
GUILD_ID = 1333167946607886449

cached_events = []
cache_expiry = datetime.min.replace(tzinfo=timezone.utc)

app = Flask(__name__)
db = Database()

def fetch_upcoming_discord_events():
    global cached_events, cache_expiry
    now = datetime.now(timezone.utc)  # timezone-aware current time
    if now < cache_expiry:
        return cached_events  # return cached copy

    url = f"https://discord.com/api/v10/guilds/{GUILD_ID}/scheduled-events"
    headers = {"Authorization": f"Bot {discord_token}"}
    response = requests.get(url, headers=headers)

    events = []
    if response.status_code == 200:
        for e in response.json():
            date_str = e.get('scheduled_start_time')
            if date_str:
                # Convert Discord ISO 8601 string to timezone-aware datetime
                date_obj = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
                date_formatted = date_obj.strftime("%b %d, %Y")
            else:
                date_formatted = "TBA"

            location = "Online" if e.get('channel_id') else e.get('entity_metadata', {}).get('location', 'TBA')

            events.append({
                "title": e.get('name', 'Untitled Event'),
                "date": date_formatted,
                "location": location
            })

    cached_events = events
    cache_expiry = now + timedelta(minutes=10)
    return events

@app.route("/")
@app.route("/home")
@app.route("/about")
@app.route("/index")
def index():
    events = fetch_upcoming_discord_events()
    return render_template("index.html", events=events)

@app.route("/events")
@app.route("/past_events")
def past_events():
    events = db.get_all_events()
    return render_template("events.html", events = events)

if __name__ == "__main__":
    app.run()