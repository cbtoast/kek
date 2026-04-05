import requests
import pandas as pd
import time
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- CONFIGURATION ---
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://polymarket.com/"
}

def get_top_traders():
    print("🚀 Identifying top 2% of monthly earners...")
    url = "https://api.polymarket.com/profile/leaderboard?period=month&limit=100"
    
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        if response.status_code != 200:
            print(f"❌ Leaderboard Error: {response.status_code}. Response: {response.text[:100]}")
            return []
        
        data = response.json()
        users = data.get('data', [])
        # Extract the proxy wallets of the top traders
        return [u['proxyWallet'] for u in users if 'proxyWallet' in u]
    except Exception as e:
        print(f"❌ Critical error in get_top_traders: {e}")
        return []

def get_user_positions(address):
    # Using the 2026 Data API endpoint
    url = f"https://data-api.polymarket.com/positions?user={address}"
    try:
        resp = requests.get(url, headers=HEADERS, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        return []
    except:
        return []

def update_sheets(data_frame):
    if data_frame.empty:
        print("⚠️ No data to write to Google Sheets.")
        return

    print("Writing to Google Sheets...")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    
    try:
        creds_dict = json.loads(os.environ.get('GOOGLE_SHEETS_JSON'))
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        # Ensure this matches your Sheet title exactly
        sheet = client.open("Polymarket Whale Tracker").sheet1 
        sheet.clear()
        
        content = [data_frame.columns.values.tolist()] + data_frame.values.tolist()
        sheet.update(content)
        print("✅ Google Sheet updated successfully!")
    except Exception as e:
        print(f"❌ Google Sheets Error: {e}")

def main():
    top_wallets = get_top_traders()
    if not top_wallets:
        print("Stopped: Could not retrieve top traders.")
        return

    all_bets = []
    print(f"Scanning {len(top_wallets)} wallets...")

    for addr in top_wallets:
        positions = get_user_positions(addr)
        for p in positions:
            if float(p.get('size', 0)) > 0:
                all_bets.append({
                    'Market': p.get('title', 'Unknown'),
                    'Outcome': p.get('outcome', 'Unknown'),
                    'Wallet': addr
                })
        time.sleep(0.5) # Crucial to avoid 2026 rate limits

    if not all_bets:
        print("No active positions found for these users.")
        return

    df = pd.DataFrame(all_bets)
    # Calculate consensus
    summary = df.groupby(['Market', 'Outcome']).size().reset_index(name='Top_User_Count')
    summary['Consensus_Pct'] = (summary['Top_User_Count'] / len(top_wallets) * 100).round(1)
    
    final_list = summary.sort_values(by='Consensus_Pct', ascending=False).head(20)
    update_sheets(final_list)

if __name__ == "__main__":
    main()
