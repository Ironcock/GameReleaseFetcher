import os
import requests
import json
from datetime import datetime, timedelta

# 1. Get Secret (This will pull the key you just set in Step 1)
API_KEY = os.environ["RAWG_API_KEY"]

def get_upcoming_games():
    url = "https://api.rawg.io/api/games"
    
    # Date Range: Tomorrow -> 6 Months from now
    today = datetime.now().date()
    start_date = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    end_date = (today + timedelta(days=180)).strftime("%Y-%m-%d")
    
    params = {
        "key": API_KEY,
        "dates": f"{start_date},{end_date}",
        "ordering": "-added",  # Sort by popularity
        "page_size": 20
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error fetching data: {e}")
        return {"results": []}

def get_pc_requirements(platforms):
    """Helper to find PC specs from the platform list"""
    for p in platforms:
        platform_data = p.get("platform", {})
        if platform_data.get("slug") == "pc":
            return p.get("requirements", {})
    return {}

def process_data(data):
    processed = []
    for game in data.get("results", []):
        
        # 1. Get Video (Best Quality)
        clip_data = game.get("clip")
        video_url = ""
        if clip_data and isinstance(clip_data, dict):
            clips = clip_data.get("clips")
            if clips:
                # Prioritize 640p, then 320p, then full
                video_url = clips.get("640") or clips.get("320") or clips.get("full") or clip_data.get("clip")

        # 2. Get PC Specs (Min/Rec)
        specs = get_pc_requirements(game.get("platforms", []))
        
        # 3. Get Genres (Top 2)
        genres = [g.get("name") for g in game.get("genres", [])[:2]]

        processed.append({
            "Title": game.get("name"),
            "ReleaseDate": game.get("released"),
            "ImageURL": game.get("background_image"),
            "StoreURL": f"https://rawg.io/games/{game.get('slug')}",
            "VideoURL": video_url,
            "Genres": genres,
            "Specs": {
                "Min": specs.get("minimum", "TBA"),
                "Rec": specs.get("recommended", "TBA")
            }
        })
    return processed

if __name__ == "__main__":
    print("Fetching games...")
    raw_data = get_upcoming_games()
    final_json = process_data(raw_data)
    
    with open("releases.json", "w") as f:
        json.dump(final_json, f, indent=2)
    
    print(f"Success! Saved {len(final_json)} games.")