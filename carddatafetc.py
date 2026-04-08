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
def fetch_sales(token, card, debug=False):
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    
    # Get all possible identifiers for better matching
    gem_rate_id = card.get('gemRateId', '')
    universal_gem_rate_id = card.get('universalGemRateId', '')
    label = card.get('label', '')
    card_id = card.get('cardId', '')
    
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
        'search_method_used': ''  # To track which search worked
    }
    
    try:
        # Try multiple search queries in order of accuracy
        search_queries = []
        if universal_gem_rate_id:
            search_queries.append(('universalGemRateId', universal_gem_rate_id))
        if gem_rate_id:
            search_queries.append(('gemRateId', gem_rate_id))
        if card_id:
            search_queries.append(('cardId', card_id))
        if label:
            search_queries.append(('label', label))
        
        for query_name, search_query in search_queries:
            params = {
                'index': 'salesarchive',
                'query': search_query,
                'limit': 50,  # Get more sales to ensure we have recent ones
                'sort': 'date',
                'direction': 'desc'
            }
            
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                              headers=headers, params=params, timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                hits = data.get('hits', [])
                
                if hits:
                    # Found sales with this query
                    valid_sales = []
                    for hit in hits:
                        price = hit.get('price')
                        date = hit.get('date')
                        if price is not None and price > 0:
                            valid_sales.append({
                                'price': price,
                                'date': date
                            })
                    
                    if valid_sales:
                        # Debug output for specific card to see what's happening
                        if debug and label == "2023 Pokemon Sword and Shield Crown Zenith 160 Full Art/pikachu":
                            st.write(f"🔍 Debug - Using {query_name}: {search_query[:50]}...")
                            st.write(f"🔍 Debug - Found {len(valid_sales)} total sales")
                            st.write(f"🔍 Debug - Most recent sale date: {valid_sales[0]['date']}")
                            st.write(f"🔍 Debug - Most recent sale price: ${valid_sales[0]['price']}")
                            if len(valid_sales) > 1:
                                st.write(f"🔍 Debug - 2nd most recent: ${valid_sales[1]['price']} on {valid_sales[1]['date']}")
                            if len(valid_sales) > 2:
                                st.write(f"🔍 Debug - 3rd most recent: ${valid_sales[2]['price']} on {valid_sales[2]['date']}")
                            if len(valid_sales) > 3:
                                st.write(f"🔍 Debug - 4th most recent: ${valid_sales[3]['price']} on {valid_sales[3]['date']}")
                        
                        # Take first 4 (most recent by date - API already sorted)
                        for i in range(min(4, len(valid_sales))):
                            res_data[f'sale{i+1}_price'] = valid_sales[i]['price']
                            res_data[f'sale{i+1}_date'] = valid_sales[i]['date']
                        
                        prices = [s['price'] for s in valid_sales[:4]]
                        res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
                        res_data['total_sales_in_db'] = data.get('totalHits', 0)
                        res_data['search_method_used'] = query_name
                        
                        # Success! Break out of the loop
                        break
                        
    except Exception as e:
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
        limit = 50000  # High safety limit
    
    debug_mode = st.checkbox("Debug Mode (shows search details for problem cards)", value=False)

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
        status.write("📈 Fetching Sales History for each card...")
        progress_sales = st.progress(0)
        
        sales_data = []
        total_to_process = len(cards)
        
        for i, card in enumerate(cards):
            # Pass debug flag for specific card
            is_debug_card = debug_mode and card.get('label', '') == "2023 Pokemon Sword and Shield Crown Zenith 160 Full Art/pikachu"
            s_result = fetch_sales(auth_token, card, debug=is_debug_card)
            sales_data.append(s_result)
            
            # Update Sales Progress
            s_prog_val = (i + 1) / total_to_process
            progress_sales.progress(s_prog_val, text=f"Pricing Card {i+1}/{total_to_process}: {card.get('label', 'Loading...')}")
            time.sleep(0.1)  # Small delay to avoid rate limiting
        
        # Merge data
        for i, s in enumerate(sales_data):
            cards[i].update(s)
            
        progress_sales.empty()

        # --- PHASE 3: PROCESSING DATA ---
        df_full = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        df_full.insert(0, 'Scrape Date', scrape_date)
        
        # FIXED: Use cardId instead of collectionCardId for URLs
        if 'cardId' in df_full.columns:
            df_full.insert(1, 'Card Unique URL', df_full['cardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true"))
        elif 'collectionCardId' in df_full.columns:
            st.warning("Using collectionCardId as fallback - card URLs may be incorrect for some cards")
            df_full.insert(1, 'Card Unique URL', df_full['collectionCardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true"))

        # Define columns for Google Sheets (includes sale dates)
        TARGET_COLS = [
            'Scrape Date', 'Card Unique URL', 'label', 'condition', 
            'variation', 'player', 'currentValue',
            'sale1_price', 'sale1_date',
            'sale2_price', 'sale2_date', 
            'sale3_price', 'sale3_date',
            'sale4_price', 'sale4_date',
            'avg_last_4_sales', 'total_sales_in_db', 'search_method_used'
        ]
        
        # Only include columns that exist in the dataframe
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
    
    # Show debug summary if debug mode was on
    if debug_mode:
        st.divider()
        st.subheader("🔍 Debug Summary")
        st.write("Check the 'search_method_used' column in the data above to see which identifier worked for each card.")
        st.write("The debug output for the Pikachu card (if in your collection) will appear in the terminal/console.")
