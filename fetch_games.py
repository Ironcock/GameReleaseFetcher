import requests
import json
import datetime
from datetime import timedelta
import re
import os
import sys

# CONFIGURATION
# SECURE THIS: Use environment variable from GitHub Actions
API_KEY = os.environ.get("RAWG_API_KEY") 
BASE_URL = "https://api.rawg.io/api/games"

# FILTERS
PC_PLATFORM_ID = 4
MIN_ADDED_COUNT_HOF = 1500  # "Baseball Filter"

def get_date_range(days_back=0, days_forward=0):
    today = datetime.date.today()
    start = today - timedelta(days=days_back)
    end = today + timedelta(days=days_forward)
    return f"{start},{end}"

def clean_game_name(name):
    name = name.lower()
    subs = ["goty", "game of the year", "complete edition", "definitive edition", 
            "director's cut", "final cut", "enhanced edition", "remastered"]
    for sub in subs:
        name = name.replace(sub, "")
    name = re.sub(r'[^a-z0-9]', '', name)
    return name

def fetch_games(endpoint_params, limit=20, clean_duplicates=False):
    games_data = []
    seen_names = set()
    page = 1
    
    while len(games_data) < limit:
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
                if len(games_data) >= limit:
                    break

                # 1. Hall of Fame "Obscurity" Filter
                if clean_duplicates and game.get('added', 0) < MIN_ADDED_COUNT_HOF:
                    continue 

                # 2. Duplicate/Edition Filter
                if clean_duplicates:
                    clean_name = clean_game_name(game['name'])
                    if clean_name in seen_names:
                        continue
                    seen_names.add(clean_name)
                    
                    bad_keywords = ["dlc", "soundtrack", "expansion pass", "season pass", "bonus content"]
                    if any(bad in game['name'].lower() for bad in bad_keywords):
                        continue

                # 3. Map Data to New Schema
                # Extract screenshots for the "Hover Scrub" feature
                screenshots = [s['image'] for s in game.get('short_screenshots', [])]
                
                # Robust Platform Check (handle missing parent_platforms)
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
                    "AddedCount": game.get('added', 0),
                    "Rating": game.get('rating', 0.0),
                    "ShortScreenshots": screenshots, 
                    "Genres": [g['name'] for g in game.get('genres', [])][:3],
                    "Platforms": platforms
                }
                
                games_data.append(game_obj)
            
            page += 1
            
        except Exception as e:
            print(f"Error fetching page {page}: {e}")
            break

    return games_data

def generate_daily_feed():
    print("--- Starting Pipeline A (Daily) ---")
    data = {}
    
    print("Fetching New Releases...")
    data["NewReleases"] = fetch_games({
        "dates": get_date_range(days_back=45, days_forward=0),
        "ordering": "-added", 
        "parent_platforms": PC_PLATFORM_ID 
    }, limit=15)

    print("Fetching Upcoming...")
    data["Upcoming"] = fetch_games({
        "dates": get_date_range(days_back=0, days_forward=180),
        "ordering": "released",
        "parent_platforms": PC_PLATFORM_ID
    }, limit=15)

    with open('daily_games.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("Saved daily_games.json")

def generate_monthly_feed():
    print("--- Starting Pipeline B (Monthly) ---")
    data = {}
    
    print("Fetching Hall of Fame...")
    data["HallOfFame"] = fetch_games({
        "ordering": "-metacritic",
        "parent_platforms": PC_PLATFORM_ID,
    }, limit=20, clean_duplicates=True)

    with open('top_games.json', 'w') as f:
        json.dump(data, f, indent=2)
    print("Saved top_games.json")

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--monthly":
        generate_monthly_feed()
    else:
        # Default to daily if no flag or --daily provided
        generate_daily_feed()