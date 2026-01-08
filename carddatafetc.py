import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import io

# ==================== CONFIGURATION ====================
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

# Define the exact columns you want for the Filtered output
TARGET_COLS = [
    'Scrape Date', 'Card Unique URL', 'label', 'condition', 
    'variation', 'player', 'currentValue', 'avg_last_3_sales', 
    'total_sales_in_db', 'sale1_price', 'sale2_price', 'sale3_price'
]

# ==================== GOOGLE SHEETS AUTH ====================
@st.cache_resource
def get_gspread_client():
    try:
        # If running locally, this uses your GOOGLE_CREDENTIALS dict
        # If on Streamlit Cloud, use st.secrets
        creds_dict = {
            "type": "service_account",
            "project_id": "cardladder",
            "private_key_id": "3e910525914e6d6fd55c9d3c08f275e755f004a0",
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace("\\n", "\n"),
            "client_email": "cardladder@cardladder.iam.gserviceaccount.com",
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google Auth Error: {e}")
        return None

# ==================== LOGIC FUNCTIONS ====================
def fetch_sales(token, card):
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    label = card.get('label', '')
    res_data = {
        'avg_last_3_sales': 0, 
        'total_sales_in_db': 0,
        'sale1_price': None, 'sale2_price': None, 'sale3_price': None
    }
    try:
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                           headers=headers, 
                           params={'index': 'salesarchive', 'query': label, 'limit': 3, 'sort': 'date', 'direction': 'desc'},
                           timeout=10)
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', [])
            res_data['total_sales_in_db'] = data.get('totalHits', 0)
            prices = [h.get('price') for h in hits if h.get('price')]
            for i in range(3):
                if i < len(prices):
                    res_data[f'sale{i+1}_price'] = prices[i]
            if prices:
                res_data['avg_last_3_sales'] = round(sum(prices)/len(prices), 2)
    except: pass
    return res_data

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Card Ladder Sync", layout="wide")
st.title("📊 Card Ladder Scraper & Sheet Sync")

with st.sidebar:
    st.header("Settings")
    token = st.text_input("Bearer Token", type="password")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    limit = st.number_input("Card Limit", value=20, min_value=1)
    threads = st.slider("Thread Speed", 1, 10, 5)

if st.button("🚀 Run Complete Process", type="primary"):
    if not token:
        st.warning("Please enter your Bearer Token in the sidebar.")
        st.stop()

    with st.status("Initializing Scraper...") as status:
        # 1. Fetch Collection
        headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                           params={'index': 'collectioncards', 'limit': limit, 'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'})
        
        if res.status_code != 200:
            st.error(f"API Connection Failed: {res.status_code}")
            st.stop()
        
        cards = res.json().get('hits', [])
        status.write(f"✅ Found {len(cards)} cards. Fetching sales data...")

        # 2. Parallel Sales Fetching
        with ThreadPoolExecutor(max_workers=threads) as exe:
            sales_results = list(exe.map(lambda c: fetch_sales(token, c), cards))
        
        for i, s in enumerate(sales_results): 
            cards[i].update(s)

        # 3. Data Processing
        df_raw = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        
        # Insert Date and URL
        df_raw.insert(0, 'Scrape Date', scrape_date)
        if 'collectionCardId' in df_raw.columns:
            df_raw.insert(1, 'Card Unique URL', df_raw['collectionCardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true"))
        
        # Apply strict column filtering
        df_filtered = df_raw.reindex(columns=TARGET_COLS).fillna('')

        # 4. Sync to Google Sheets
        status.write("📝 Syncing to Google Sheets...")
        client = get_gspread_client()
        if client:
            try:
                ws = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
                ws.clear()
                sheet_data = [df_filtered.columns.values.tolist()] + df_filtered.values.tolist()
                ws.update(sheet_data, value_input_option='USER_ENTERED')
                status.write("✅ Google Sheets Sync Complete!")
            except Exception as e:
                st.error(f"Sheet Sync Failed: {e}")

        status.update(label="All Tasks Finished!", state="complete")

        # 5. Display & Download
        st.subheader("Results Preview")
        st.dataframe(df_filtered, use_container_width=True)

        # Create Excel Download
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False)
        
        st.download_button(
            label="📥 Download Filtered Excel",
            data=buf.getvalue(),
            file_name=f"CardLadder_Scrape_{scrape_date}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
