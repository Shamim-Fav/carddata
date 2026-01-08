import streamlit as st
import requests
import json
import time
import pandas as pd
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== GOOGLE SHEETS INTEGRATION ====================
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = Fals

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Card Ladder Complete Scraper",
    page_icon="📦",
    layout="wide"
)

# ==================== GOOGLE SHEETS MANAGER ====================
class GoogleSheetsManager:
    def __init__(self, credentials_dict=None, spreadsheet_id=None):
        self.credentials_dict = credentials_dict or GOOGLE_CREDENTIALS
        self.spreadsheet_id = spreadsheet_id or SPREADSHEET_ID
        self.client = None
        self.connected = False
        
    def connect(self):
        try:
            if not GOOGLE_SHEETS_AVAILABLE:
                return False, "Google Sheets libraries not installed"
            if not self.credentials_dict:
                return False, "No credentials provided"
            
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                self.credentials_dict, scope)
            self.client = gspread.authorize(credentials)
            self.connected = True
            return True, "Connected to Google Sheets API"
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def create_or_open_sheet(self, sheet_name):
        try:
            if not self.connected:
                success, message = self.connect()
                if not success:
                    return None, message
            
            if self.spreadsheet_id:
                spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            else:
                spreadsheet = self.client.create(sheet_name)
                self.spreadsheet_id = spreadsheet.id
            
            return spreadsheet, "Success"
        except Exception as e:
            return None, f"Error accessing sheet: {str(e)}"
    
    def save_dataframe_to_sheet(self, spreadsheet, sheet_name, df, clear_existing=True):
        try:
            df_clean = df.copy()
            for col in df_clean.columns:
                df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), None)
                df_clean[col] = df_clean[col].astype(str)
            
            data = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
            
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                if clear_existing:
                    worksheet.clear()
            except gspread.exceptions.WorksheetNotFound:
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=26)
            
            worksheet.update(data, value_input_option='USER_ENTERED')
            
            try:
                worksheet.format('A1:Z1', {
                    'textFormat': {'bold': True},
                    'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}
                })
            except:
                pass
            
            return True, f"Data saved to {sheet_name}"
        except Exception as e:
            return False, f"Error saving to sheet: {str(e)}"
    
    def get_spreadsheet_url(self, spreadsheet):
        return spreadsheet.url

# ==================== STREAMLIT APP ====================
# Initialize session state
if 'collection_data' not in st.session_state:
    st.session_state.collection_data = []
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'sales_success' not in st.session_state:
    st.session_state.sales_success = 0

# Custom CSS
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .status-box { background-color: #2b2b2b; color: white; padding: 15px; border-radius: 5px; }
    .log-box { background-color: #1e1e1e; color: #00ff00; padding: 15px; border-radius: 5px; font-family: monospace; }
    .metric-box { background-color: white; padding: 15px; border-radius: 5px; border-left: 5px solid #007acc; }
    </style>
    """, unsafe_allow_html=True)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.title("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150, 
                               help="Copy the 'authorization' header from DevTools.")
    
    st.divider()
    
    st.title("⚙️ Settings")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    col1, col2 = st.columns(2)
    with col1:
        test_mode = st.checkbox("Test Mode", value=True)
    with col2:
        max_workers = st.slider("Max Threads", 1, 10, 1)
    
    test_limit = st.number_input("Test Limit (cards)", min_value=1, max_value=100, value=5, 
                                 disabled=not test_mode)
    
    st.divider()
    
    if st.button("🗑️ Clear All Data", use_container_width=True):
        st.session_state.collection_data = []
        st.session_state.logs = []
        st.session_state.sales_success = 0
        st.rerun()
    
    if GOOGLE_SHEETS_AVAILABLE:
        st.info("✅ Google Sheets available")
    else:
        st.warning("⚠️ Install gspread and oauth2client for Google Sheets")

# ==================== MAIN INTERFACE ====================
st.title("📦 Card Ladder Complete Scraper")
st.markdown("Two-phase scraper: Fetch collection → Fetch last 3 sales per card")

# Status Display
status_col1, status_col2, status_col3 = st.columns(3)
with status_col1:
    st.metric("Collection Cards", len(st.session_state.collection_data) if st.session_state.collection_data else 0)
with status_col2:
    st.metric("Sales Success", st.session_state.sales_success)
with status_col3:
    if st.session_state.collection_data:
        success_rate = (st.session_state.sales_success / len(st.session_state.collection_data)) * 100
        st.metric("Success Rate", f"{success_rate:.1f}%")
    else:
        st.metric("Success Rate", "0%")

# Control Buttons
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    if st.button("🚀 Start Complete Process", use_container_width=True, type="primary"):
        if not token_input:
            st.error("Please provide a token in the sidebar!")
        else:
            st.session_state.processing = True
            st.session_state.logs = []
            st.rerun()

with col2:
    if st.button("⏹️ Stop Process", use_container_width=True, disabled=not st.session_state.processing):
        st.session_state.processing = False
        st.rerun()

with col3:
    export_disabled = len(st.session_state.collection_data) == 0 or st.session_state.processing
    if st.button("💾 Export Data", use_container_width=True, disabled=export_disabled):
        st.rerun()  # Will trigger export section

# ==================== SCRAPING FUNCTIONS ====================
def log_message(message):
    """Add message to logs"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    st.session_state.logs.append(f"[{timestamp}] {message}")
    if len(st.session_state.logs) > 100:  # Keep last 100 logs
        st.session_state.logs = st.session_state.logs[-100:]

def fetch_collection():
    """Phase 1: Fetch all cards from collection"""
    all_cards = []
    page = 0
    limit = 20
    
    headers = {
        'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}",
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0'
    }
    
    log_message("=== PHASE 1: Fetching Collection ===")
    
    try:
        while True and st.session_state.processing:
            log_message(f"Fetching page {page}...")
            
            params = {
                'index': 'collectioncards',
                'page': page,
                'limit': limit,
                'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true',
                'sort': 'dateAdded',
                'direction': 'asc'
            }
            
            response = requests.get(
                'https://search-zzvl7ri3bq-uc.a.run.app/search',
                headers=headers,
                params=params,
                timeout=15
            )
            
            if response.status_code != 200:
                log_message(f"❌ Error: Server returned {response.status_code}")
                break
                
            data = response.json()
            hits = data.get('hits', [])
            total = data.get('totalHits', 0)
            
            if not hits:
                break
                
            all_cards.extend(hits)
            log_message(f"✅ Page {page}: {len(hits)} cards (Total: {len(all_cards)}/{total})")
            
            if test_mode and len(all_cards) >= test_limit:
                all_cards = all_cards[:test_limit]
                log_message(f"⚠️ Test mode: Limiting to {test_limit} cards")
                break
            
            if len(all_cards) >= total or len(hits) < limit:
                break
                
            page += 1
            time.sleep(0.3)
        
        if all_cards:
            st.session_state.collection_data = all_cards
            log_message(f"✅ PHASE 1 COMPLETE: Collected {len(all_cards)} cards")
            return True
        else:
            log_message("⚠️ No cards found in collection")
            return False
            
    except Exception as e:
        log_message(f"❌ Phase 1 Error: {str(e)}")
        return False

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
            
    except Exception as e:
        return None

def fetch_sales_for_all_cards():
    """Phase 2: Fetch sales for all collected cards"""
    if not st.session_state.collection_data:
        log_message("❌ No collection data to process")
        return 0
    
    log_message("\n=== PHASE 2: Fetching Last 3 Sales ===")
    
    total_cards = len(st.session_state.collection_data)
    sales_success = 0
    
    # Create progress bar and status
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, card in enumerate(st.session_state.collection_data, 1):
            if not st.session_state.processing:
                break
            futures.append((executor.submit(fetch_sales_for_card, card), card, idx))
        
        completed = 0
        for future, card, idx in futures:
            if not st.session_state.processing:
                break
            
            completed += 1
            result = future.result()
            
            if result:
                card.update(result)
                sales_success += 1
                
                player = card.get('player', f'Card {idx}')
                sales_found = result.get('sales_found', 0)
                avg_price = result.get('avg_last_3_sales')
                
                if sales_found > 0:
                    prices = []
                    for i in range(1, 4):
                        price = result.get(f'sale{i}_price')
                        listing_type = result.get(f'sale{i}_listingType', '')
                        if price:
                            price_str = f"${price}"
                            if listing_type:
                                price_str += f" ({listing_type})"
                            prices.append(price_str)
                    
                    if prices:
                        avg_str = f", Avg: ${avg_price:.2f}" if avg_price else ""
                        log_message(f"✅ [{idx}/{total_cards}] {player}: {sales_found} sales{avg_str}")
                    else:
                        log_message(f"✅ [{idx}/{total_cards}] {player}: {sales_found} sales")
                else:
                    log_message(f"⚠️ [{idx}/{total_cards}] {player}: No sales found")
            else:
                player = card.get('player', f'Card {idx}')
                log_message(f"❌ [{idx}/{total_cards}] {player}: Failed to fetch sales")
            
            # Update progress
            progress = completed / total_cards
            progress_bar.progress(progress)
            status_text.text(f"Processing: {completed}/{total_cards} cards ({progress:.1%})")
            
            time.sleep(0.2)
    
    progress_bar.empty()
    status_text.empty()
    return sales_success

# ==================== PROCESS EXECUTION ====================
if st.session_state.processing:
    # Phase 1: Fetch collection
    with st.spinner("Phase 1: Fetching collection..."):
        phase1_success = fetch_collection()
    
    if phase1_success and st.session_state.processing:
        # Phase 2: Fetch sales
        with st.spinner("Phase 2: Fetching sales data..."):
            st.session_state.sales_success = fetch_sales_for_all_cards()
        
        if st.session_state.processing:
            st.success("✅ Process complete!")
            st.session_state.processing = False
            st.rerun()
    else:
        st.session_state.processing = False
        if not phase1_success:
            st.error("❌ Phase 1 failed")

# ==================== LOG DISPLAY ====================
st.subheader("📝 Processing Log")
log_container = st.container(height=300)
with log_container:
    for log in st.session_state.logs[-20:]:  # Show last 20 logs
        st.text(log)

# ==================== DATA EXPORT ====================
if st.session_state.collection_data and not st.session_state.processing:
    st.divider()
    st.subheader("💾 Export Data")
    
    # Prepare DataFrame
    df = pd.json_normalize(st.session_state.collection_data)
    current_date = datetime.now()
    scrape_date_filename = current_date.strftime("%Y-%b-%d")
    scrape_date_display = current_date.strftime("%Y-%m-%d")
    
    # Add Scrape Date and Card URL columns
    df.insert(0, 'Scrape Date', scrape_date_display)
    if 'collectionCardId' in df.columns:
        df.insert(1, 'Card Unique URL', df['collectionCardId'].apply(
            lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true&backTo=Collection" 
            if pd.notna(x) else None
        ))
    else:
        df.insert(1, 'Card Unique URL', None)
    
    # Create full Excel with reordered columns
    cols = list(df.columns)
    sale_price_cols = sorted([c for c in cols if 'sale' in c and 'price' in c])
    sale_date_cols = sorted([c for c in cols if 'sale' in c and 'date' in c])
    sale_listingtype_cols = sorted([c for c in cols if 'sale' in c and 'listingType' in c])
    special_cols = [c for c in cols if 'avg_last_3_sales' in c or 'sales_count_for_avg' in c]
    other_cols = ['Scrape Date', 'Card Unique URL'] + [c for c in cols if c not in (['Scrape Date', 'Card Unique URL'] + sale_price_cols + sale_date_cols + 
                 sale_listingtype_cols + special_cols)]
    ordered_cols = (other_cols + sale_price_cols + sale_date_cols + sale_listingtype_cols + special_cols)
    df_full = df[ordered_cols]
    df_full_clean = df_full.where(pd.notnull(df_full), None)
    
    # Create filtered Excel
    filtered_columns = ['Scrape Date', 'Card Unique URL', 'label', 'condition', 'variation', 'player', 'currentValue', 'avg_last_3_sales', 'total_sales_in_db']
    available_columns = []
    for col in filtered_columns:
        if col in df.columns:
            available_columns.append(col)
        else:
            matching_cols = [c for c in df.columns if col.lower() in c.lower()]
            if matching_cols:
                available_columns.append(matching_cols[0])
            else:
                available_columns.append(col)
    
    df_filtered = pd.DataFrame()
    for col in available_columns:
        if col in df.columns:
            df_filtered[col] = df[col]
        else:
            df_filtered[col] = None
    df_filtered = df_filtered[available_columns]
    df_filtered_clean = df_filtered.where(pd.notnull(df_filtered), None)
    
    # Export buttons
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        # Full Excel
        output_excel_full = io.BytesIO()
        with pd.ExcelWriter(output_excel_full, engine='openpyxl') as writer:
            df_full_clean.to_excel(writer, index=False, sheet_name='Full Data')
        excel_full_data = output_excel_full.getvalue()
        st.download_button(
            label="📗 Full Excel",
            data=excel_full_data,
            file_name=f"Cardladder_{scrape_date_filename}_full.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col2:
        # Filtered Excel
        output_excel_filtered = io.BytesIO()
        with pd.ExcelWriter(output_excel_filtered, engine='openpyxl') as writer:
            df_filtered_clean.to_excel(writer, index=False, sheet_name='Filtered Data')
        excel_filtered_data = output_excel_filtered.getvalue()
        st.download_button(
            label="📘 Filtered Excel",
            data=excel_filtered_data,
            file_name=f"Filter_cardladder_{scrape_date_filename}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    
    with col3:
        # CSV
        csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
        st.download_button(
            label="📊 CSV",
            data=csv_data,
            file_name=f"collection_{coll_id}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col4:
        # JSON
        json_data = json.dumps(st.session_state.collection_data, indent=2).encode('utf-8')
        st.download_button(
            label="💾 Raw JSON",
            data=json_data,
            file_name=f"collection_{coll_id}.json",
            mime="application/json",
            use_container_width=True
        )
    
    # Google Sheets Export
    if GOOGLE_SHEETS_AVAILABLE:
        st.divider()
        st.subheader("📊 Google Sheets Export")
        
        if st.button("Upload to Google Sheets", use_container_width=True):
            with st.spinner("Connecting to Google Sheets..."):
                try:
                    google_sheets = GoogleSheetsManager()
                    success, message = google_sheets.connect()
                    
                    if success:
                        sheet_name = f"CardLadder_{scrape_date_filename}"
                        spreadsheet, msg = google_sheets.create_or_open_sheet(sheet_name)
                        
                        if spreadsheet:
                            # Save Full Data
                            with st.spinner("Saving full data..."):
                                success, message = google_sheets.save_dataframe_to_sheet(
                                    spreadsheet, "Full Data", df_full_clean
                                )
                                if success:
                                    st.success(message)
                            
                            # Save Filtered Data
                            with st.spinner("Saving filtered data..."):
                                success, message = google_sheets.save_dataframe_to_sheet(
                                    spreadsheet, "Filtered Data", df_filtered_clean
                                )
                                if success:
                                    st.success(message)
                            
                            # Save Summary
                            summary_data = {
                                'Metric': ['Total Cards', 'Cards with Sales', 'Success Rate', 
                                          'Scrape Date', 'Collection ID', 'Mode'],
                                'Value': [len(st.session_state.collection_data), st.session_state.sales_success,
                                         f"{(st.session_state.sales_success/len(st.session_state.collection_data))*100:.1f}%" if len(st.session_state.collection_data) > 0 else "N/A",
                                         scrape_date_display, coll_id, "TEST" if test_mode else "FULL"]
                            }
                            df_summary = pd.DataFrame(summary_data)
                            with st.spinner("Saving summary..."):
                                success, message = google_sheets.save_dataframe_to_sheet(
                                    spreadsheet, "Summary", df_summary
                                )
                                if success:
                                    st.success(message)
                            
                            sheet_url = spreadsheet.url
                            st.success(f"✅ Google Sheets saved!")
                            st.markdown(f"[Open Google Sheet]({sheet_url})")
                        else:
                            st.error(f"Failed to create/open spreadsheet: {msg}")
                    else:
                        st.error(f"Google Sheets connection failed: {message}")
                        
                except Exception as e:
                    st.error(f"Google Sheets error: {str(e)}")
    
    # Data Preview
    st.divider()
    st.subheader("👀 Data Preview")
    st.dataframe(df_filtered_clean.head(20), use_container_width=True)
    
    # Summary Stats
    st.subheader("📈 Summary Statistics")
    if 'currentValue' in df.columns and 'avg_last_3_sales' in df.columns:
        col1, col2, col3 = st.columns(3)
        with col1:
            total_value = df['currentValue'].sum()
            st.metric("Total Current Value", f"${total_value:,.2f}")
        with col2:
            avg_sales = df['avg_last_3_sales'].mean()
            st.metric("Average Last 3 Sales", f"${avg_sales:,.2f}" if not pd.isna(avg_sales) else "N/A")
        with col3:
            if total_value > 0 and not pd.isna(avg_sales):
                diff_percent = ((avg_sales - total_value) / total_value) * 100
                st.metric("Difference", f"{diff_percent:+.1f}%")
