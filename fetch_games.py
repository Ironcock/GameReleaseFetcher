import os
import requests
import json
import time
from datetime import datetime, timedelta

API_KEY = os.environ["RAWG_API_KEY"]

def get_hover_clip(game):
    clip_obj = game.get("clip")
    if not clip_obj:
        return ""
    
    if clip_obj.get("clip"):
        return clip_obj.get("clip")
    
    clips = clip_obj.get("clips", {})
    if clips:
        return clips.get("640") or clips.get("320") or clips.get("full") or ""

    return ""

def process_game(game):
    specs = {"Min": "TBA", "Rec": "TBA"}
    if game.get("platforms"):
        for p in game.get("platforms"):
            if p.get("platform", {}).get("slug") == "pc":
                raw = p.get("requirements") or p.get("requirements_en") or {}
                specs["Min"] = raw.get("minimum", "TBA")
                specs["Rec"] = raw.get("recommended", "TBA")
                break

    return {
        "Title": game.get("name"),
        "ReleaseDate": game.get("released"),
        "ImageURL": game.get("background_image"),
        "StoreURL": f"https://rawg.io/games/{game.get('slug')}",
        "VideoURL": get_hover_clip(game),
        "Rating": game.get("metacritic"),
        "Popularity": game.get("added", 0),
        "Genres": [g.get("name") for g in game.get("genres", [])],
        "Specs": specs
    }

def fetch_section(name, params, limit):
    print(f"--- Fetching {name} ---")
    results = []
    url = "https://api.rawg.io/api/games"
    params["key"] = API_KEY
    params["parent_platforms"] = "1"
    params["page_size"] = 40
    
    while url and len(results) < limit:
        if url == "https://api.rawg.io/api/games":
            resp = requests.get(url, params=params)
        else:
            resp = requests.get(url)
        data = resp.json()
        for g in data.get("results", []):
            # No dedupe needed for daily sections usually
            results.append(process_game(g))
            if len(results) >= limit: break
            
        url = data.get("next")
        time.sleep(0.2)
    return results

def main():
    today = datetime.now().date()
    
    # 1. NEW RELEASES
    start_new = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    end_new = today.strftime("%Y-%m-%d")
    new_games = fetch_section("NewReleases", {"dates": f"{start_new},{end_new}", "ordering": "-added"}, 60)

    # 2. UPCOMING
    start_up = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    end_up = (today + timedelta(days=60)).strftime("%Y-%m-%d")
    upcoming_games = fetch_section("Upcoming", {"dates": f"{start_up},{end_up}", "ordering": "-added"}, 100)

    with open("daily_games.json", "w") as f:
        json.dump({"NewReleases": new_games, "Upcoming": upcoming_games}, f, indent=2)

if __name__ == "__main__":
    main()