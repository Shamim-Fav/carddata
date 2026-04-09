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

# ==================== HELPER FUNCTIONS ====================
def get_card_details(token, card_id, debug=False):
    """Fetch full card details including gemRateId"""
    headers = {'authorization': token if "Bearer" in token else f"Bearer {token}"}
    
    try:
        # Try the card details endpoint
        url = f"https://api.cardladder.com/api/cards/{card_id}"
        res = requests.get(url, headers=headers, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            gem_rate_id = data.get('gemRateId', '')
            if debug and gem_rate_id:
                st.write(f"   ✅ Found gemRateId: {gem_rate_id[:30]}...")
            return gem_rate_id
        else:
            if debug:
                st.write(f"   ⚠️ Card details API returned {res.status_code}")
                
    except Exception as e:
        if debug:
            st.write(f"   ❌ Error fetching card details: {e}")
    
    return ''

def fetch_sales_by_gem_rate_id(token, gem_rate_id, condition, debug=False):
    """Fetch sales using gemRateId with filters (matches website behavior)"""
    headers = {'authorization': token if "Bearer" in token else f"Bearer {token}"}
    
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
        'avg_last_4_sales': 0
    }
    
    try:
        # Convert condition from 'PSA 9' to 'g9'
        condition_code = condition.lower().replace('psa ', 'g') if condition else ''
        
        # Build filters string like the website does
        filters_parts = [f"gemRateId:{gem_rate_id}"]
        if condition_code:
            filters_parts.append(f"condition:{condition_code}")
        
        filters_str = "|".join(filters_parts)
        
        params = {
            'index': 'salesarchive',
            'query': '',  # Empty query when using filters!
            'limit': 50,
            'filters': filters_str,
            'sort': 'date',
            'direction': 'desc'
        }
        
        if debug:
            st.write(f"   🔍 Filters: {filters_str}")
        
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                          headers=headers, params=params, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', [])
            res_data['total_sales_in_db'] = data.get('totalHits', 0)
            
            # Extract valid sales with prices
            valid_sales = []
            for hit in hits:
                price = hit.get('price')
                date = hit.get('date')
                if price is not None and price > 0:
                    valid_sales.append({
                        'price': price,
                        'date': date
                    })
            
            if debug:
                st.write(f"   📊 Found {len(valid_sales)} valid sales")
            
            # Take the first 4 (already sorted by date descending)
            for i in range(min(4, len(valid_sales))):
                res_data[f'sale{i+1}_price'] = valid_sales[i]['price']
                res_data[f'sale{i+1}_date'] = valid_sales[i]['date']
            
            # Calculate average
            prices = [s['price'] for s in valid_sales[:4]]
            if prices:
                res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
                
            if debug and valid_sales:
                st.write(f"   💰 Most recent: ${valid_sales[0]['price']} on {valid_sales[0]['date']}")
                
    except Exception as e:
        if debug:
            st.write(f"   ❌ Error fetching sales: {e}")
    
    return res_data

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Card Ladder Scraper", layout="wide")
st.title("🕰️ Card Data Scraper")

with st.sidebar:
    st.header("Settings")
    auth_token = st.text_input("Enter Bearer Token", type="password", 
                               help="Paste your Bearer token here (starts with 'Bearer eyJ...')")
    
    coll_id = st.text_input("Collection ID", value="em34JGn38x7No7vkwoT5",
                            help="Your collection ID from the URL")
    
    st.divider()
    
    scrape_all = st.checkbox("Scrape ALL Cards in Collection", value=False)
    if not scrape_all:
        limit = st.number_input("Limit (number of cards)", value=5, min_value=1)
    else:
        st.info("Will fetch entire collection.")
        limit = 50000
    
    debug_mode = st.checkbox("Debug Mode - Show detailed info", value=True)

if st.button("🚀 Start Scrape"):
    if not auth_token:
        st.error("Please provide a Bearer Token!")
        st.stop()
    
    if not coll_id:
        st.error("Please provide a Collection ID!")
        st.stop()

    all_cards = []
    
    with st.status("Scraping Data...", expanded=True) as status:
        # --- PHASE 1: FETCHING CARD LIST ---
        status.write("📂 Downloading card list...")
        headers = {'authorization': auth_token if "Bearer" in auth_token else f"Bearer {auth_token}"}
        
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
                st.write(f"Response: {res.text}")
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
        
        st.write(f"✅ Retrieved {len(cards)} cards from collection")

        # --- PHASE 2: FETCH GEMRATEID AND SALES ---
        status.write("📈 Fetching gemRateId and sales for each card...")
        status.write("⏱️ This takes ~2-3 seconds per card...")
        
        progress_sales = st.progress(0)
        total_to_process = len(cards)
        
        for i, card in enumerate(cards):
            card_id = card.get('cardId', '')
            label = card.get('label', 'Unknown')[:50]
            condition = card.get('condition', '')
            
            if debug_mode:
                st.write(f"\n--- Card {i+1}/{total_to_process}: {label} ---")
                st.write(f"   Card ID: {card_id}")
                st.write(f"   Condition: {condition}")
            
            # Step 1: Get gemRateId from card details API
            if card_id:
                gem_rate_id = get_card_details(auth_token, card_id, debug_mode)
                
                if gem_rate_id:
                    # Step 2: Fetch sales using gemRateId
                    sales_result = fetch_sales_by_gem_rate_id(auth_token, gem_rate_id, condition, debug_mode)
                else:
                    if debug_mode:
                        st.warning("   ⚠️ No gemRateId found, skipping sales")
                    sales_result = {
                        'total_sales_in_db': 0,
                        'sale1_price': None, 'sale2_price': None, 
                        'sale3_price': None, 'sale4_price': None,
                        'sale1_date': None, 'sale2_date': None,
                        'sale3_date': None, 'sale4_date': None,
                        'avg_last_4_sales': 0
                    }
            else:
                if debug_mode:
                    st.warning("   ⚠️ No cardId found")
                sales_result = {
                    'total_sales_in_db': 0,
                    'sale1_price': None, 'sale2_price': None, 
                    'sale3_price': None, 'sale4_price': None,
                    'sale1_date': None, 'sale2_date': None,
                    'sale3_date': None, 'sale4_date': None,
                    'avg_last_4_sales': 0
                }
            
            # Merge sales data with card
            card.update(sales_result)
            
            # Update progress
            s_prog_val = (i + 1) / total_to_process
            progress_sales.progress(s_prog_val, text=f"Processed {i+1}/{total_to_process}")
            time.sleep(0.3)  # Rate limiting
        
        progress_sales.empty()

        # --- PHASE 3: PROCESSING DATA ---
        status.write("📊 Processing data...")
        df_full = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        df_full.insert(0, 'Scrape Date', scrape_date)
        
        # Generate URL using cardId
        if 'cardId' in df_full.columns:
            df_full.insert(1, 'Card URL', df_full['cardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=True" if x else "N/A"))

        # Define columns for output
        TARGET_COLS = [
            'Scrape Date', 'Card URL', 'label', 'condition', 
            'variation', 'player', 'currentValue',
            'sale1_price', 'sale1_date',
            'sale2_price', 'sale2_date', 
            'sale3_price', 'sale3_date',
            'sale4_price', 'sale4_date',
            'avg_last_4_sales', 'total_sales_in_db'
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
