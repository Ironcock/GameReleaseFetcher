import requests
import json
import datetime
from datetime import timedelta
import os

# CONFIGURATION
API_KEY = os.environ.get("RAWG_API_KEY") 
BASE_URL = "https://api.rawg.io/api/games"
PC_PARENT_PLATFORM_ID = 1

# FILTER LISTS
BLACKLIST = ['nsfw', 'erotica', 'hentai', 'porn', 'uncensored', 'sex']
CONDITIONAL = ['nudity', 'sexual-content', 'adult'] 

def get_date_range(days_back=0, days_forward=0):
    today = datetime.date.today()
    start = today - timedelta(days=days_back)
    end = today + timedelta(days=days_forward)
    return f"{start},{end}"

def diagnose():
    print("--- DIAGNOSTIC MODE (CRASH FIX APPLIED) ---")
    
    dates = get_date_range(days_back=30, days_forward=0)
    print(f"1. Querying Date Range: {dates}")
    
    params = {
        "key": API_KEY,
        "page_size": 20, 
        "page": 1,
        "dates": dates,
        "ordering": "-released",
        "parent_platforms": PC_PARENT_PLATFORM_ID
    }

    try:
        print("2. Sending Request...")
        response = requests.get(BASE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [])
        
        print(f"3. Games Found: {len(results)}")
        
        if not results:
            print("   [ERROR] 0 results found.")
            return

        print("\n--- ANALYZING GAMES ---")
        for game in results:
            # --- THE FIX IS HERE ---
            # We safely handle if 'tags' is None/Null
            raw_tags = game.get('tags')
            if raw_tags:
                tags = [t['slug'] for t in raw_tags]
            else:
                tags = [] # Empty list if null
            
            print(f"GAME: {game['name']} (Added: {game.get('added', 0)})")
            
            # LOGIC TEST
            status = "ACCEPTED"
            reason = "Valid"
            
            if any(tag in BLACKLIST for tag in tags):
                status = "REJECTED"
                reason = "Hard Ban Tag"
            elif any(tag in CONDITIONAL for tag in tags):
                if game.get('added', 0) < 10:
                    status = "REJECTED"
                    reason = "Risky Tag + Low Added Count"
            
            print(f"   > RESULT: {status} ({reason})")
            print("-" * 30)
            
        print("\n[SUCCESS] Script finished without crashing!")

    except Exception as e:
        print(f"\n[CRASH] Still crashing: {e}")

if __name__ == "__main__":
    diagnose()