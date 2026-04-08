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
        
        # All required fields are here to prevent the 'client_id' error
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
    res_data = {
        'total_sales_in_db': 0,
        'sale1_price': None,
        'sale2_price': None,
        'sale3_price': None,
        'sale4_price': None,
        'avg_last_4_sales': 0
    }
    try:
        # Fetch more sales to ensure we get 4 unique ones after deduplication
        params = {'index': 'salesarchive', 'query': label, 'limit': 50, 'sort': 'date', 'direction': 'desc'}
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', [])
            res_data['total_sales_in_db'] = data.get('totalHits', 0)
            
            # Deduplicate by cert number (unique slab serial)
            seen_certs = set()
            unique_sales = []
            
            for hit in hits:
                cert = hit.get('cert')
                if cert:
                    if cert not in seen_certs:
                        seen_certs.add(cert)
                        unique_sales.append(hit)
                else:
                    # If no cert, use date+price as unique identifier
                    unique_key = f"{hit.get('date')}_{hit.get('price')}"
                    if unique_key not in seen_certs:
                        seen_certs.add(unique_key)
                        unique_sales.append(hit)
            
            # Get prices from unique sales (limit to 4)
            prices = [h.get('price') for h in unique_sales[:4] if h.get('price')]
            
            # Assign individual sale prices
            for i in range(4):
                if i < len(prices):
                    res_data[f'sale{i+1}_price'] = prices[i]
            
            # Calculate average of last 4 unique sales
            if prices:
                res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
                
    except Exception as e:
        st.warning(f"Error fetching sales for {label}: {str(e)[:100]}")
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
        limit = 50000  # High safety limit

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
            
            # Update Progress Bar
            prog_val = min(len(all_cards) / total_available, 1.0) if total_available > 0 else 1.0
            progress_cards.progress(prog_val, text=f"Found {len(all_cards)} of {total_available} cards")
            
            if len(all_cards) >= total_available or len(all_cards) >= limit or not hits:
                break
            
            page += 1
            time.sleep(0.2)
        
        cards = all_cards[:limit]
        progress_cards.empty()
        
        # --- PHASE 2: FETCHING SALES (Slow Step) ---
        status.write("📈 Fetching Sales History for each card (last 4 unique sales)...")
        progress_sales = st.progress(0)
        
        sales_data = []
        total_to_process = len(cards)
        
        for i, card in enumerate(cards):
            s_result = fetch_sales(auth_token, card)
            sales_data.append(s_result)
            
            # Update Sales Progress
            s_prog_val = (i + 1) / total_to_process
            progress_sales.progress(s_prog_val, text=f"Pricing Card {i+1}/{total_to_process}: {card.get('label', 'Loading...')}")
        
        # Merge data
        for i, s in enumerate(sales_data):
            cards[i].update(s)
        
        progress_sales.empty()
        
        # --- PHASE 3: PROCESSING DATA ---
        df_full = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        df_full.insert(0, 'Scrape Date', scrape_date)
        
        if 'collectionCardId' in df_full.columns:
            df_full.insert(1, 'Card Unique URL', df_full['collectionCardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true"))
        
        # Define columns for Google Sheets (updated with 4 sales and new average)
        TARGET_COLS = [
            'Scrape Date', 
            'Card Unique URL', 
            'label', 
            'condition', 
            'variation', 
            'player', 
            'currentValue',
            'sale1_price',
            'sale2_price', 
            'sale3_price',
            'sale4_price',
            'avg_last_4_sales', 
            'total_sales_in_db'
        ]
        df_filtered = df_full.reindex(columns=TARGET_COLS).fillna('')
        
        # --- PHASE 4: GOOGLE SHEETS SYNC ---
        status.write("📝 Updating Google Sheets...")
        client = get_gspread_client()
        if client:
            try:
                sh = client.open_by_key(SPREADSHEET_ID)
                ws = sh.sheet1
                ws.clear()
                
                # Convert to list for gspread
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
        st.subheader("Google Sheet Version (Filtered)")
        st.dataframe(df_filtered, height=400)
        
        buf1 = io.BytesIO()
        with pd.ExcelWriter(buf1, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False)
        st.download_button("📥 Download Filtered Excel", buf1.getvalue(), f"Filtered_Cards_{scrape_date}.xlsx")
    
    with c2:
        st.subheader("Master File (Full Data)")
        st.dataframe(df_full, height=400)
        
        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine='openpyxl') as writer:
            df_full.to_excel(writer, index=False)
        st.download_button("📥 Download FULL Master Excel", buf2.getvalue(), f"Full_Cards_{scrape_date}.xlsx")
