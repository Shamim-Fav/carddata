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
# We pull credentials from Streamlit Secrets for safety
def get_gspread_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        # You can either paste the dict here or use st.secrets for GitHub safety
        creds_dict = {
            "type": "service_account",
            "project_id": "cardladder",
            "private_key_id": "3e910525914e6d6fd55c9d3c08f275e755f004a0",
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace("\\n", "\n"),
            "client_email": "cardladder@cardladder.iam.gserviceaccount.com",
            "token_uri": "https://oauth2.googleapis.com/token",
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
    res_data = {'avg_last_3_sales': 0, 'total_sales_in_db': 0}
    
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

# ==================== STREAMLIT INTERFACE ====================
st.set_page_config(page_title="Card Ladder Scraper", layout="wide")
st.title("📦 Card Ladder Scraper (Streamlit Edition)")

with st.sidebar:
    st.header("Settings")
    auth_token = st.text_input("Enter Bearer Token", type="password")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    limit = st.number_input("Card Limit", value=5, min_value=1)
    threads = st.slider("Threads", 1, 10, 5)

if st.button("🚀 Start Complete Process"):
    if not auth_token:
        st.error("Please provide a token!")
        st.stop()

    with st.status("Running Scraper...", expanded=True) as status:
        # Phase 1: Fetch Collection
        st.write("🔍 Phase 1: Fetching cards from collection...")
        headers = {'authorization': f"Bearer {auth_token}" if "Bearer" not in auth_token else auth_token}
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                           params={'index': 'collectioncards', 'limit': limit, 'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'})
        
        if res.status_code != 200:
            st.error(f"API Error: {res.status_code}")
            st.stop()
        
        cards = res.json().get('hits', [])
        st.write(f"✅ Found {len(cards)} cards.")

        # Phase 2: Sales
        st.write("📊 Phase 2: Fetching sales history...")
        with ThreadPoolExecutor(max_workers=threads) as exe:
            sales_data = list(exe.map(lambda c: fetch_sales(auth_token, c), cards))
        
        for i, s in enumerate(sales_data):
            cards[i].update(s)

        # Phase 3: Processing & Filtering
        df = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        df.insert(0, 'Scrape Date', scrape_date)
        if 'collectionCardId' in df.columns:
            df.insert(1, 'Card Unique URL', df['collectionCardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true"))
        
        # This is your exact filtering logic
        TARGET_COLS = ['Scrape Date', 'Card Unique URL', 'label', 'condition', 'variation', 'player', 'currentValue', 'avg_last_3_sales', 'total_sales_in_db']
        df_filtered = df.reindex(columns=TARGET_COLS).fillna('')

        # Phase 4: Google Sheets Sync
        st.write("📝 Syncing to Google Sheets...")
        client = get_gspread_client()
        if client:
            ws = client.open_by_key(SPREADSHEET_ID).sheet1
            ws.clear()
            # Clean data for Sheets
            clean_list = [df_filtered.columns.tolist()] + df_filtered.astype(str).values.tolist()
            ws.update(clean_list, value_input_option='USER_ENTERED')
            st.success("✅ Google Sheets Updated!")

        status.update(label="Process Complete!", state="complete")

    # Final Display and Downloads
    st.divider()
    st.subheader("Data Preview")
    st.dataframe(df_filtered)

    # Download Buttons (Excel)
    col1, col2 = st.columns(2)
    
    # Filtered Excel
    buf_f = io.BytesIO()
    with pd.ExcelWriter(buf_f, engine='openpyxl') as writer:
        df_filtered.to_excel(writer, index=False)
    col1.download_button("📥 Download Filtered Excel", buf_f.getvalue(), f"Filtered_Cards_{scrape_date}.xlsx", "application/vnd.ms-excel")

    # Full Excel
    buf_full = io.BytesIO()
    with pd.ExcelWriter(buf_full, engine='openpyxl') as writer:
        df.to_excel(writer, index=False)
    col2.download_button("📥 Download Full Excel", buf_full.getvalue(), f"Full_Cards_{scrape_date}.xlsx", "application/vnd.ms-excel")
