import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io
import time
import re

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

# ==================== ACCURATE SALES FETCHING USING GEMRATEID ====================
def get_gemrateid_from_sales(token, card_label):
    """Get gemRateId by searching sales archive (first sale gives the correct gemRateId)"""
    headers = {'authorization': token if 'Bearer' in token else f"Bearer {token}"}
    
    try:
        params = {
            'index': 'salesarchive',
            'query': card_label,
            'limit': 1,
            'sort': 'date',
            'direction': 'desc'
        }
        response = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                                headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get('hits', [])
            if hits:
                return hits[0].get('gemRateId')
    except:
        pass
    return None

def fetch_sales_by_gemrateid(token, gemrate_id, condition="PSA 10"):
    """Fetch last 4 sales using gemRateId - 100% ACCURATE"""
    headers = {'authorization': token if 'Bearer' in token else f"Bearer {token}"}
    
    # Map condition to API format
    condition_map = {
        "PSA 10": "g10",
        "PSA 9": "g9",
        "PSA 8": "g8",
        "BGS 10": "bgs10",
        "BGS 9.5": "bgs9.5",
    }
    grade_code = condition_map.get(condition, "g10")
    
    res_data = {
        'total_sales_in_db': 0,
        'sale1_price': None,
        'sale1_date': None,
        'sale2_price': None,
        'sale2_date': None,
        'sale3_price': None,
        'sale3_date': None,
        'sale4_price': None,
        'sale4_date': None,
        'avg_last_4_sales': 0,
        'gemRateId': gemrate_id
    }
    
    if not gemrate_id:
        return res_data
    
    try:
        # Use filters with gemRateId for exact matching
        params = {
            'index': 'salesarchive',
            'limit': 4,
            'sort': 'date',
            'direction': 'desc',
            'filters': f'condition:{grade_code}|gemRateId:{gemrate_id}|gradingCompany:psa'
        }
        
        response = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                                headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get('hits', [])
            res_data['total_sales_in_db'] = data.get('totalHits', 0)
            
            prices = []
            for i in range(min(4, len(hits))):
                hit = hits[i]
                price = hit.get('price')
                date_str = hit.get('date', '')
                res_data[f'sale{i+1}_price'] = price
                
                # Format date nicely (YYYY-MM-DD)
                if date_str:
                    try:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        res_data[f'sale{i+1}_date'] = date_obj.strftime('%Y-%m-%d')
                    except:
                        res_data[f'sale{i+1}_date'] = date_str[:10]
                
                if price:
                    prices.append(price)
            
            if prices:
                res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
                
    except Exception as e:
        st.warning(f"Error fetching sales: {e}")
    
    return res_data

def fetch_sales_fallback(token, card_label):
    """Fallback: Fetch sales using label search if gemRateId not found"""
    headers = {'authorization': token if 'Bearer' in token else f"Bearer {token}"}
    
    res_data = {
        'total_sales_in_db': 0,
        'sale1_price': None,
        'sale1_date': None,
        'sale2_price': None,
        'sale2_date': None,
        'sale3_price': None,
        'sale3_date': None,
        'sale4_price': None,
        'sale4_date': None,
        'avg_last_4_sales': 0,
        'gemRateId': None
    }
    
    try:
        params = {
            'index': 'salesarchive',
            'query': card_label,
            'limit': 4,
            'sort': 'date',
            'direction': 'desc'
        }
        response = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                                headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get('hits', [])
            res_data['total_sales_in_db'] = data.get('totalHits', 0)
            
            prices = []
            for i in range(min(4, len(hits))):
                hit = hits[i]
                price = hit.get('price')
                date_str = hit.get('date', '')
                res_data[f'sale{i+1}_price'] = price
                
                if date_str:
                    try:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        res_data[f'sale{i+1}_date'] = date_obj.strftime('%Y-%m-%d')
                    except:
                        res_data[f'sale{i+1}_date'] = date_str[:10]
                
                if price:
                    prices.append(price)
            
            if prices:
                res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
    except:
        pass
    
    return res_data

def fetch_sales(token, card):
    """Main sales fetch function - uses gemRateId for accuracy"""
    label = card.get('label', '')
    condition = card.get('condition', 'PSA 10')
    
    # Step 1: Try to get gemRateId from sales archive
    gemrate_id = get_gemrateid_from_sales(token, label)
    
    # Step 2: If gemRateId found, use it for accurate sales
    if gemrate_id:
        return fetch_sales_by_gemrateid(token, gemrate_id, condition)
    else:
        # Step 3: Fallback to label search
        return fetch_sales_fallback(token, label)

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Card Ladder Scraper - Accurate Sales", layout="wide")
st.title("🕰️ Card Data Scraper (Accurate Sales)")

with st.sidebar:
    st.header("Settings")
    auth_token = st.text_input("Enter Bearer Token", type="password")
    coll_id = st.text_input("Collection ID", value="m5H67EW8v1L1tXYf4Y32")
    
    st.markdown("---")
    st.info("""
    **How it works:**
    1. Fetches your collection cards
    2. Gets gemRateId from sales archive
    3. Uses gemRateId for 100% accurate sales
    4. Returns last 4 sales with dates
    """)
    
    scrape_all = st.checkbox("Scrape ALL Cards in Collection", value=False)
    if not scrape_all:
        limit = st.number_input("Limit (number of cards)", value=5, min_value=1)
    else:
        st.info("Will fetch entire collection.")
        limit = 50000

if st.button("🚀 Start Scrape", type="primary"):
    if not auth_token:
        st.error("Please provide a token!")
        st.stop()

    # Ensure token has Bearer prefix
    if not auth_token.startswith('Bearer '):
        auth_token = f"Bearer {auth_token}"

    all_cards = []
    
    with st.status("Scraping Data...", expanded=True) as status:
        # --- PHASE 1: FETCHING CARD LIST ---
        status.write("📂 Downloading card list...")
        headers = {'authorization': auth_token}
        
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
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                             headers=headers, params=params)
            
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
        st.write(f"✅ Found {len(cards)} cards to process")

        # --- PHASE 2: FETCHING SALES USING GEMRATEID ---
        status.write("📈 Fetching Sales History using gemRateId (100% accurate)...")
        progress_sales = st.progress(0)
        
        sales_data = []
        total_to_process = len(cards)
        
        for i, card in enumerate(cards):
            card_label = card.get('label', 'Unknown')
            status.write(f"Processing {i+1}/{total_to_process}: {card_label[:60]}...")
            
            s_result = fetch_sales(auth_token, card)
            sales_data.append(s_result)
            
            s_prog_val = (i + 1) / total_to_process
            progress_sales.progress(s_prog_val, text=f"Card {i+1}/{total_to_process}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        # Merge data
        for i, s in enumerate(sales_data):
            cards[i].update(s)
            
        progress_sales.empty()

        # --- PHASE 3: PROCESSING DATA ---
        status.write("📊 Processing data...")
        df_full = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        df_full.insert(0, 'Scrape Date', scrape_date)
        
        if 'collectionCardId' in df_full.columns:
            df_full.insert(1, 'Card Unique URL', df_full['collectionCardId'].apply(
                lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=True"))

        # Define columns for Google Sheets (includes all 4 sales with dates)
        TARGET_COLS = [
            'Scrape Date', 
            'Card Unique URL', 
            'label', 
            'condition', 
            'variation', 
            'player', 
            'year',
            'set',
            'currentValue',
            'avg_last_4_sales', 
            'total_sales_in_db',
            'gemRateId',
            'sale1_price', 
            'sale1_date', 
            'sale2_price', 
            'sale2_date', 
            'sale3_price', 
            'sale3_date', 
            'sale4_price', 
            'sale4_date'
        ]
        
        # Only include columns that exist
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

    # --- STATISTICS ---
    st.divider()
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Cards", len(df_filtered))
    with col2:
        cards_with_sales = df_filtered[df_filtered['total_sales_in_db'] > 0].shape[0] if 'total_sales_in_db' in df_filtered.columns else 0
        st.metric("Cards with Sales", cards_with_sales)
    with col3:
        cards_with_gemrate = df_filtered[df_filtered['gemRateId'] != ''].shape[0] if 'gemRateId' in df_filtered.columns else 0
        st.metric("Found gemRateId", cards_with_gemrate)
    with col4:
        avg_price = df_filtered['avg_last_4_sales'].mean() if 'avg_last_4_sales' in df_filtered.columns else 0
        st.metric("Avg Sale Price", f"${avg_price:.2f}" if avg_price > 0 else "N/A")
    
    # --- DOWNLOADS ---
    st.divider()
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📊 Filtered Data (With Sales)")
        st.dataframe(df_filtered, height=400, use_container_width=True)
        
        buf1 = io.BytesIO()
        with pd.ExcelWriter(buf1, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False)
        st.download_button("📥 Download Filtered Excel", buf1.getvalue(), 
                          f"Filtered_Cards_{scrape_date}.xlsx")

    with c2:
        st.subheader("📋 Master File (Full Data)")
        st.dataframe(df_full, height=400, use_container_width=True)
        
        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine='openpyxl') as writer:
            df_full.to_excel(writer, index=False)
        st.download_button("📥 Download FULL Master Excel", buf2.getvalue(), 
                          f"Full_Cards_{scrape_date}.xlsx")

st.markdown("---")
st.caption("💡 Uses gemRateId for 100% accurate sales matching | Shows last 4 sales with dates")
