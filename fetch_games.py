import os
import requests
import json
import time
from datetime import datetime, timedelta

API_KEY = os.environ["RAWG_API_KEY"]

def get_trailer(game_id):
    """Try to get the Official 4K Trailer"""
    try:
        url = f"https://api.rawg.io/api/games/{game_id}/movies"
        response = requests.get(url, params={"key": API_KEY})
        if response.status_code == 200:
            data = response.json()
            if data.get("results"):
                return data["results"][0].get("data", {}).get("max", "")
    except:
        pass
    return ""

def get_clip_fallback(game):
    """Robust Clip Finder: Checks all resolution folders"""
    clip_obj = game.get("clip")
    if not clip_obj:
        return ""
    
    # 1. Try direct string
    if clip_obj.get("clip"):
        return clip_obj.get("clip")
        
    # 2. Deep Search (Fixes the missing video bug)
    clips = clip_obj.get("clips", {})
    if clips:
        return clips.get("640") or clips.get("320") or clips.get("full") or ""
        
    return ""

def process_game(game, deep_fetch=False):
    specs = {"Min": "TBA", "Rec": "TBA"}
    if game.get("platforms"):
        for p in game.get("platforms"):
            if p.get("platform", {}).get("slug") == "pc":
                raw = p.get("requirements") or p.get("requirements_en") or {}
                specs["Min"] = raw.get("minimum", "TBA")
                specs["Rec"] = raw.get("recommended", "TBA")
                break

    video_url = ""
    if deep_fetch:
        video_url = get_trailer(game.get("id"))
    
    # Fallback to robust finder if trailer fails
    if not video_url:
        video_url = get_clip_fallback(game)

    return {
        "Title": game.get("name"),
        "ReleaseDate": game.get("released"),
        "ImageURL": game.get("background_image"),
        "StoreURL": f"https://rawg.io/games/{game.get('slug')}",
        "VideoURL": video_url,
        "Rating": game.get("metacritic"),
        "Popularity": game.get("added", 0),
        "Genres": [g.get("name") for g in game.get("genres", [])],
        "Specs": specs
    }

def fetch_section(name, params, limit, deep_limit):
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
            is_top = len(results) < deep_limit
            results.append(process_game(g, deep_fetch=is_top))
            if is_top: time.sleep(0.2)
        url = data.get("next")
    return results

def main():
    today = datetime.now().date()
    
    # 1. NEW RELEASES
    start_new = (today - timedelta(days=30)).strftime("%Y-%m-%d")
    end_new = today.strftime("%Y-%m-%d")
    new_games = fetch_section("NewReleases", {"dates": f"{start_new},{end_new}", "ordering": "-added"}, 60, 10)

    # 2. UPCOMING
    start_up = (today + timedelta(days=1)).strftime("%Y-%m-%d")
    end_up = (today + timedelta(days=60)).strftime("%Y-%m-%d")
    upcoming_games = fetch_section("Upcoming", {"dates": f"{start_up},{end_up}", "ordering": "-added"}, 100, 15)

    with open("daily_games.json", "w") as f:
        json.dump({"NewReleases": new_games, "Upcoming": upcoming_games}, f, indent=2)

if __name__ == "__main__":
    main()