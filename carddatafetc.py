import streamlit as st
import requests
import pandas as pd
import io
import json
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Card Ladder Scraper (Read-Only Google Sheet)",
    page_icon="📦",
    layout="wide"
)

# ==================== SESSION STATE ====================
if 'collection_data' not in st.session_state:
    st.session_state.collection_data = []
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'sales_success' not in st.session_state:
    st.session_state.sales_success = 0

# ==================== SETTINGS ====================
# Collection ID
coll_id = "zKC3o1sfYEcBGNaTPDRn"
# Test mode
test_mode = True
test_limit = 5
# Max threads
max_workers = 2
# Bearer token (paste your token here)
token_input = "YOUR_BEARER_TOKEN_HERE"
# Google Sheet CSV (public read-only)
gs_csv_url = "https://docs.google.com/spreadsheets/d/1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw/export?format=csv&gid=2146192861"

# ==================== LOGGING ====================
def log_message(message):
    timestamp = datetime.now().strftime('%H:%M:%S')
    st.session_state.logs.append(f"[{timestamp}] {message}")
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]

# ==================== DATA IMPORT ====================
def load_google_sheet_csv(url):
    """Load CSV from public Google Sheet"""
    try:
        df = pd.read_csv(url)
        st.session_state.collection_data = df.to_dict('records')
        log_message(f"✅ Loaded {len(st.session_state.collection_data)} cards from Google Sheet")
        return True
    except Exception as e:
        log_message(f"❌ Failed to load Google Sheet: {str(e)}")
        return False

# ==================== SCRAPING FUNCTIONS ====================
def fetch_sales_for_card(card_data):
    """Fetch last 3 sales for a single card"""
    try:
        headers = {
            'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}",
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0'
        }

        label = card_data.get('label', '')
        if not label:
            year = card_data.get('year', '')
            number = card_data.get('number', '')
            condition = card_data.get('condition', '')
            card_set = card_data.get('set', '')
            player = card_data.get('player', '')
            label = f"{year} {card_set} {player} #{number} {condition}"

        params = {
            'index': 'salesarchive',
            'query': label,
            'page': 0,
            'limit': 20,
            'filters': '',
            'sort': 'date',
            'direction': 'desc'
        }

        response = requests.get(
            'https://search-zzvl7ri3bq-uc.a.run.app/search',
            headers=headers,
            params=params,
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()
            hits = data.get('hits', [])
            sales_info = {
                'sales_search_query': label,
                'total_sales_in_db': data.get('totalHits', 0),
                'sales_found': len(hits)
            }

            last_three = hits[:3]
            sale_prices = []

            for i, sale in enumerate(last_three, 1):
                price = sale.get('price')
                date = sale.get('date', '')
                listing_type = sale.get('listingType', '')

                if price is not None:
                    sale_prices.append(price)

                if date and 'T' in date:
                    try:
                        dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                        date = dt.strftime('%Y-%m-%d')
                    except:
                        pass

                sales_info[f'sale{i}_price'] = price
                sales_info[f'sale{i}_date'] = date
                sales_info[f'sale{i}_listingType'] = listing_type

            for i in range(len(last_three) + 1, 4):
                sales_info[f'sale{i}_price'] = None
                sales_info[f'sale{i}_date'] = None
                sales_info[f'sale{i}_listingType'] = None

            if sale_prices:
                sales_info['avg_last_3_sales'] = round(sum(sale_prices) / len(sale_prices), 2)
                sales_info['sales_count_for_avg'] = len(sale_prices)
            else:
                sales_info['avg_last_3_sales'] = None
                sales_info['sales_count_for_avg'] = 0

            return sales_info
        else:
            return None
    except:
        return None

def fetch_sales_for_all_cards():
    """Fetch sales for all cards"""
    if not st.session_state.collection_data:
        log_message("❌ No collection data to process")
        return 0

    total_cards = len(st.session_state.collection_data)
    sales_success = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_sales_for_card, card) for card in st.session_state.collection_data]

        for idx, future in enumerate(futures, 1):
            result = future.result()
            if result:
                st.session_state.collection_data[idx-1].update(result)
                sales_success += 1
                log_message(f"✅ [{idx}/{total_cards}] Card processed: {result.get('sales_found',0)} sales found")
            else:
                log_message(f"❌ [{idx}/{total_cards}] Failed to fetch sales")

    return sales_success

# ==================== MAIN PROCESS ====================
if not st.session_state.collection_data:
    load_google_sheet_csv(gs_csv_url)

if st.session_state.collection_data:
    st.subheader("Collection Loaded ✅")
    st.write(f"Total Cards: {len(st.session_state.collection_data)}")

    if st.button("🚀 Fetch Last 3 Sales for All Cards"):
        st.session_state.processing = True
        with st.spinner("Fetching sales data..."):
            st.session_state.sales_success = fetch_sales_for_all_cards()
        st.success(f"Completed! Sales fetched for {st.session_state.sales_success}/{len(st.session_state.collection_data)} cards")

# ==================== EXPORT DATA ====================
if st.session_state.collection_data:
    df = pd.DataFrame(st.session_state.collection_data)
    
    # Excel
    output_excel = io.BytesIO()
    df.to_excel(output_excel, index=False)
    st.download_button(
        label="📗 Download Excel",
        data=output_excel.getvalue(),
        file_name="CardLadder_Data.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # CSV
    csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
    st.download_button(
        label="📊 Download CSV",
        data=csv_data,
        file_name="CardLadder_Data.csv",
        mime="text/csv"
    )

    # JSON
    json_data = json.dumps(st.session_state.collection_data, indent=2).encode('utf-8')
    st.download_button(
        label="💾 Download JSON",
        data=json_data,
        file_name="CardLadder_Data.json",
        mime="application/json"
    )

# ==================== LOGS ====================
st.subheader("📝 Logs")
for log in st.session_state.logs[-20:]:
    st.text(log)
