import requests
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
