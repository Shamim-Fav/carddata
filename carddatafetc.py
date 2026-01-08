import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==================== CONFIGURATION ====================
# Using the new keys you provided
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

def get_gspread_client():
    try:
        s = st.secrets["gcp_service_account"]
        # Handle newline characters in the private key
        clean_key = s["private_key"].replace("\\n", "\n").strip()
        
        creds_dict = {
            "type": "service_account",
            "project_id": s["project_id"],
            "private_key_id": s["private_key_id"],
            "private_key": clean_key,
            "client_email": s["client_email"],
            "client_id": s["client_id"],
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google Auth Error: {e}")
        return None

def fetch_sales(token, card):
    """Fetches the last 3 sales and calculates average"""
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    label = card.get('label', '')
    
    sales_data = {
        'avg_last_3_sales': 0,
        'total_sales_in_db': 0,
        'sale1_price': None,
        'sale2_price': None,
        'sale3_price': None
    }
    
    try:
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                           headers=headers, 
                           params={'index': 'salesarchive', 'query': label, 'limit': 3, 'sort': 'date', 'direction': 'desc'},
                           timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', [])
            sales_data['total_sales_in_db'] = data.get('totalHits', 0)
            
            prices = []
            for i, hit in enumerate(hits):
                price = hit.get('price')
                if price:
                    prices.append(price)
                    sales_data[f'sale{i+1}_price'] = price
            
            if prices:
                sales_data['avg_last_3_sales'] = round(sum(prices) / len(prices), 2)
                
    except Exception as e:
        pass
    return sales_data

# ==================== STREAMLIT INTERFACE ====================
st.set_page_config(page_title="Card Ladder Pro Scraper", layout="wide")
st.title("📦 Card Ladder to Google Sheets & Excel")

with st.sidebar:
    st.header("Settings")
    token = st.text_area("Bearer Token")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    limit = st.number_input("Card Limit", value=50)
    threads = st.slider("Threads (Speed)", 1, 10, 5)

if st.button("🚀 Run Complete Process"):
    if not token:
        st.error("Please provide a Bearer Token")
    else:
        with st.status("Processing...") as status:
            # 1. Fetch Collection
            status.write("📡 Fetching collection cards...")
            headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                               params={'index': 'collectioncards', 'limit': limit, 'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'})
            
            if res.status_code != 200:
                st.error(f"Failed to fetch collection: {res.text}")
                st.stop()

            cards = res.json().get('hits', [])
            status.write(f"✅ Found {len(cards)} cards.")

            # 2. Fetch Sales (Multi-threaded)
            status.write("📊 Fetching sales for each card...")
            with ThreadPoolExecutor(max_workers=threads) as exe:
                sales_results = list(exe.map(lambda c: fetch_sales(token, c), cards))
            
            for i, s in enumerate(sales_results): 
                cards[i].update(s)

            # 3. Process DataFrame (Excel Logic)
            df = pd.json_normalize(cards)
            
            # Add Custom Columns
            scrape_date = datetime.now().strftime("%Y-%m-%d")
            df.insert(0, 'Scrape Date', scrape_date)
            
            if 'collectionCardId' in df.columns:
                df.insert(1, 'Card Unique URL', df['collectionCardId'].apply(
                    lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true" if pd.notna(x) else ""
                ))
            else:
                df.insert(1, 'Card Unique URL', "")

            # 4. Create Filtered Data (Matching your original Excel requirement)
            filter_cols = ['Scrape Date', 'Card Unique URL', 'label', 'condition', 'variation', 'player', 'currentValue', 'avg_last_3_sales', 'total_sales_in_db', 'sale1_price', 'sale2_price', 'sale3_price']
            # Only keep columns that actually exist in the data
            existing_cols = [c for c in filter_cols if c in df.columns]
            df_filtered = df[existing_cols].copy()

            # 5. DATA CLEANING (SIMPLE VERSION - Fixes Google Sheets 400 Error)
            # This handles nested lists/objects by converting them to strings
            df_sheets = df_filtered.copy()
            for col in df_sheets.columns:
                df_sheets[col] = df_sheets[col].where(pd.notnull(df_sheets[col]), "")
                df_sheets[col] = df_sheets[col].astype(str)

            # 6. Upload to Google Sheets
            status.write("📝 Updating Google Sheet...")
            client = get_gspread_client()
            if client:
                sh = client.open_by_key(SPREADSHEET_ID)
                ws = sh.get_worksheet(0)
                ws.clear()
                
                payload = [df_sheets.columns.values.tolist()] + df_sheets.values.tolist()
                ws.update(payload, value_input_option='USER_ENTERED')
                
                # Format Header
                ws.format('A1:Z1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})
                
                status.update(label="Process Complete!", state="complete")
                st.balloons()
                st.success("Google Sheet and Data Processing Successful!")
                st.dataframe(df_filtered.head())
            
            # 7. Provide Excel Download
            csv = df_filtered.to_csv(index=False).encode('utf-8')
            st.download_button("Download Filtered Data as CSV", csv, f"card_ladder_{scrape_date}.csv", "text/csv")
