import os
import requests
import json
import time

API_KEY = os.environ["RAWG_API_KEY"]

def get_trailer(game_id):
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

def process_game(game):
    specs = {"Min": "TBA", "Rec": "TBA"}
    if game.get("platforms"):
        for p in game.get("platforms"):
            if p.get("platform", {}).get("slug") == "pc":
                raw = p.get("requirements") or p.get("requirements_en") or {}
                specs["Min"] = raw.get("minimum", "TBA")
                specs["Rec"] = raw.get("recommended", "TBA")
                break
    
    video_url = get_trailer(game.get("id"))
    if not video_url and game.get("clip"):
        video_url = game.get("clip", {}).get("clip", "")

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
    print("--- Starting Monthly Deep Fetch (Top 100) ---")
    all_games = []
    url = "https://api.rawg.io/api/games"
    params = {
        "key": API_KEY, "parent_platforms": "1", "ordering": "-metacritic",
        "metacritic": "85,100", "page_size": 25
    }
    
    while url and len(all_games) < 100:
        if url == "https://api.rawg.io/api/games":
            resp = requests.get(url, params=params)
        else:
            resp = requests.get(url) 
        data = resp.json()
        for g in data.get("results", []):
            all_games.append(process_game(g))
            time.sleep(0.1)
        url = data.get("next")
        
    with open("top_games.json", "w") as f:
        json.dump(all_games, f, indent=2)

if __name__ == "__main__":
    main()