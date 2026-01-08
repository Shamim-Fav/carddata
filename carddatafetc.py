import streamlit as st
import requests
import pandas as pd
import gspread
import time
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==================== SETTINGS ====================
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

def get_gspread_client():
    """Builds credentials from Streamlit Secrets with strict key cleaning"""
    try:
        s = st.secrets["gcp_service_account"]
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
        st.error(f"Authentication Setup Failed: {e}")
        return None

def fetch_sales_for_card(token, card_data):
    """Fetches last 3 sales for a single card (Your Core Logic)"""
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    label = card_data.get('label', '')
    
    params = {
        'index': 'salesarchive',
        'query': label,
        'page': 0,
        'limit': 3,
        'sort': 'date',
        'direction': 'desc'
    }
    
    try:
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
        if res.status_code == 200:
            hits = res.json().get('hits', [])
            prices = [h.get('price') for h in hits if h.get('price')]
            avg = round(sum(prices)/len(prices), 2) if prices else 0
            return {'avg_last_3_sales': avg, 'total_sales_in_db': res.json().get('totalHits', 0)}
    except:
        pass
    return {'avg_last_3_sales': 0, 'total_sales_in_db': 0}

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Card Ladder Pro Scraper", layout="wide")
st.title("🚀 Card Ladder ⮕ Google Sheets")

with st.sidebar:
    st.header("1. Authentication")
    token = st.text_area("Bearer Token")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    limit = st.number_input("Card Limit", min_value=1, value=25)
    
    st.header("2. Processing")
    threads = st.slider("Threads (Speed)", 1, 10, 3)

if st.button("Start Scrape & Sync"):
    if not token:
        st.warning("Please enter your Bearer Token.")
    else:
        # --- PHASE 1: FETCH COLLECTION ---
        with st.status("Fetching Collection...") as status:
            headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
            params = {'index': 'collectioncards', 'page': 0, 'limit': limit, 'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'}
            
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
            if res.status_code != 200:
                st.error(f"Card Ladder API Error: {res.status_code}")
                st.stop()
            
            cards = res.json().get('hits', [])
            st.write(f"✅ Found {len(cards)} cards.")

            # --- PHASE 2: FETCH SALES (MULTI-THREADED) ---
            st.write("Fetching sales data...")
            with ThreadPoolExecutor(max_workers=threads) as executor:
                results = list(executor.map(lambda c: fetch_sales_for_card(token, c), cards))
            
            for i, result in enumerate(results):
                cards[i].update(result)
            
            # --- PHASE 3: PROCESS DATAFRAME ---
            df = pd.json_normalize(cards)
            
            # Add Your Custom Columns
            scrape_date = datetime.now().strftime("%Y-%m-%d")
            df.insert(0, 'Scrape Date', scrape_date)
            
            if 'collectionCardId' in df.columns:
                df.insert(1, 'Card Unique URL', df['collectionCardId'].apply(
                    lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true" if pd.notna(x) else ""
                ))

            # CLEAN DATA FOR GOOGLE SHEETS (Your "SIMPLE VERSION" Method)
            df_clean = df.copy()
            for col in df_clean.columns:
                # Fill NaNs
                df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), "")
                # Force everything to string to handle list_value errors
                df_clean[col] = df_clean[col].astype(str)

            # --- PHASE 4: UPLOAD TO GOOGLE SHEETS ---
            status.update(label="Uploading to Google Sheets...", state="running")
            client = get_gspread_client()
            if client:
                try:
                    sh = client.open_by_key(SPREADSHEET_ID)
                    ws = sh.get_worksheet(0)
                    ws.clear()
                    
                    # Prepare list format
                    payload = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
                    ws.update(payload, value_input_option='USER_ENTERED')
                    
                    status.update(label="Sync Complete!", state="complete")
                    st.balloons()
                    st.success("✅ Data saved to Google Sheets!")
                    st.dataframe(df_clean.head())
                except Exception as e:
                    st.error(f"Sheets Error: {e}")
