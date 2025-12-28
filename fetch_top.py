import os
import requests
import json
import time
from datetime import datetime, timedelta

API_KEY = os.environ["RAWG_API_KEY"]

def get_hover_clip(game):
    """
    Strictly extracts the 'clip' video used for hover previews.
    Returns empty string if no clip is available.
    """
    clip_obj = game.get("clip")
    if not clip_obj:
        return ""
    
    # Priority: Full res clip -> 640p -> 320p -> generic full
    if clip_obj.get("clip"):
        return clip_obj.get("clip")
    
    clips = clip_obj.get("clips", {})
    if clips:
        return clips.get("640") or clips.get("320") or clips.get("full") or ""

    return ""

def process_game(game):
    specs = {"Min": "TBA", "Rec": "TBA"}
    
    # Platform filtering for PC specs
    if game.get("platforms"):
        for p in game.get("platforms"):
            if p.get("platform", {}).get("slug") == "pc":
                raw = p.get("requirements") or p.get("requirements_en") or {}
                specs["Min"] = raw.get("minimum", "TBA")
                specs["Rec"] = raw.get("recommended", "TBA")
                break
    
    # Get the hover clip only
    video_url = get_hover_clip(game)

    return {
        "Title": game.get("name"),
        "ReleaseDate": game.get("released"),
        "ImageURL": game.get("background_image"),
        "StoreURL": f"https://rawg.io/games/{game.get('slug')}",
        "VideoURL": video_url,
        "Metacritic": game.get("metacritic"),
        "MetacriticURL": game.get("metacritic_url", ""),
        "RedditURL": game.get("reddit_url", ""),
        "WebsiteURL": game.get("website", ""),
        "Genres": [g.get("name") for g in game.get("genres", [])],
        "Specs": specs
    }

def main():
    print("--- Starting Monthly Deep Fetch (Top 150 Modern PC Games) ---")
    print("--- Mode: Hover Clips Only (Fast) ---")
    
    today = datetime.now().date()
    # Filter: Last 10 Years
    ten_years_ago = (today - timedelta(days=365*10)).strftime("%Y-%m-%d")
    today_str = today.strftime("%Y-%m-%d")
    
    all_games = []
    url = "https://api.rawg.io/api/games"
    
    params = {
        "key": API_KEY,
        "parent_platforms": "1",    # PC Only
        "dates": f"{ten_years_ago},{today_str}",
        "ordering": "-metacritic",
        "metacritic": "80,100",
        "page_size": 40
    }
    
    while url and len(all_games) < 150:
        try:
            if url == "https://api.rawg.io/api/games":
                resp = requests.get(url, params=params)
            else:
                resp = requests.get(url) 
                
            if resp.status_code != 200:
                print(f"Error fetching data: {resp.status_code}")
                break

            data = resp.json()
            
            for g in data.get("results", []):
                if any(existing['Title'] == g.get('name') for existing in all_games):
                    continue
                    
                print(f"Processing ({len(all_games) + 1}/150): {g.get('name')}")
                all_games.append(process_game(g))
                
                if len(all_games) >= 150:
                    break
                    
            url = data.get("next")
            time.sleep(0.2)
            
        except Exception as e:
            print(f"An error occurred: {e}")
            break
        
    with open("top_games.json", "w") as f:
        json.dump(all_games, f, indent=2)
    
    print(f"Success! Saved {len(all_games)} modern top games.")

if __name__ == "__main__":
    main()