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
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
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
    """Fetch last 4 sales using FULL LABEL search for accuracy"""
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    label = card.get('label', '')
    
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
        'search_method': 'Full Label'
    }
    
    try:
        # Using FULL LABEL for most accurate results
        params = {
            'index': 'salesarchive', 
            'query': label,  # Full label search
            'limit': 4, 
            'sort': 'date', 
            'direction': 'desc'
        }
        
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                          headers=headers, 
                          params=params, 
                          timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', [])
            res_data['total_sales_in_db'] = data.get('totalHits', 0)
            
            # Extract price and date for each sale
            for i in range(4):
                if i < len(hits):
                    hit = hits[i]
                    res_data[f'sale{i+1}_price'] = hit.get('price')
                    res_data[f'sale{i+1}_date'] = hit.get('date')
            
            # Calculate average of last 4 sales (or fewer if not enough)
            prices = [hit.get('price') for hit in hits if hit.get('price')]
            if prices:
                res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
                
    except Exception as e:
        st.warning(f"Error fetching sales for {label[:50]}: {str(e)[:100]}")
        
    return res_data

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Card Ladder Scraper", layout="wide")
st.title("🕰️ Card Data Scraper - Full Label Search")

with st.sidebar:
    st.header("Settings")
    auth_token = st.text_input("Enter Bearer Token", type="password")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    st.markdown("---")
    st.info("🔍 **Using FULL LABEL search** for most accurate sales matching")
    
    scrape_all = st.checkbox("Scrape ALL Cards in Collection", value=False)
    if not scrape_all:
        limit = st.number_input("Limit (number of cards)", value=5, min_value=1, max_value=100)
    else:
        st.info("Will fetch entire collection.")
        limit = 50000

if st.button("🚀 Start Scrape", type="primary"):
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
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                             headers=headers, 
                             params=params)
            
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
        
        st.write(f"✅ Found {len(cards)} cards to process")

        # --- PHASE 2: FETCHING SALES USING FULL LABEL ---
        status.write("📈 Fetching Sales History using FULL LABEL search...")
        progress_sales = st.progress(0)
        
        sales_data = []
        total_to_process = len(cards)
        
        for i, card in enumerate(cards):
            # Show current card being processed
            card_label = card.get('label', 'Unknown')
            status.write(f"Processing {i+1}/{total_to_process}: {card_label[:60]}...")
            
            s_result = fetch_sales(auth_token, card)
            sales_data.append(s_result)
            
            # Update Sales Progress
            s_prog_val = (i + 1) / total_to_process
            progress_sales.progress(s_prog_val, text=f"Pricing Card {i+1}/{total_to_process}")
        
        # Merge data
        for i, s in enumerate(sales_data):
            cards[i].update(s)
            
        progress_sales.empty()

        # --- PHASE 3: PROCESSING DATA ---
        status.write("📊 Processing data...")
        df_full = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df_full.insert(0, 'Scrape Date', scrape_date)
        
        if 'collectionCardId' in df_full.columns:
            df_full.insert(1, 'Card Unique URL', df_full['collectionCardId'].apply(
                lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=True"))

        # Define columns for Google Sheets (includes all sales data)
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
            'search_method',
            'sale1_price', 
            'sale1_date', 
            'sale2_price', 
            'sale2_date', 
            'sale3_price', 
            'sale3_date', 
            'sale4_price', 
            'sale4_date'
        ]
        
        # Only include columns that exist in the dataframe
        existing_cols = [col for col in TARGET_COLS if col in df_full.columns]
        df_filtered = df_full.reindex(columns=existing_cols).fillna('')

        # --- PHASE 4: GOOGLE SHEETS SYNC (Optional) ---
        if st.checkbox("Sync to Google Sheets", value=True):
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
        else:
            status.write("⏭️ Skipping Google Sheets sync")

        status.update(label="Scrape Finished Successfully!", state="complete")

    # --- DOWNLOADS ---
    st.divider()
    st.subheader("📥 Download Results")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Cards Processed", len(df_filtered))
        
    with col2:
        cards_with_sales = df_filtered[df_filtered['total_sales_in_db'] > 0].shape[0] if 'total_sales_in_db' in df_filtered.columns else 0
        st.metric("Cards with Sales Data", cards_with_sales)
        
    with col3:
        avg_sales = df_filtered['avg_last_4_sales'].mean() if 'avg_last_4_sales' in df_filtered.columns else 0
        st.metric("Average Price (Last 4 Sales)", f"${avg_sales:.2f}" if avg_sales > 0 else "N/A")
    
    st.divider()
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📊 Filtered Data (Google Sheets Version)")
        st.dataframe(df_filtered, height=400, use_container_width=True)
        
        # Excel download
        buf1 = io.BytesIO()
        with pd.ExcelWriter(buf1, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False)
        st.download_button(
            "📥 Download Filtered Excel", 
            buf1.getvalue(), 
            f"Filtered_Cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            use_container_width=True
        )

    with c2:
        st.subheader("📋 Master File (Full Data)")
        
        # Show sample of sales data
        if 'sale1_price' in df_full.columns:
            sale_cols = ['label', 'sale1_price', 'sale1_date', 'sale2_price', 'sale2_date']
            existing_sale_cols = [col for col in sale_cols if col in df_full.columns]
            if existing_sale_cols:
                st.dataframe(df_full[existing_sale_cols].head(10), height=400, use_container_width=True)
        else:
            st.dataframe(df_full.head(10), height=400, use_container_width=True)
        
        # Excel download
        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine='openpyxl') as writer:
            df_full.to_excel(writer, index=False)
        st.download_button(
            "📥 Download FULL Master Excel", 
            buf2.getvalue(), 
            f"Full_Cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            use_container_width=True
        )

# Footer
st.divider()
st.caption(f"🕒 Last run would show here | Using FULL LABEL search for accurate sales matching | CardLadder Scraper v2.0")
