import requests
import json
import datetime
from datetime import timedelta
import os
import sys
import time

# CONFIGURATION
# The script prioritizes the environment variable for GitHub Actions, fallback for local testing.
API_KEY = os.environ.get("RAWG_API_KEY") or "0ac6ccd2428642d8be0bdf14a1077985"
BASE_URL = "https://api.rawg.io/api/games"

# CONTENT FILTERING RULES (Matching the current HTML logic)
BLACKLIST_TAGS = ['nsfw', 'erotica', 'hentai', 'porn', 'uncensored']
CONDITIONAL_TAGS = ['nudity', 'mature', 'sexual-content', 'adult']
MIN_ADDED_FOR_MATURE = 10

def get_date_range(days_back=0, days_forward=0):
    """Generates a date string for RAWG API (YYYY-MM-DD,YYYY-MM-DD)"""
    today = datetime.date.today()
    start = today - timedelta(days=days_back)
    end = today + timedelta(days=days_forward)
    return f"{start},{end}"

def is_filtered_adult_content(game_tags, added_count):
    """
    Filters out adult content based on tags and popularity:
    1. Hard-blocks specific NSFW tags.
    2. Filters 'Mature' content unless the game has at least 10 'Adds'.
    """
    if any(tag in BLACKLIST_TAGS for tag in game_tags):
        return True
    
    if any(tag in CONDITIONAL_TAGS for tag in game_tags):
        if added_count < MIN_ADDED_FOR_MATURE:
            return True
            
    return False

def fetch_games(endpoint_params, target_limit=500):
    """Fetches games from RAWG across multiple pages to reach the target limit."""
    games_data = []
    page = 1
    max_pages = 40 
    
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

                # Extract Tags and Adds for Filtering
                tags_list = [t['slug'] for t in game.get('tags', [])]
                added_count = game.get('added', 0)

                # APPLY CONTENT FILTER
                if is_filtered_adult_content(tags_list, added_count):
                    continue

                # EXTRACT DATA
                screenshots = [s['image'] for s in game.get('short_screenshots', [])]
                
                platforms = []
                if game.get('parent_platforms'):
                    platforms = [p['platform']['slug'] for p in game['parent_platforms']]

                game_obj = {
                    "ID": game['id'],
                    "Title": game['name'],
                    "ReleaseDate": game.get('released', 'TBA'),
                    "ImageURL": game.get('background_image') or "", 
                    "StoreURL": f"https://rawg.io/games/{game['slug']}",
                    "Metacritic": game.get('metacritic'),
                    "AddedCount": added_count,
                    "Rating": game.get('rating', 0.0),
                    "ShortScreenshots": screenshots, 
                    "Genres": [g['name'] for g in game.get('genres', [])][:3],
                    "Tags": tags_list,
                    "Platforms": platforms
                }
                
                games_data.append(game_obj)
            
            print(f"   > Page {page} processed. Total items gathered: {len(games_data)}")
            page += 1
            time.sleep(0.2) # Safety delay to avoid rate limiting
            
        except Exception as e:
            print(f"Error on page {page}: {e}")
            break

    return games_data

def generate_daily_feed():
    """Pipeline: Generates the daily update for New Releases and Upcoming games."""
    print("--- Starting Daily Feed Generation ---")
    data = {}
    
    # NEW RELEASES: Last 30 days, PC Only, Newest First
    print("Fetching New Releases (Last 30 Days)...")
    data["NewReleases"] = fetch_games({
        "dates": get_date_range(days_back=30, days_forward=0),
        "parent_platforms": 1,
        "ordering": "-released"
    }, target_limit=500)

    # UPCOMING: Next 90 days, PC Only, Closest Date First
    print("Fetching Upcoming (Next 90 Days)...")
    data["Upcoming"] = fetch_games({
        "dates": get_date_range(days_back=0, days_forward=90),
        "parent_platforms": 1,
        "ordering": "released"
    }, target_limit=500)

    with open('daily_games.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(">> daily_games.json generated.")

def generate_monthly_feed():
    """Pipeline: Generates the stable monthly update for the Hall of Fame."""
    print("--- Starting Monthly Feed Generation ---")
    data = {}
    
    # TOP GAMES: Ordered by Metacritic score
    print("Fetching Top 250 (Hall of Fame)...")
    data["HallOfFame"] = fetch_games({
        "parent_platforms": 1,
        "ordering": "-metacritic",
    }, target_limit=250)

    with open('top_games.json', 'w') as f:
        json.dump(data, f, indent=2)
    print(">> top_games.json generated.")

if __name__ == "__main__":
    # Check for the --monthly flag to run Pipeline B
    if len(sys.argv) > 1 and sys.argv[1] == "--monthly":
        generate_monthly_feed()
    else:
        generate_daily_feed()