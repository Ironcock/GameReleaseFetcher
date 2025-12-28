import os
import requests
import json
from datetime import datetime, timedelta

API_KEY = os.environ["RAWG_API_KEY"]

def fetch_rawg(endpoint, params):
    """Generic helper to fetch data from RAWG"""
    url = f"https://api.rawg.io/api/{endpoint}"
    params["key"] = API_KEY
    params["parent_platforms"] = "1" # ID 1 = PC (Strictly PC only)
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json().get("results", [])
    except Exception as e:
        print(f"Error fetching {endpoint}: {e}")
        return []

def get_video_url(game):
    """Extracts the best available video clip"""
    clip_data = game.get("clip")
    if clip_data and isinstance(clip_data, dict):
        clips = clip_data.get("clips")
        if clips:
            return clips.get("640") or clips.get("320") or clips.get("full") or clip_data.get("clip")
    return ""

def process_games(games_list):
    """Cleans up the raw data for the App"""
    processed = []
    for game in games_list:
        specs = {}
        # Find PC specs
        if game.get("platforms"):
            for p in game.get("platforms"):
                if p.get("platform", {}).get("slug") == "pc":
                    specs = p.get("requirements", {})
                    break

        processed.append({
            "Title": game.get("name"),
            "ReleaseDate": game.get("released"),
            "ImageURL": game.get("background_image"),
            "StoreURL": f"https://rawg.io/games/{game.get('slug')}",
            "VideoURL": get_video_url(game),
            "Rating": game.get("metacritic"),
            "Genres": [g.get("name") for g in game.get("genres", [])[:2]],
            "Specs": {
                "Min": specs.get("minimum", "TBA"),
                "Rec": specs.get("recommended", "TBA")
            }
        })
    return processed

def main():
    today = datetime.now().date()
    
    # 1. NEW RELEASES (Last 30 Days)
    # Filter: Must have > 10 ratings/adds to filter out trash
    start_new = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    end_new = today.strftime("%Y-%m-%d")
    print("Fetching New Releases...")
    new_releases = fetch_rawg("games", {
        "dates": f"{start_new},{end_new}",
        "ordering": "-added", # Most popular first
        "page_size": 20,
        "metacritic": "50,100" # Quality Control: Metacritic 50+ (filters unrated junk)
    })

    # 2. UPCOMING 30 DAYS
    start_up30 = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    end_up30 = (today + timedelta(days=30)).strftime("%Y-%m-%d")
    print("Fetching Upcoming 30...")
    upcoming_30 = fetch_rawg("games", {
        "dates": f"{start_up30},{end_up30}",
        "ordering": "-added",
        "page_size": 20
    })

    # 3. UPCOMING 90 DAYS
    # We start from day 31 to avoid duplicates with the list above
    start_up90 = (today + timedelta(days=31)).strftime("%Y-%m-%d")
    end_up90 = (today + timedelta(days=90)).strftime("%Y-%m-%d")
    print("Fetching Upcoming 90...")
    upcoming_90 = fetch_rawg("games", {
        "dates": f"{start_up90},{end_up90}",
        "ordering": "-added",
        "page_size": 20
    })

    # 4. ALL TIME TOP 150 (PC)
    print("Fetching Top 150...")
    # RAWG's 'metacritic' ordering is best for "All Time"
    top_150 = fetch_rawg("games", {
        "ordering": "-metacritic",
        "page_size": 40, # Let's just get top 40 for now to keep file size small
        "metacritic": "80,100"
    })

    # Package everything
    final_data = {
        "NewReleases": process_games(new_releases),
        "Upcoming30": process_games(upcoming_30),
        "Upcoming90": process_games(upcoming_90),
        "TopGames": process_games(top_150)
    }

    with open("releases.json", "w") as f:
        json.dump(final_data, f, indent=2)
    
    print("Success! releases.json updated.")

if __name__ == "__main__":
    main()