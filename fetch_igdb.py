import requests
import json
import time
import os
import datetime

# --- CONFIGURATION ---
CLIENT_ID = os.environ.get("IGDB_CLIENT_ID")
CLIENT_SECRET = os.environ.get("IGDB_CLIENT_SECRET")

# Store IDs: 1=Steam, 26=Epic, 5=GOG
STORE_PRIORITY = [1, 26, 5] 
STORE_URLS = {
    1: "https://store.steampowered.com/app/{}",
    26: "https://store.epicgames.com/p/{}",
    5: "https://www.gog.com/game/{}"
}

def get_auth_token():
    url = f"https://id.twitch.tv/oauth2/token?client_id={CLIENT_ID}&client_secret={CLIENT_SECRET}&grant_type=client_credentials"
    try:
        res = requests.post(url)
        res.raise_for_status()
        return res.json()['access_token']
    except Exception as e:
        print(f"Auth failed: {e}")
        exit(1)

def resolve_store(game):
    """
    Finds the best store link (Steam > Epic > GOG).
    Checks: Game -> Version Parent -> Parent Game
    """
    potential_sources = []
    
    # 1. The game itself
    if "external_games" in game:
        potential_sources.append(game["external_games"])
    
    # 2. Version parent (e.g. GOTY Edition)
    if "version_parent" in game and "external_games" in game["version_parent"]:
        potential_sources.append(game["version_parent"]["external_games"])
        
    # 3. Parent game (e.g. Episode 1)
    if "parent_game" in game and "external_games" in game["parent_game"]:
        potential_sources.append(game["parent_game"]["external_games"])
    
    for store_id in STORE_PRIORITY:
        for source_list in potential_sources:
            # FIX: Check 'external_game_source' instead of 'category'
            match = next((item for item in source_list if item.get("external_game_source") == store_id), None)
            
            if match:
                # OPTION A: Build URL from UID (Cleaner)
                if "uid" in match:
                    base_url = STORE_URLS.get(store_id)
                    return base_url.format(match["uid"])
                
                # OPTION B: Use direct URL if IGDB provided it
                if "url" in match:
                    return match["url"]
    
    return ""

def fetch_from_igdb(token, query):
    url = "https://api.igdb.com/v4/games"
    headers = {
        'Client-ID': CLIENT_ID,
        'Authorization': f'Bearer {token}',
        'Content-Type': 'text/plain'
    }
    try:
        res = requests.post(url, headers=headers, data=query)
        res.raise_for_status()
        return res.json()
    except Exception as e:
        print(f"API Request Failed: {e}")
        return []

def map_game_to_json(game):
    # Image Resolution (Swap thumbnail for big cover)
    image_url = ""
    if "cover" in game and "url" in game["cover"]:
        image_url = "https:" + game["cover"]["url"].replace("t_thumb", "t_cover_big")
    
    # Screenshots
    screenshots = []
    if "screenshots" in game:
        for s in game["screenshots"][:10]:
            if "url" in s:
                screenshots.append("https:" + s["url"].replace("t_thumb", "t_screenshot_med"))

    # Date
    release_date = "TBA"
    if "first_release_date" in game:
        release_date = datetime.datetime.fromtimestamp(game["first_release_date"]).strftime('%Y-%m-%d')

    # Store Logic
    store_url = resolve_store(game)

    # Genres
    genres = [g['name'] for g in game.get('genres', [])]

    return {
        "ID": game["id"],
        "Title": game["name"],
        "ReleaseDate": release_date,
        "ImageURL": image_url,
        "StoreURL": store_url,
        "Metacritic": round(game.get("rating", 0)), 
        "AddedCount": game.get("hypes", 0),
        "Rating": game.get("rating", 0.0),
        "ShortScreenshots": screenshots,
        "Genres": genres[:3],
        "Tags": [],
        "Platforms": ["pc"]
    }

def main():
    print("--- IGDB FETCH START ---")
    token = get_auth_token()
    
    now = int(time.time())
    day_30_ago = now - (30 * 24 * 60 * 60)
    day_90_future = now + (90 * 24 * 60 * 60)
    year_20_ago = now - (20 * 365 * 24 * 60 * 60)

    # --- THE FIX: Use 'external_game_source' instead of 'category' ---
    fields_raw = """
        name, cover.url, screenshots.url, rating, rating_count, first_release_date, hypes, game_type, genres.name,
        external_games.external_game_source, external_games.uid, external_games.url,
        parent_game.external_games.external_game_source, parent_game.external_games.uid, parent_game.external_games.url,
        version_parent.external_games.external_game_source, version_parent.external_games.uid, version_parent.external_games.url
    """
    fields = fields_raw.replace("\n", "").replace(" ", "")

    # 1. HALL OF FAME
    print("Fetching Hall of Fame...")
    query_hof = f"fields {fields}; where cover != null & platforms = (6) & first_release_date >= {year_20_ago} & rating >= 80 & rating_count > 100 & parent_game = null & version_parent = null; sort rating desc; limit 150;"
    
    hof_raw = fetch_from_igdb(token, query_hof)
    hof_data = [map_game_to_json(g) for g in hof_raw]
    
    with open('top_games.json', 'w') as f:
        json.dump({"HallOfFame": hof_data}, f, indent=2)

    # 2. DAILY FEED
    daily_data = {}
    
    print("Fetching New Releases...")
    query_new = f"fields {fields}; where cover != null & first_release_date >= {day_30_ago} & first_release_date <= {now} & platforms = (6) & game_type = 0; sort hypes desc; limit 50;"
    new_raw = fetch_from_igdb(token, query_new)
    daily_data["NewReleases"] = [map_game_to_json(g) for g in new_raw]

    print("Fetching Upcoming...")
    query_upcoming = f"fields {fields}; where cover != null & first_release_date > {now} & first_release_date < {day_90_future} & platforms = (6) & game_type = 0; sort hypes desc; limit 50;"
    upcoming_raw = fetch_from_igdb(token, query_upcoming)
    daily_data["Upcoming"] = [map_game_to_json(g) for g in upcoming_raw]

    with open('daily_games.json', 'w') as f:
        json.dump(daily_data, f, indent=2)
        
    print("--- FETCH COMPLETE ---")

if __name__ == "__main__":
    main()