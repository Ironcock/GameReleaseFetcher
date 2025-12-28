import requests
import json
import datetime
from datetime import timedelta
import os
import sys
import time

# CONFIGURATION
API_KEY = os.environ.get("RAWG_API_KEY") 
BASE_URL = "https://api.rawg.io/api/games"
PC_PLATFORM_ID = 4  # RAWG ID for PC

# --- SAFETY CONFIGURATION ---

# 1. HARD BANS: Instant rejection.
HARD_BANNED_TAGS = {
    "nsfw", 
    "hentai", 
    "erotica", 
    "porn",
    "sex" 
}

# 2. RISKY TAGS: Allowed ONLY if Added Count > Threshold.
RISKY_TAGS = {
    "nudity", 
    "sexual-content", 
    "mature", 
    "mature-content"
}

# 3. TITLE BLACKLIST
BANNED_TITLE_KEYWORDS = [
    "hentai", "porn", "sex ", "waifu", "uncensored", "boobs", "milf"
]

def get_date_range(days_back=0, days_forward=0):
    today = datetime.date.today()
    start = today - timedelta(days=days_back)
    end = today + timedelta(days=days_forward)
    return f"{start},{end}"

def is_safe_for_work(game):
    # 1. ESRB Check
    if game.get("esrb_rating"):
        slug = game["esrb_rating"].get("slug")
        if slug == "adults-only":
            return False

    # 2. Tag Check
    if game.get("tags"):
        for tag in game["tags"]:
            slug = tag.get("slug")
            
            if slug in HARD_BANNED_TAGS:
                return False
                
            if slug in RISKY_TAGS:
                # Threshold = 10 (Allows new releases, blocks junk)
                if game.get("added", 0) < 10: 
                    return False

    # 3. Title Check
    title_lower = game.get("name", "").lower()
    if any(bad_word in title_lower for bad_word in BANNED_TITLE_KEYWORDS):
        return False
        
    return True

def fetch_games(endpoint_params, target_limit=100):
    games_data = []
    page = 1
    max_pages = 25 
    
    print(f"   > Fetching target: {target_limit} items...")

    while len(games_data) < target_limit and page < max_pages:
        params = {
            "key": API_KEY,
            "page_size": 40,
            "page": page,
            **endpoint_params
        }
        
        try:
            response = requests.get(BASE_URL, params=params)
            response.raise_for_status()
            data = response.json()
            results = data.get("results", [])
            
            if not results:
                break

            for game in results:
                if len(games_data) >= target_limit:
                    break

                if not is_safe_for_work(game):
                    continue

                screenshots = [s['image'] for s in game.get('short_screenshots', [])]
                platforms = []
                if game.get('parent_platforms'):
                    platforms = [p['platform']['slug'] for p in game['parent_platforms']]
                
                tags_list = [t['name'] for t in game.get('tags', [])][:5]

                game_obj = {
                    "ID": game['id'],
                    "Title": game['name'],
                    "ReleaseDate": game.get('released', 'TBA'),
                    "ImageURL": game.get('background_image') or "", 
                    "StoreURL": f"https://rawg.io/games/{game['slug']}",
                    "Metacritic": game.get('metacritic'),
                    "AddedCount": game.get('added', 0),
                    "Rating": game.get('rating', 0.0),
                    "ShortScreenshots": screenshots, 
                    "Genres": [g['name'] for g in game.get('genres', [])][:3],
                    "Tags": tags_list,
                    "Platforms": platforms
                }
                
                games_data.append(game_obj)
            
            print(f"   > Page {page} done. Count: {len(games_data)}")
            page += 1
            time.sleep(0.2)
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break

    return games_data

def generate_daily_feed():
    print("--- Starting Daily Feed (New & Upcoming) ---")
    data = {}
    
    # We strictly enforce PC_PLATFORM_ID here to ensure the list isn't filled with mobile/console games
    print("Fetching New Releases (Last 30 Days)...")
    data["NewReleases"] = fetch_games({
        "dates": get_date_range(days_back=30, days_forward=0),
        "ordering": "-added", 
        "parent_platforms": PC_PLATFORM_ID 
    }, target_limit=100)

    print("Fetching Upcoming (Next 3 Months)...")
    data["Upcoming"] = fetch_games({
        "dates": get_date_range(days_back=0, days_forward=90),
        "ordering": "-added", 
        "parent_platforms": PC_PLATFORM_ID
    }, target_limit=150)

    with open('daily_games.json', 'w') as f:
        json.dump(data, f, indent=2)

def generate_monthly_feed():
    print("--- Starting Monthly Feed (Top 250) ---")
    data = {}
    
    print("Fetching Top 250...")
    data["HallOfFame"] = fetch_games({
        "ordering": "-metacritic",
        "parent_platforms": PC_PLATFORM_ID
    }, target_limit=250)

    with open('top_games.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--monthly":
        generate_monthly_feed()
    else:
        generate_daily_feed()

# Command to push:
# git add .
# git commit -m "Restore PC Platform constraint to fix missing games"
# git push