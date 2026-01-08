import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import io
import time

# ==================== GOOGLE SHEETS CONFIG ====================
def get_gspread_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds_dict = {
            "type": "service_account",
            "project_id": "cardladder",
            "private_key_id": "3e910525914e6d6fd55c9d3c08f275e755f004a0",
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace("\\n", "\n"),
            "client_email": "cardladder@cardladder.iam.gserviceaccount.com",
            "client_id": "100678312403939380954",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/web/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/cardladder%40cardladder.iam.gserviceaccount.com"
        }
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google Auth Error: {e}")
        return None

SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

# ==================== DATA LOGIC ====================
def fetch_sales(token, card):
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    label = card.get('label', '')
    res_data = {}
    try:
        params = {'index': 'salesarchive', 'query': label, 'limit': 3, 'sort': 'date', 'direction': 'desc'}
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', [])
            res_data['total_sales_in_db'] = data.get('totalHits', 0)
            prices = [h.get('price') for h in hits if h.get('price')]
            for i in range(3):
                res_data[f'sale{i+1}_price'] = prices[i] if i < len(prices) else None
            if prices:
                res_data['avg_last_3_sales'] = round(sum(prices)/len(prices), 2)
    except: pass
    return res_data

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Card Ladder Scraper", layout="wide")
st.title("📊 Card Data Scraper")

with st.sidebar:
    st.header("Settings")
    auth_token = st.text_input("Enter Bearer Token", type="password")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    scrape_all = st.checkbox("Scrape ALL Cards", value=False)
    if not scrape_all:
        limit = st.number_input("Card Limit", value=5, min_value=1)
    else:
        st.info("Scraping all items. This may take a while.")
        limit = 99999

if st.button("🚀 Run Scraper"):
    if not auth_token:
        st.error("Please provide a token!")
        st.stop()

    all_cards = []
    
    with st.status("Processing...") as status:
        # --- 1. FETCH CARDS ---
        status.write("📂 Accessing Collection...")
        progress_bar = st.progress(0) # Start progress bar
        
        headers = {'authorization': f"Bearer {auth_token}" if "Bearer" not in auth_token else auth_token}
        page = 0
        limit_per_request = 50 
        
        while True:
            params = {
                'index': 'collectioncards', 
                'limit': limit_per_request, 
                'page': page,
                'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'
            }
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
            
            if res.status_code != 200: break
            
            data = res.json()
            hits = data.get('hits', [])
            total_available = data.get('totalHits', 0)
            
            all_cards.extend(hits)
            
            # Update Progress Bar for Cards
            current_progress = min(len(all_cards) / total_available, 1.0) if total_available > 0 else 1.0
            progress_bar.progress(current_progress, text=f"Collected {len(all_cards)} of {total_available} cards")

            if len(all_cards) >= total_available or len(all_cards) >= limit or not hits:
                break
            
            page += 1
            time.sleep(0.3)

        cards = all_cards[:limit]
        progress_bar.empty() # Clear the first progress bar

        # --- 2. FETCH SALES (With Progress) ---
        status.write("📈 Fetching Sales History...")
        sales_progress = st.progress(0)
        
        sales_results = []
        total_cards = len(cards)
        
        # We loop manually to update the progress bar for each card
        for i, card in enumerate(cards):
            result = fetch_sales(auth_token, card)
            sales_results.append(result)
            
            # Update Sales Progress Bar
            p_val = (i + 1) / total_cards
            sales_progress.progress(p_val, text=f"Processing Card {i+1} of {total_cards}: {card.get('label', 'Unknown')}")

        for i, s in enumerate(sales_results):
            cards[i].update(s)
        
        sales_progress.empty() # Clear

        # --- 3. DATAFRAMES ---
        df_full = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        df_full.insert(0, 'Scrape Date', scrape_date)
        if 'collectionCardId' in df_full.columns:
            df_full.insert(1, 'Card Unique URL', df_full['collectionCardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true"))

        TARGET_COLS = ['Scrape Date', 'Card Unique URL', 'label', 'condition', 'variation', 'player', 'currentValue', 'avg_last_3_sales', 'total_sales_in_db']
        df_filtered = df_full.reindex(columns=TARGET_COLS).fillna('')

        # --- 4. SYNC TO GOOGLE ---
        status.write("📝 Syncing to Google Sheets...")
        client = get_gspread_client()
        if client:
            try:
                ws = client.open_by_key(SPREADSHEET_ID).sheet1
                ws.clear()
                clean_list = [df_filtered.columns.tolist()] + df_filtered.astype(str).values.tolist()
                ws.update(clean_list, value_input_option='USER_ENTERED')
                st.success(f"✅ Google Sheets Updated with {len(df_filtered)} cards!")
            except Exception as e:
                st.error(f"Sheet Error: {e}")

        status.update(label="All Data Processed!", state="complete")

    # --- DOWNLOADS ---
    st.divider()
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Filtered Data")
        st.dataframe(df_filtered, height=300)
        buf_f = io.BytesIO()
        with pd.ExcelWriter(buf_f, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False)
        st.download_button("📥 Download Filtered Excel", buf_f.getvalue(), f"Filtered_{scrape_date}.xlsx")

    with col2:
        st.subheader("Full Data")
        st.dataframe(df_full, height=300)
        buf_full = io.BytesIO()
        with pd.ExcelWriter(buf_full, engine='openpyxl') as writer:
            df_full.to_excel(writer, index=False)
        st.download_button("📥 Download FULL Excel", buf_full.getvalue(), f"Full_Cards_{scrape_date}.xlsx")
