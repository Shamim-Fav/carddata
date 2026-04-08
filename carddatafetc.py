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
def fetch_sales(token, card):
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    label = card.get('label', '')
    
    # Initialize result dictionary
    result = {
        'total_sales_in_db': 0,
        'sale1_price': '',
        'sale2_price': '',
        'sale3_price': '',
        'avg_last_3_sales': '',
        'raw_sale_prices': '',
        'sale_dates': '',
        'sale_grades': ''
    }
    
    try:
        params = {'index': 'salesarchive', 'query': label, 'limit': 3, 'sort': 'date', 'direction': 'desc'}
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params, timeout=10)
        
        if res.status_code == 200:
            data = res.json()
            hits = data.get('hits', [])
            result['total_sales_in_db'] = data.get('totalHits', 0)
            
            prices = []
            dates = []
            grades = []
            
            for hit in hits:
                price = hit.get('price')
                sale_date = hit.get('date', '')
                grade = hit.get('grade', '')
                
                if price is not None and price != '':
                    prices.append(float(price))
                if sale_date:
                    dates.append(sale_date)
                if grade:
                    grades.append(grade)
            
            # Store raw data
            result['raw_sale_prices'] = ', '.join([str(p) for p in prices]) if prices else 'No sales'
            result['sale_dates'] = ', '.join(dates) if dates else 'No dates'
            result['sale_grades'] = ', '.join(grades) if grades else 'No grades'
            
            # Store individual prices
            for i in range(3):
                if i < len(prices):
                    result[f'sale{i+1}_price'] = prices[i]
            
            # Calculate average
            if prices:
                result['avg_last_3_sales'] = round(sum(prices) / len(prices), 2)
                
    except Exception as e:
        st.warning(f"Error fetching sales for {label}: {str(e)[:100]}")
    
    return result

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

        # --- PHASE 2: FETCHING SALES ---
        status.write("📈 Fetching Sales History for each card...")
        progress_sales = st.progress(0)
        
        # Create a list to store all card data with sales
        cards_with_sales = []
        total_to_process = len(cards)
        
        for i, card in enumerate(cards):
            # Get sales data
            sales_data = fetch_sales(auth_token, card)
            
            # Create a new dictionary combining card and sales data
            combined_card = {}
            combined_card.update(card)  # Add all original card data
            combined_card.update(sales_data)  # Add sales data (will overwrite any conflicts)
            
            cards_with_sales.append(combined_card)
            
            # Update Progress
            s_prog_val = (i + 1) / total_to_process
            progress_sales.progress(s_prog_val, text=f"Processing {i+1}/{total_to_process}: {card.get('label', 'Loading')[:50]}")
            
        progress_sales.empty()

        # --- PHASE 3: CREATE DATAFRAME ---
        # Convert to DataFrame
        df_full = pd.DataFrame(cards_with_sales)
        
        # Add scrape date
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        df_full.insert(0, 'Scrape Date', scrape_date)
        
        # Add URL if collectionCardId exists
        if 'collectionCardId' in df_full.columns:
            df_full.insert(1, 'Card Unique URL', df_full['collectionCardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true"))
        
        # Debug: Show what columns we have
        st.write("### Debug: Available Sales Columns")
        sales_cols = [col for col in df_full.columns if 'sale' in col.lower() or 'avg' in col.lower() or 'total_sales' in col.lower()]
        st.write(sales_cols if sales_cols else "No sales columns found!")
        
        # Define columns for Main Tab
        TARGET_COLS = [
            'Scrape Date', 'Card Unique URL', 'label', 'condition', 
            'variation', 'player', 'currentValue', 'avg_last_3_sales', 
            'total_sales_in_db'
        ]
        
        # Only use columns that exist
        existing_target_cols = [col for col in TARGET_COLS if col in df_full.columns]
        df_filtered = df_full[existing_target_cols].fillna('')
        
        # Define columns for Raw Data Tab
        RAW_COLS = [
            'Scrape Date', 'label', 'condition', 'variation', 'player',
            'currentValue', 'total_sales_in_db', 'avg_last_3_sales',
            'sale1_price', 'sale2_price', 'sale3_price',
            'raw_sale_prices', 'sale_dates', 'sale_grades'
        ]
        
        existing_raw_cols = [col for col in RAW_COLS if col in df_full.columns]
        df_raw = df_full[existing_raw_cols].fillna('') if existing_raw_cols else pd.DataFrame()

        # --- PHASE 4: GOOGLE SHEETS SYNC ---
        status.write("📝 Updating Google Sheets...")
        client = get_gspread_client()
        if client:
            try:
                sh = client.open_by_key(SPREADSHEET_ID)
                
                # Clear existing sheets
                for worksheet in sh.worksheets():
                    sh.del_worksheet(worksheet)
                
                # Create Main Data tab
                ws_main = sh.add_worksheet(title="Main Data", rows="1000", cols="20")
                data_to_send = [df_filtered.columns.tolist()] + df_filtered.astype(str).values.tolist()
                ws_main.update(data_to_send, value_input_option='USER_ENTERED')
                
                # Create Raw Sales Data tab if we have data
                if not df_raw.empty:
                    ws_raw = sh.add_worksheet(title="Raw Sales Data", rows="1000", cols="20")
                    raw_data_to_send = [df_raw.columns.tolist()] + df_raw.astype(str).values.tolist()
                    ws_raw.update(raw_data_to_send, value_input_option='USER_ENTERED')
                    st.info(f"📊 Raw Sales Data tab created with {len(df_raw)} rows")
                
                st.success(f"✅ Sync Complete: {len(df_filtered)} cards sent to Google Sheets!")
                
            except Exception as e:
                st.error(f"Google Sheet Error: {e}")

        status.update(label="Scrape Finished Successfully!", state="complete")

    # --- DOWNLOADS ---
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Main Data (Filtered)")
        st.dataframe(df_filtered, height=400)
        
        buf1 = io.BytesIO()
        with pd.ExcelWriter(buf1, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name='Main Data')
            if not df_raw.empty:
                df_raw.to_excel(writer, index=False, sheet_name='Raw Sales Data')
        st.download_button("📥 Download Excel", buf1.getvalue(), f"Card_Data_{scrape_date}.xlsx")

    with c2:
        st.subheader("Raw Sales Data (Debug)")
        if not df_raw.empty:
            st.dataframe(df_raw, height=400)
        else:
            st.info("No raw sales data available to display")

    # --- Data Quality Warnings ---
    st.divider()
    st.subheader("⚠️ Data Quality Warnings")
    
    # Check for suspicious averages
    if 'total_sales_in_db' in df_full.columns and 'avg_last_3_sales' in df_full.columns:
        if 'sale1_price' in df_full.columns:
            # Convert to numeric for comparison
            df_full['sale1_price'] = pd.to_numeric(df_full['sale1_price'], errors='coerce')
            df_full['avg_last_3_sales'] = pd.to_numeric(df_full['avg_last_3_sales'], errors='coerce')
            
            suspicious = df_full[
                (df_full['total_sales_in_db'] == 1) & 
                (df_full['avg_last_3_sales'] != df_full['sale1_price'])
            ]
            
            if len(suspicious) > 0:
                st.warning(f"⚠️ Found {len(suspicious)} cards with 1 sale but average doesn't match sale price!")
                cols_to_show = [col for col in ['label', 'total_sales_in_db', 'sale1_price', 'avg_last_3_sales', 'raw_sale_prices'] if col in suspicious.columns]
                st.dataframe(suspicious[cols_to_show])
            else:
                st.success("✓ No suspicious averages detected")
        else:
            st.info("No single-sale cards found to check")
    else:
        st.error("❌ Sales data columns missing from dataframe!")
        st.write("First row of data:", df_full.iloc[0].to_dict() if len(df_full) > 0 else "No data")
