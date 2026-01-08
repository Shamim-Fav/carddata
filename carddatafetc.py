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

def get_gspread_client():
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
        st.error(f"Auth Error: {e}")
        return None

def fetch_sales(token, card):
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    label = card.get('label', '')
    res_data = {
        'avg_last_3_sales': 0, 
        'total_sales_in_db': 0,
        'sale1_price': None, 'sale2_price': None, 'sale3_price': None
    }
    try:
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                           params={'index': 'salesarchive', 'query': label, 'limit': 3, 'sort': 'date', 'direction': 'desc'})
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', [])
            res_data['total_sales_in_db'] = data.get('totalHits', 0)
            prices = [h.get('price') for h in hits if h.get('price')]
            for i, p in enumerate(prices[:3]):
                res_data[f'sale{i+1}_price'] = p
            if prices:
                res_data['avg_last_3_sales'] = round(sum(prices)/len(prices), 2)
    except: pass
    return res_data

# ==================== INTERFACE ====================
st.set_page_config(page_title="Card Ladder Pro Scraper", layout="wide")
st.title("📊 Card Ladder Scraper (Excel & Sheets)")

with st.sidebar:
    token = st.text_area("Bearer Token")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    limit = st.number_input("Limit", value=20)
    threads = st.slider("Threads", 1, 10, 5)

if st.button("🚀 Run Complete Process"):
    if not token:
        st.error("Missing Token")
    else:
        with st.status("Processing...") as status:
            # 1. Fetch Collection
            headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                               params={'index': 'collectioncards', 'limit': limit, 'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'})
            cards = res.json().get('hits', [])
            
            # 2. Fetch Sales
            with ThreadPoolExecutor(max_workers=threads) as exe:
                sales_results = list(exe.map(lambda c: fetch_sales(token, c), cards))
            for i, s in enumerate(sales_results): cards[i].update(s)

            # 3. Create Full Dataframe
            df_full = pd.json_normalize(cards)
            scrape_date = datetime.now().strftime("%Y-%m-%d")
            df_full.insert(0, 'Scrape Date', scrape_date)
            if 'collectionCardId' in df_full.columns:
                df_full.insert(1, 'Card Unique URL', df_full['collectionCardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true"))

            # 4. Create Filtered Dataframe
            filter_cols = ['Scrape Date', 'Card Unique URL', 'label', 'condition', 'variation', 'player', 'currentValue', 'avg_last_3_sales', 'total_sales_in_db']
            available = [c for c in filter_cols if c in df_full.columns]
            df_filtered = df_full[available].copy()

            # 5. Save to Google Sheets (Cleaned for Sheets)
            client = get_gspread_client()
            if client:
                df_sheets = df_filtered.copy().astype(str)
                ws = client.open_by_key(SPREADSHEET_ID).get_worksheet(0)
                ws.clear()
                ws.update([df_sheets.columns.values.tolist()] + df_sheets.values.tolist(), value_input_option='USER_ENTERED')
                ws.format('A1:Z1', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})

            status.update(label="Complete!", state="complete")

            # 6. DOWNLOAD BUTTONS (EXCEL)
            col1, col2 = st.columns(2)
            
            # Full Excel
            buffer_full = io.BytesIO()
            with pd.ExcelWriter(buffer_full, engine='xlsxwriter') as writer:
                df_full.to_excel(writer, index=False)
            col1.download_button("📥 Download Full Excel", buffer_full.getvalue(), f"Cardladder_Full_{scrape_date}.xlsx")

            # Filtered Excel
            buffer_filt = io.BytesIO()
            with pd.ExcelWriter(buffer_filt, engine='xlsxwriter') as writer:
                df_filtered.to_excel(writer, index=False)
            col2.download_button("📥 Download Filtered Excel", buffer_filt.getvalue(), f"Filter_Cardladder_{scrape_date}.xlsx")

            st.success("Process successful! Files ready below.")
            st.write("### Filtered Data Preview")
            st.dataframe(df_filtered.head())
