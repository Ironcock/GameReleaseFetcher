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

def get_date_range(days_back=0, days_forward=0):
    today = datetime.date.today()
    start = today - timedelta(days=days_back)
    end = today + timedelta(days=days_forward)
    return f"{start},{end}"

def fetch_games(endpoint_params, target_limit=100):
    games_data = []
    page = 1
    max_pages = 20 # Safety cap
    
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

                # EXTRACT DATA (Rich Schema)
                screenshots = [s['image'] for s in game.get('short_screenshots', [])]
                
                # Get all platforms (Client will filter for PC later)
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
                    "Platforms": platforms # Now includes everything (Xbox, PS5, PC)
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
    
    # 1. New Releases (Last 30 Days)
    # Fetch broadly. Client will filter "PC Only" and "Popularity > X"
    print("Fetching New Releases (Last 30 Days)...")
    data["NewReleases"] = fetch_games({
        "dates": get_date_range(days_back=30, days_forward=0),
        "ordering": "-added", # Most popular first
    }, target_limit=100)

    # 2. Upcoming (Next 90 Days)
    print("Fetching Upcoming (Next 3 Months)...")
    data["Upcoming"] = fetch_games({
        "dates": get_date_range(days_back=0, days_forward=90),
        "ordering": "-added", # Sort by Hype (most added)
    }, target_limit=150)

    with open('daily_games.json', 'w') as f:
        json.dump(data, f, indent=2)

def generate_monthly_feed():
    print("--- Starting Monthly Feed (Top 250) ---")
    data = {}
    
    # 3. Top 250 All Time
    # We fetch 250. Client filters out the old stuff (pre-2005) or non-PC.
    print("Fetching Top 250...")
    data["HallOfFame"] = fetch_games({
        "ordering": "-metacritic",
    }, target_limit=250)

    with open('top_games.json', 'w') as f:
        json.dump(data, f, indent=2)

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--monthly":
        generate_monthly_feed()
    else:
        generate_daily_feed()