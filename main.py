import requests
import pandas as pd
import time
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- STEP 1: THE SCRAPER ---
def get_top_traders():
    url = "https://api.polymarket.com/profile/leaderboard?period=month&limit=500"
    
    # This 'header' makes your script look like a Chrome browser
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
        "Accept": "application/json"
    }
    
    response = requests.get(url, headers=headers)
    
    # If the site blocks us, we want to know why instead of crashing
    if response.status_code != 200:
        print(f"❌ API Error: Status {response.status_code}. The site might be blocking the script temporarily.")
        return []

    try:
        users = response.json().get('data', [])
        top_count = max(int(len(users) * 0.02), 50)
        return [u['proxyWallet'] for u in users[:top_count]]
    except Exception as e:
        print(f"❌ Failed to parse JSON: {e}")
        return []
        
def get_user_positions(address):
    url = f"https://data-api.polymarket.com/positions?user={address}"
    try:
        resp = requests.get(url, timeout=5).json()
        return resp if isinstance(resp, list) else []
    except:
        return []

# --- STEP 2: THE GOOGLE SHEETS UPDATER ---
def update_sheets(data_frame):
    print("Writing to Google Sheets...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    # This pulls the JSON Secret from your GitHub Settings
    creds_dict = json.loads(os.environ.get('GOOGLE_SHEETS_JSON'))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)

    # Make sure this matches your Sheet title exactly!
    sheet = client.open("polymarketkek").sheet1 
    
    sheet.clear()
    # Prepare data: Header row + Data rows
    content = [data_frame.columns.values.tolist()] + data_frame.values.tolist()
    sheet.update(content)
    print("✅ Google Sheet updated successfully!")

# --- STEP 3: THE MAIN BRAIN ---
def main():
    print("🚀 Starting Polymarket Whale Tracker...")
    top_wallets = get_top_traders()
    all_bets = []
    
    for addr in top_wallets:
        positions = get_user_positions(addr)
        for p in positions:
            if float(p.get('size', 0)) > 0:
                all_bets.append({
                    'Market': p.get('title'),
                    'Outcome': p.get('outcome'),
                    'Count': 1 # Used for counting consensus
                })
        time.sleep(0.5)

    # Process data into a Top 20 list
    df = pd.DataFrame(all_bets)
    summary = df.groupby(['Market', 'Outcome']).size().reset_index(name='Top_User_Count')
    summary['Consensus_Pct'] = (summary['Top_User_Count'] / len(top_wallets) * 100).round(1)
    
    final_list = summary.sort_values(by='Consensus_Pct', ascending=False).head(20)

    # FINAL STEP: Send the results to Google
    update_sheets(final_list)

if __name__ == "__main__":
    main()import requests
import pandas as pd
import time


TOP_PERCENT = 0.02  
MIN_USERS = 50      

def get_top_traders():
    """Fetches the monthly leaderboard and returns the top 2% of addresses."""
   
    url = "https://api.polymarket.com/profile/leaderboard?period=month&limit=500"
    response = requests.get(url).json()
    
    users = response.get('data', [])
    top_count = max(int(len(users) * TOP_PERCENT), MIN_USERS)
    return [u['proxyWallet'] for u in users[:top_count]]

def get_user_positions(address):
    """Gets all active bets for a specific wallet."""
    url = f"https://data-api.polymarket.com/positions?user={address}"
    try:
        
        resp = requests.get(url, timeout=5).json()
        return resp if isinstance(resp, list) else []
    except:
        return []

def main():
    print("🚀 Identifying top 2% of monthly earners...")
    top_wallets = get_top_traders()
    total_scanned = len(top_wallets)
    
    all_bets = []
    
    print(f"Scanning {total_scanned} wallets... this may take a minute.")
    for addr in top_wallets:
        positions = get_user_positions(addr)
        for p in positions:
            
            if float(p.get('size', 0)) > 0:
                all_bets.append({
                    'market': p.get('conditionId'), 
                    'title': p.get('title'),       
                    'outcome': p.get('outcome')   
                })
        time.sleep(0.2) 

    
    df = pd.DataFrame(all_bets)
    
    
    summary = df.groupby(['title', 'outcome']).size().reset_index(name='count')
    summary['consensus_pct'] = (summary['count'] / total_scanned * 100).round(1)
    
    
    final_list = summary.sort_values(by='consensus_pct', ascending=False).head(20)
    
    print("\n--- TOP 20 CONSENSUS BETS BY WHALES ---")
    print(final_list[['consensus_pct', 'title', 'outcome']])



if __name__ == "__main__":
    main()
