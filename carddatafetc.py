import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
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
def get_card_details(token, card_id):
    """Fetch card details to get gemRateId"""
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    
    try:
        # Try to get card details from the card endpoint
        url = f"https://api.cardladder.com/api/cards/{card_id}"
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            card_data = res.json()
            return card_data.get('gemRateId', '')
    except:
        pass
    
    return ''

def fetch_sales(token, card, debug=False):
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    
    # Get cardId from the collection card
    card_id = card.get('cardId', '')
    label = card.get('label', '')
    
    res_data = {
        'total_sales_in_db': 0,
        'sale1_price': None,
        'sale2_price': None,
        'sale3_price': None,
        'sale4_price': None,
        'sale1_date': None,
        'sale2_date': None,
        'sale3_date': None,
        'sale4_date': None,
        'avg_last_4_sales': 0,
        'search_method_used': 'none'
    }
    
    try:
        # FIRST: Try to get gemRateId from card details API
        gem_rate_id = ''
        if card_id:
            gem_rate_id = get_card_details(token, card_id)
            if debug and gem_rate_id:
                st.write(f"🔍 Found gemRateId for {label[:50]}: {gem_rate_id[:20]}...")
        
        # Priority 1: Use gemRateId if found (MOST ACCURATE)
        if gem_rate_id:
            params = {
                'index': 'salesarchive',
                'query': gem_rate_id,
                'limit': 50,
                'sort': 'date',
                'direction': 'desc'
            }
            
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                              headers=headers, params=params, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                hits = data.get('hits', [])
                
                if hits:
                    valid_sales = []
                    for hit in hits:
                        price = hit.get('price')
                        date = hit.get('date')
                        if price is not None and price > 0:
                            valid_sales.append({'price': price, 'date': date})
                    
                    if valid_sales:
                        for i in range(min(4, len(valid_sales))):
                            res_data[f'sale{i+1}_price'] = valid_sales[i]['price']
                            res_data[f'sale{i+1}_date'] = valid_sales[i]['date']
                        
                        prices = [s['price'] for s in valid_sales[:4]]
                        res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
                        res_data['total_sales_in_db'] = data.get('totalHits', 0)
                        res_data['search_method_used'] = 'gemRateId (from card details)'
                        
                        if debug:
                            st.success(f"✅ Using gemRateId: Found {len(valid_sales)} sales")
                        return res_data
        
        # Priority 2: Use cardId directly
        if card_id and not res_data['sale1_price']:
            params = {
                'index': 'salesarchive',
                'query': card_id,
                'limit': 50,
                'sort': 'date',
                'direction': 'desc'
            }
            
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                              headers=headers, params=params, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                hits = data.get('hits', [])
                
                if hits:
                    valid_sales = []
                    for hit in hits:
                        price = hit.get('price')
                        date = hit.get('date')
                        if price is not None and price > 0:
                            valid_sales.append({'price': price, 'date': date})
                    
                    if valid_sales:
                        for i in range(min(4, len(valid_sales))):
                            res_data[f'sale{i+1}_price'] = valid_sales[i]['price']
                            res_data[f'sale{i+1}_date'] = valid_sales[i]['date']
                        
                        prices = [s['price'] for s in valid_sales[:4]]
                        res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
                        res_data['total_sales_in_db'] = data.get('totalHits', 0)
                        res_data['search_method_used'] = 'cardId'
                        
                        if debug:
                            st.info(f"📝 Using cardId: Found {len(valid_sales)} sales")
                        return res_data
        
        # Priority 3: Fall back to label (least accurate)
        if label and not res_data['sale1_price']:
            params = {
                'index': 'salesarchive',
                'query': label,
                'limit': 50,
                'sort': 'date',
                'direction': 'desc'
            }
            
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                              headers=headers, params=params, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                hits = data.get('hits', [])
                
                if hits:
                    valid_sales = []
                    for hit in hits:
                        price = hit.get('price')
                        date = hit.get('date')
                        if price is not None and price > 0:
                            valid_sales.append({'price': price, 'date': date})
                    
                    if valid_sales:
                        for i in range(min(4, len(valid_sales))):
                            res_data[f'sale{i+1}_price'] = valid_sales[i]['price']
                            res_data[f'sale{i+1}_date'] = valid_sales[i]['date']
                        
                        prices = [s['price'] for s in valid_sales[:4]]
                        res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
                        res_data['total_sales_in_db'] = data.get('totalHits', 0)
                        res_data['search_method_used'] = 'label (fallback)'
                        
                        if debug:
                            st.warning(f"⚠️ Using label fallback: Found {len(valid_sales)} sales")
                        return res_data
                        
    except Exception as e:
        if debug:
            st.write(f"Error fetching sales: {e}")
    
    return res_data

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Card Ladder Scraper", layout="wide")
st.title("🕰️ Card Data Scraper")

with st.sidebar:
    st.header("Settings")
    auth_token = st.text_input("Enter Bearer Token", type="password")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    scrape_all = st.checkbox("Scrape ALL Cards in Collection", value=False)
    if not scrape_all:
        limit = st.number_input("Limit (number of cards)", value=5, min_value=1)
    else:
        st.info("Will fetch entire collection.")
        limit = 50000
    
    debug_mode = st.checkbox("Debug Mode - Show detailed search info", value=False)
    
    st.warning("⚠️ Note: This script makes an extra API call per card to get accurate sales data. This will be slower but more accurate.")

if st.button("🚀 Start Scrape"):
    if not auth_token:
        st.error("Please provide a token!")
        st.stop()

    all_cards = []
    
    with st.status("Scraping Data...", expanded=True) as status:
        # --- PHASE 1: FETCHING CARD LIST ---
        status.write("📂 Downloading card list...")
        headers = {'authorization': f"Bearer {auth_token}" if "Bearer" not in auth_token else auth_token}
        
        page = 0
        limit_per_request = 50 
        progress_cards = st.progress(0)
        
        while True:
            params = {
                'index': 'collectioncards', 
                'limit': limit_per_request, 
                'page': page,
                'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'
            }
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
            
            if res.status_code != 200:
                st.error(f"API Error: {res.status_code}")
                break
            
            data = res.json()
            hits = data.get('hits', [])
            total_available = data.get('totalHits', 0)
            
            all_cards.extend(hits)
            
            prog_val = min(len(all_cards) / total_available, 1.0) if total_available > 0 else 1.0
            progress_cards.progress(prog_val, text=f"Found {len(all_cards)} of {total_available} cards")

            if len(all_cards) >= total_available or len(all_cards) >= limit or not hits:
                break
            
            page += 1
            time.sleep(0.2)

        cards = all_cards[:limit]
        progress_cards.empty()

        # --- PHASE 2: FETCHING CARD DETAILS AND SALES ---
        status.write("📈 Fetching card details and sales history...")
        status.write("⏱️ This will take ~2-3 seconds per card...")
        
        progress_sales = st.progress(0)
        
        sales_data = []
        total_to_process = len(cards)
        
        for i, card in enumerate(cards):
            if debug_mode:
                st.write(f"\n--- Processing card {i+1}/{total_to_process} ---")
            
            s_result = fetch_sales(auth_token, card, debug=debug_mode)
            sales_data.append(s_result)
            
            s_prog_val = (i + 1) / total_to_process
            progress_sales.progress(s_prog_val, text=f"Processing Card {i+1}/{total_to_process}: {card.get('label', 'Loading...')[:50]}")
            time.sleep(0.5)  # Delay to avoid rate limiting
        
        # Merge data
        for i, s in enumerate(sales_data):
            cards[i].update(s)
            
        progress_sales.empty()

        # --- PHASE 3: PROCESSING DATA ---
        status.write("📊 Processing data...")
        df_full = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        df_full.insert(0, 'Scrape Date', scrape_date)
        
        # Fix URL generation
        if 'cardId' in df_full.columns:
            df_full.insert(1, 'Card Unique URL', df_full['cardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=True"))
        elif 'collectionCardId' in df_full.columns:
            df_full.insert(1, 'Card Unique URL', df_full['collectionCardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=True"))

        TARGET_COLS = [
            'Scrape Date', 'Card Unique URL', 'label', 'condition', 
            'variation', 'player', 'currentValue',
            'sale1_price', 'sale1_date',
            'sale2_price', 'sale2_date', 
            'sale3_price', 'sale3_date',
            'sale4_price', 'sale4_date',
            'avg_last_4_sales', 'total_sales_in_db', 'search_method_used'
        ]
        
        existing_cols = [col for col in TARGET_COLS if col in df_full.columns]
        df_filtered = df_full.reindex(columns=existing_cols).fillna('')

        # --- PHASE 4: GOOGLE SHEETS SYNC ---
        status.write("📝 Updating Google Sheets...")
        client = get_gspread_client()
        if client:
            try:
                sh = client.open_by_key(SPREADSHEET_ID)
                ws = sh.sheet1
                ws.clear()
                
                data_to_send = [df_filtered.columns.tolist()] + df_filtered.astype(str).values.tolist()
                ws.update(data_to_send, value_input_option='USER_ENTERED')
                st.success(f"✅ Sync Complete: {len(df_filtered)} cards sent to Google Sheets!")
            except Exception as e:
                st.error(f"Google Sheet Error: {e}")

        status.update(label="Scrape Finished Successfully!", state="complete")

    # --- DOWNLOADS ---
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Filtered Data")
        st.dataframe(df_filtered, height=400)
        
        buf1 = io.BytesIO()
        with pd.ExcelWriter(buf1, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False)
        st.download_button("📥 Download Filtered Excel", buf1.getvalue(), f"Filtered_Cards_{scrape_date}.xlsx")

    with c2:
        st.subheader("Full Data")
        st.dataframe(df_full, height=400)
        
        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine='openpyxl') as writer:
            df_full.to_excel(writer, index=False)
        st.download_button("📥 Download Full Master Excel", buf2.getvalue(), f"Full_Cards_{scrape_date}.xlsx")
