import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import io

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
    limit = st.number_input("Card Limit", value=5, min_value=1)

if st.button("🚀 Run Scraper"):
    if not auth_token:
        st.error("Please provide a token!")
        st.stop()

    with st.status("Fetching Data...") as status:
        # 1. Fetch Cards
        headers = {'authorization': f"Bearer {auth_token}" if "Bearer" not in auth_token else auth_token}
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                           params={'index': 'collectioncards', 'limit': limit, 'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'})
        
        cards = res.json().get('hits', [])
        
        # 2. Fetch Sales
        with ThreadPoolExecutor(max_workers=1) as exe:
            sales_results = list(exe.map(lambda c: fetch_sales(auth_token, c), cards))
        
        for i, s in enumerate(sales_results):
            cards[i].update(s)

        # 3. Create THE FULL DATAFRAME (Everything)
        df_full = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        df_full.insert(0, 'Scrape Date', scrape_date)
        if 'collectionCardId' in df_full.columns:
            df_full.insert(1, 'Card Unique URL', df_full['collectionCardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true"))

        # 4. Create THE FILTERED DATAFRAME (Only specific columns)
        TARGET_COLS = ['Scrape Date', 'Card Unique URL', 'label', 'condition', 'variation', 'player', 'currentValue', 'avg_last_3_sales', 'total_sales_in_db']
        # We use reindex to handle cases where a column might be missing from the API
        df_filtered = df_full.reindex(columns=TARGET_COLS).fillna('')

        # 5. Sync FILTERED to Google Sheets
        status.write("📝 Syncing Filtered Data to Google Sheets...")
        client = get_gspread_client()
        if client:
            try:
                ws = client.open_by_key(SPREADSHEET_ID).sheet1
                ws.clear()
                clean_list = [df_filtered.columns.tolist()] + df_filtered.astype(str).values.tolist()
                ws.update(clean_list, value_input_option='USER_ENTERED')
                st.success("✅ Google Sheets Updated!")
            except Exception as e:
                st.error(f"Sheet Error: {e}")

        status.update(label="All Data Processed!", state="complete")

    # --- DOWNLOAD SECTION ---
    st.divider()
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Filtered Data")
        st.write("Columns for Google Sheets")
        st.dataframe(df_filtered, height=300)
        
        buf_f = io.BytesIO()
        with pd.ExcelWriter(buf_f, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False)
        st.download_button("📥 Download Filtered Excel", buf_f.getvalue(), f"Filtered_Cards_{scrape_date}.xlsx")

    with col2:
        st.subheader("Full Data")
        st.write("All available API data")
        st.dataframe(df_full, height=300)
        
        buf_full = io.BytesIO()
        with pd.ExcelWriter(buf_full, engine='openpyxl') as writer:
            df_full.to_excel(writer, index=False)
        st.download_button("📥 Download FULL Excel", buf_full.getvalue(), f"Full_Cards_{scrape_date}.xlsx")
