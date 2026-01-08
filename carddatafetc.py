import streamlit as st
import requests
import json
import time
import pandas as pd
import io
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- Page Config ---
st.set_page_config(
    page_title="Card Ladder Complete Scraper", 
    page_icon="📦",
    layout="wide"
)

# Initialize session state
if 'full_data' not in st.session_state:
    st.session_state.full_data = []
if 'total_found' not in st.session_state:
    st.session_state.total_found = 0
if 'sales_data_processed' not in st.session_state:
    st.session_state.sales_data_processed = 0
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'stop_requested' not in st.session_state:
    st.session_state.stop_requested = False
if 'log_messages' not in st.session_state:
    st.session_state.log_messages = []
if 'progress_value' not in st.session_state:
    st.session_state.progress_value = 0
if 'current_phase' not in st.session_state:
    st.session_state.current_phase = ""
if 'thread_running' not in st.session_state:
    st.session_state.thread_running = False

# --- Google Sheets Configuration ---
GOOGLE_CREDENTIALS =GOOGLE_CREDENTIALS ={
  "type": "service_account",
  "project_id": "cardladder",
  "private_key_id": "8a99314852d5823a123ed7f1231af473e1ca3732",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvgIBADANBgkqhkiG9w0BAQEFAASCBKgwggSkAgEAAoIBAQC4JxRv2ogJ6c6R\neB2xb+UPJ63Dq5UH4sFq92ULm613qsXgGaWiItwf3XknKV1tftbxpb4RuQhr+5Jx\nxxdcgGs4EZgyoyCXgOrdZUQtcJG2GQZm/5OBgAQuKgy85qsKduQlQafMIH842YS7\nW1T7hDAPdr/upDYEdL6Wj9DhNthwzwxtBApM//zuIPI7UhLo4JcMap7hvFan9N4H\nIka8lw1xsYTKVOgT+b6lAwDwnD+I+/EVbAFVtZbqZD0f71v+AwlterMtX3mHIlt8\nxLuOTLcbFd9aZCHWuEylgijxxmRxDISROE24GIcQ62+fSqTpCirqzHvTnZh+1t3y\nSxMgYvwzAgMBAAECggEAErPlX3bSWi9ky2Fnop26pc9h1n2WpTZibnqxyHwHIiA1\n+IyiRdVEhff4VgHde0FmkyRCKYqhUFY8iVGvDbX9LbSbwIjQxpJRSCsAwZytL9Fa\n1Rsf4AcgZY/fu0+yD14DzcTdRd4HDb8Ju/2KpADI4MkutQ34bnts3927WSQ41zwD\nmh99SUVF/ItquSDBlovaHw7ldaJ4EItkPeRstM5JKgCMaj5YA2d9pgJghddJySou\ngTiYExWU1MnlIiZ0wiNs+PM862d4MEfDpOBpnMFLSXx3GA88bkSIZZRwB9gRg38I\n+TNySi2v1EDcaxlm7WGbwD+2tdWi7XmcSDdYBL5wAQKBgQD0/84k6k63oeE5cxIn\nqT49tWMdViUDg+o3jmbCaIcLjMlFpWo6dHe0vAuKEinPtCHohaz6yl5I+2FW2x03\nFLZCcI8nw0vuAoGQPY0UsxqgxXPAexHkkoJclOgKnaGPMxjH1XAQkDDzspVX85A8\nyl9vicZLTIHJ4z4oSLLn/GFVdwKBgQDAa9xhWzWbYbu//fZGqPahiSTe6NMbBl7G\nHVJ+b1UCMNdia+M08MH/i21d7/4kvLL4H3khLAvsTdRdMK7NMjdF5YcC2ehUc2Yu\nc/wEgO4V630s2iea5qKawLlJjHKgfVDLzSaQ8IVYN4pf04EZFvQ6E6j/svECLjDz\nIXR3mUvuJQKBgQDDkEGj0+hbynr2mbTfNcg6B8UDENVg1faqvB+ohTlu7cVns590\n46z99rCbWN5JLnd2nOW0Fr9mMErFwweyBPVrWV/cFJdSeGulkIxB/ql9tb8s4NAq\njQxEDJSgjKz+moHoWaYngoGgtWdimkgDTmMZrHc9eeeMGLlv/H/aj+m+BwKBgEMr\nI6HEcgEMa7qIT1i5EGaw9fLt+Qsc/SZRBAPonxcFr5nGqWhIhp/KruG0rdVrHVop\numHO+1aAkJn7LXmphsvaZHelU0lvgwLCL/3ud62lJ2vptxuGWMqGbedzpGvLctHB\nii3cF+AEe0QaE52LerNvO3YOo7ysHSAx1HMPSwcVAoGBAK/OyNSO3FPBjcIiXINB\nOF2a/dr7FIYS0IosGozmbwT/6KNoGIo/NXsmJB4TqM/1nH7FMRIUMVsNo4abOPbO\nAIfT82Dkjv6/e+yQZQIxGAueJvVZ74hWNPLlm+ii4kJPiY2LtDv+cZgw413BnosP\nrkE5iww8l6ixZWhF6JCBCn8M\n-----END PRIVATE KEY-----\n",
  "client_email": "cardladder@cardladder.iam.gserviceaccount.com",
  "client_id": "100678312403939380954",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/cardladder%40cardladder.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

class GoogleSheetsManager:
    def __init__(self, credentials_dict=None, spreadsheet_id=None):
        self.credentials_dict = credentials_dict or GOOGLE_CREDENTIALS
        self.spreadsheet_id = spreadsheet_id or SPREADSHEET_ID
        self.client = None
        self.connected = False
        
    def connect(self):
        """Connect to Google Sheets API"""
        try:
            if not self.credentials_dict:
                return False, "No credentials provided"
            
            # Define the scope
            scope = ['https://spreadsheets.google.com/feeds',
                    'https://www.googleapis.com/auth/drive']
            
            # Create credentials from dictionary
            credentials = ServiceAccountCredentials.from_json_keyfile_dict(
                self.credentials_dict, scope)
            
            # Authorize the client
            self.client = gspread.authorize(credentials)
            self.connected = True
            return True, "Connected to Google Sheets API"
            
        except Exception as e:
            return False, f"Connection error: {str(e)}"
    
    def create_or_open_sheet(self, sheet_name):
        """Create a new sheet or open existing one"""
        try:
            if not self.connected:
                success, message = self.connect()
                if not success:
                    return None, message
            
            if self.spreadsheet_id:
                # Open existing spreadsheet by ID
                spreadsheet = self.client.open_by_key(self.spreadsheet_id)
            else:
                # Create new spreadsheet
                spreadsheet = self.client.create(sheet_name)
                self.spreadsheet_id = spreadsheet.id
            
            return spreadsheet, "Success"
            
        except Exception as e:
            return None, f"Error accessing sheet: {str(e)}"
    
    def save_dataframe_to_sheet(self, spreadsheet, sheet_name, df, clear_existing=True):
        """Save pandas DataFrame to Google Sheet"""
        try:
            # Create a clean DataFrame copy
            df_clean = df.copy()
            
            # Convert all columns to string type
            for col in df_clean.columns:
                df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), None)
                df_clean[col] = df_clean[col].astype(str)
            
            # Convert to list for Google Sheets
            data = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
            
            # Try to open existing worksheet
            try:
                worksheet = spreadsheet.worksheet(sheet_name)
                if clear_existing:
                    worksheet.clear()
            except gspread.exceptions.WorksheetNotFound:
                # Create new worksheet
                worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=26)
            
            # Update worksheet with data
            worksheet.update(data, value_input_option='USER_ENTERED')
            
            # Format header row
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
        """Get the URL of the spreadsheet"""
        return spreadsheet.url

# --- Styling ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; }
    .start-button { background-color: #007acc !important; color: white !important; }
    .stop-button { background-color: #cc0000 !important; color: white !important; }
    .download-button { background-color: #00aa55 !important; color: white !important; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; }
    .metric-card { background-color: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar: Authentication & Settings ---
with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150, 
                              help="Copy the 'authorization' header from DevTools.")
    
    st.divider()
    st.header("⚙️ Settings")
    
    # Collection ID
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    # Max Threads
    max_workers = st.slider("Max Threads", min_value=1, max_value=10, value=1)
    
    # How many records
    st.divider()
    st.header("📊 Records Selection")
    record_option = st.radio("How many records?", ["All Records", "Specific Number"])
    
    if record_option == "Specific Number":
        record_count = st.number_input("Number of records to fetch", min_value=1, value=50)
    else:
        record_count = None
    
    st.divider()
    
    # Google Sheets toggle
    use_google_sheets = st.checkbox("Save to Google Sheets", value=True)
    
    st.divider()
    # Clear Data Button
    if st.button("🗑️ Clear All Data", use_container_width=True):
        st.session_state.full_data = []
        st.session_state.total_found = 0
        st.session_state.sales_data_processed = 0
        st.session_state.log_messages = []
        st.session_state.progress_value = 0
        st.session_state.current_phase = ""
        st.session_state.processing = False
        st.session_state.stop_requested = False
        st.session_state.thread_running = False
        st.rerun()

# --- Main UI ---
st.title("📦 Card Ladder Complete Scraper")
st.info("This tool fetches cards from collection and their last 3 sales data.")

# Status display
status_col1, status_col2, status_col3 = st.columns(3)
with status_col1:
    if st.session_state.processing:
        st.success(f"🔄 {st.session_state.current_phase}")
    elif st.session_state.full_data:
        st.success("✅ Process Complete!")
    else:
        st.info("Ready to start")
        
with status_col2:
    if st.session_state.processing:
        progress_bar = st.progress(st.session_state.progress_value)
    else:
        progress_bar = st.progress(0)
        
with status_col3:
    if st.session_state.stop_requested:
        st.warning("🛑 Stop requested")

# Log display
log_expander = st.expander("📝 Processing Log", expanded=True)
with log_expander:
    if st.session_state.log_messages:
        st.text_area("", value="\n".join(st.session_state.log_messages[-20:]), 
                    height=200, label_visibility="collapsed")
    else:
        st.info("Log will appear here when processing starts")

# Control Buttons
col1, col2 = st.columns([2, 1])
with col1:
    start_button = st.button("🚀 Start Complete Process", 
                           key="start", 
                           use_container_width=True, 
                           type="primary", 
                           disabled=st.session_state.processing)
with col2:
    stop_button = st.button("⏹️ Stop Process", 
                          key="stop", 
                          use_container_width=True,
                          disabled=not st.session_state.processing)

# --- Functions ---
def log_message(message):
    """Add message to log"""
    st.session_state.log_messages.append(f"[{datetime.now().strftime('%H:%M:%S')}] {message}")
    # Keep only last 100 messages
    if len(st.session_state.log_messages) > 100:
        st.session_state.log_messages = st.session_state.log_messages[-100:]

def fetch_collection_data():
    """Phase 1: Fetch all cards from collection"""
    all_cards = []
    page = 0
    limit = 20
    
    headers = {
        'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}",
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0',
        'Cache-Control': 'no-cache'
    }
    
    log_message("=== PHASE 1: Fetching Collection ===")
    st.session_state.current_phase = "Phase 1: Fetching collection..."
    
    try:
        while True and not st.session_state.stop_requested:
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
                timeout=20
            )
            
            if response.status_code != 200:
                log_message(f"❌ Error: Server returned {response.status_code}")
                break
                
            data = response.json()
            hits = data.get('hits', [])
            total = data.get('totalHits', 0)
            st.session_state.total_found = total
            
            if not hits:
                break
                
            all_cards.extend(hits)
            log_message(f"✅ Page {page}: {len(hits)} cards (Total: {len(all_cards)}/{total})")
            
            # Apply record count limit if specified
            if record_count and len(all_cards) >= record_count:
                all_cards = all_cards[:record_count]
                log_message(f"⚠️ Limiting to {record_count} records as requested")
                break
            
            if len(all_cards) >= total or len(hits) < limit:
                break
                
            page += 1
            time.sleep(0.3)
        
        return all_cards
            
    except Exception as e:
        log_message(f"❌ Phase 1 Error: {str(e)}")
        return []

def fetch_sales_for_card(card_data):
    """Fetch last 3 sales for a single card"""
    try:
        headers = {
            'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}",
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0'
        }
        
        # Use label field for search
        label = card_data.get('label', '')
        player = card_data.get('player', 'N/A')
        
        if not label:
            # Build label from components if not available
            year = card_data.get('year', '')
            number = card_data.get('number', '')
            condition = card_data.get('condition', '')
            card_set = card_data.get('set', '')
            player = card_data.get('player', '')
            
            label = f"{year} {card_set} {player} #{number} {condition}"
        
        # Search sales archive using label
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
            total = data.get('totalHits', 0)
            
            # Prepare sales data
            sales_info = {
                'sales_search_query': label,
                'total_sales_in_db': total,
                'sales_found': len(hits)
            }
            
            # Get last 3 sales
            last_three = hits[:3]
            
            # Collect prices for average calculation
            sale_prices = []
            
            for i, sale in enumerate(last_three, 1):
                price = sale.get('price')
                date = sale.get('date', '')
                listing_type = sale.get('listingType', '')
                
                # Collect price for average calculation
                if price is not None:
                    sale_prices.append(price)
                
                # Format date
                if date and 'T' in date:
                    try:
                        dt = datetime.fromisoformat(date.replace('Z', '+00:00'))
                        date = dt.strftime('%Y-%m-%d')
                    except:
                        pass
                
                sales_info[f'sale{i}_price'] = price
                sales_info[f'sale{i}_date'] = date
                sales_info[f'sale{i}_listingType'] = listing_type
            
            # Fill empty slots if less than 3 sales
            for i in range(len(last_three) + 1, 4):
                sales_info[f'sale{i}_price'] = None
                sales_info[f'sale{i}_date'] = None
                sales_info[f'sale{i}_listingType'] = None
            
            # Calculate average of last 3 sales
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

def fetch_sales_for_all_cards(cards):
    """Fetch sales for all collected cards"""
    if not cards:
        log_message("❌ No collection data to process")
        return 0, []
    
    log_message(f"\n=== PHASE 2: Fetching Last 3 Sales ===")
    st.session_state.current_phase = "Phase 2: Fetching sales data..."
    
    total_cards = len(cards)
    sales_success = 0
    processed_cards = []
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, card in enumerate(cards, 1):
            if st.session_state.stop_requested:
                break
            
            futures.append((executor.submit(fetch_sales_for_card, card), card, idx))
        
        # Process results as they complete
        completed = 0
        for future, card, idx in futures:
            if st.session_state.stop_requested:
                break
            
            completed += 1
            result = future.result()
            
            if result:
                # Merge sales data into card
                card.update(result)
                sales_success += 1
                processed_cards.append(card)
                
                player = card.get('player', f'Card {idx}')
                sales_found = result.get('sales_found', 0)
                avg_price = result.get('avg_last_3_sales')
                
                if sales_found > 0:
                    log_message(f"✅ [{idx}/{total_cards}] {player}: {sales_found} sales, Avg: ${avg_price:.2f}" if avg_price else f"✅ [{idx}/{total_cards}] {player}: {sales_found} sales")
                else:
                    log_message(f"⚠️ [{idx}/{total_cards}] {player}: No sales found")
            else:
                player = card.get('player', f'Card {idx}')
                log_message(f"❌ [{idx}/{total_cards}] {player}: Failed to fetch sales")
            
            # Update progress
            progress = (completed / total_cards) * 100
            st.session_state.progress_value = progress / 100
            
            # Rate limiting
            time.sleep(0.2)
    
    return sales_success, processed_cards

def save_to_google_sheets(df_full, df_filtered, sales_success):
    """Save data to Google Sheets"""
    try:
        google_sheets = GoogleSheetsManager()
        success, message = google_sheets.connect()
        
        if not success:
            log_message(f"❌ Google Sheets connection failed: {message}")
            return None
        
        # Create or open spreadsheet
        current_date = datetime.now().strftime("%Y-%b-%d")
        sheet_name = f"CardLadder_{current_date}"
        
        spreadsheet, msg = google_sheets.create_or_open_sheet(sheet_name)
        
        if not spreadsheet:
            log_message(f"❌ Failed to create/open spreadsheet: {msg}")
            return None
        
        # Save Full Data
        log_message("📊 Saving full data to Google Sheets...")
        success, message = google_sheets.save_dataframe_to_sheet(
            spreadsheet, "Full Data", df_full
        )
        if success:
            log_message(f"✅ {message}")
        
        # Save Filtered Data
        log_message("📊 Saving filtered data to Google Sheets...")
        success, message = google_sheets.save_dataframe_to_sheet(
            spreadsheet, "Filtered Data", df_filtered
        )
        if success:
            log_message(f"✅ {message}")
        
        # Save Summary
        summary_data = {
            'Metric': ['Total Cards', 'Cards with Sales', 'Success Rate', 
                      'Scrape Date', 'Collection ID'],
            'Value': [len(df_full), sales_success,
                     f"{(sales_success/len(df_full))*100:.1f}%" if len(df_full) > 0 else "N/A",
                     datetime.now().strftime("%Y-%m-%d"), coll_id]
        }
        df_summary = pd.DataFrame(summary_data)
        success, message = google_sheets.save_dataframe_to_sheet(
            spreadsheet, "Summary", df_summary
        )
        if success:
            log_message(f"✅ Summary saved")
        
        # Get URL
        sheet_url = spreadsheet.url
        log_message(f"✅ Google Sheets saved: {sheet_url}")
        
        return sheet_url
        
    except Exception as e:
        log_message(f"❌ Google Sheets error: {str(e)}")
        return None

# --- Main Processing Function ---
def run_complete_process():
    """Run the complete two-phase process"""
    try:
        # Clear previous data
        st.session_state.full_data = []
        st.session_state.sales_data_processed = 0
        st.session_state.progress_value = 0
        
        # Phase 1: Fetch collection
        log_message("Starting Phase 1: Fetching collection data...")
        st.session_state.current_phase = "Phase 1: Fetching collection..."
        collection_cards = fetch_collection_data()
        
        if not collection_cards or st.session_state.stop_requested:
            log_message("Process stopped or no cards found")
            st.session_state.processing = False
            st.session_state.thread_running = False
            return
        
        log_message(f"✅ Phase 1 Complete: Collected {len(collection_cards)} cards")
        
        # Phase 2: Fetch sales data
        log_message("Starting Phase 2: Fetching sales data...")
        st.session_state.current_phase = "Phase 2: Fetching sales data..."
        st.session_state.progress_value = 0
        
        sales_success, processed_cards = fetch_sales_for_all_cards(collection_cards)
        
        if st.session_state.stop_requested:
            log_message("Process stopped by user")
            st.session_state.processing = False
            st.session_state.thread_running = False
            return
        
        st.session_state.full_data = processed_cards
        st.session_state.sales_data_processed = sales_success
        
        # Save results
        if processed_cards:
            current_date = datetime.now()
            scrape_date_filename = current_date.strftime("%Y-%b-%d")
            scrape_date_display = current_date.strftime("%Y-%m-%d")
            
            # Create DataFrame
            df = pd.json_normalize(processed_cards)
            
            # Add Scrape Date and Card URL
            df.insert(0, 'Scrape Date', scrape_date_display)
            if 'collectionCardId' in df.columns:
                df.insert(1, 'Card Unique URL', df['collectionCardId'].apply(
                    lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true&backTo=Collection" 
                    if pd.notna(x) else None
                ))
            
            # Create full Excel file
            full_excel_name = f"Cardladder_{scrape_date_filename}_full.xlsx"
            df.to_excel(full_excel_name, index=False)
            
            # Create filtered Excel file
            filtered_excel_name = f"Filter_cardladder_{scrape_date_filename}.xlsx"
            filtered_columns = ['Scrape Date', 'Card Unique URL', 'label', 'condition', 
                              'variation', 'player', 'currentValue', 'avg_last_3_sales', 
                              'total_sales_in_db']
            available_columns = [col for col in filtered_columns if col in df.columns]
            df_filtered = df[available_columns]
            df_filtered.to_excel(filtered_excel_name, index=False)
            
            log_message(f"📗 Full Excel saved: {full_excel_name}")
            log_message(f"📘 Filtered Excel saved: {filtered_excel_name}")
            
            # Save to Google Sheets if enabled
            if use_google_sheets:
                sheet_url = save_to_google_sheets(df, df_filtered, sales_success)
                if sheet_url:
                    log_message(f"📊 Google Sheets URL: {sheet_url}")
            
            # Show summary
            log_message(f"\n{'='*60}")
            log_message("✨ PROCESS COMPLETE!")
            log_message(f"{'='*60}")
            log_message(f"✅ Total cards: {len(processed_cards)}")
            log_message(f"✅ Cards with sales data: {sales_success}")
            
            if sales_success > 0:
                success_rate = (sales_success / len(processed_cards)) * 100
                log_message(f"✅ Success rate: {success_rate:.1f}%")
        
        st.session_state.current_phase = "Process Complete!"
        st.session_state.progress_value = 1.0
        st.session_state.processing = False
        st.session_state.thread_running = False
        
    except Exception as e:
        log_message(f"❌ Process Error: {str(e)}")
        st.session_state.processing = False
        st.session_state.thread_running = False

# --- Handle Start Button ---
if start_button and token_input and not st.session_state.processing:
    # Reset state
    st.session_state.full_data = []
    st.session_state.sales_data_processed = 0
    st.session_state.log_messages = []
    st.session_state.progress_value = 0
    st.session_state.current_phase = ""
    st.session_state.processing = True
    st.session_state.stop_requested = False
    st.session_state.thread_running = True
    
    # Start processing in a separate thread
    thread = threading.Thread(target=run_complete_process)
    thread.daemon = True
    thread.start()
    
    # Show immediate feedback
    st.rerun()

# --- Handle Stop Button ---
if stop_button and st.session_state.processing:
    st.session_state.stop_requested = True
    st.session_state.current_phase = "Stopping..."
    log_message("⏹️ Stop requested by user")

# --- Auto-refresh while processing ---
if st.session_state.processing:
    # Auto-refresh every 2 seconds while processing
    time.sleep(2)
    st.rerun()

# --- Data Display & Downloads ---
if st.session_state.full_data and not st.session_state.processing:
    st.divider()
    
    # Summary Metrics
    st.subheader("📈 Collection Snapshot")
    m1, m2, m3, m4, m5 = st.columns(5)
    
    df = pd.json_normalize(st.session_state.full_data)
    
    m1.metric("Total Cards", len(df))
    m2.metric("Cards with Sales", st.session_state.sales_data_processed)
    if st.session_state.sales_data_processed > 0:
        success_rate = (st.session_state.sales_data_processed / len(df)) * 100
        m3.metric("Success Rate", f"{success_rate:.1f}%")
    
    if 'currentValue' in df.columns:
        total_value = df['currentValue'].sum()
        m4.metric("Total Current Value", f"${total_value:,.2f}")
    
    if 'avg_last_3_sales' in df.columns:
        avg_sales = df['avg_last_3_sales'].mean()
        m5.metric("Avg Last 3 Sales", f"${avg_sales:,.2f}" if not pd.isna(avg_sales) else "N/A")
    
    # Export Section
    st.subheader("📊 Export Results")
    c1, c2, c3, c4 = st.columns(4)
    
    # 1. Full Excel Export
    current_date = datetime.now().strftime("%Y-%b-%d")
    output_excel_full = io.BytesIO()
    with pd.ExcelWriter(output_excel_full, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Full Collection')
    excel_full_data = output_excel_full.getvalue()
    
    c1.download_button(
        "📗 Download Full Excel", 
        data=excel_full_data, 
        file_name=f"Cardladder_{current_date}_full.xlsx", 
        use_container_width=True
    )
    
    # 2. Filtered Excel Export
    filtered_columns = ['Scrape Date', 'Card Unique URL', 'label', 'condition', 
                       'variation', 'player', 'currentValue', 'avg_last_3_sales', 
                       'total_sales_in_db']
    available_columns = [col for col in filtered_columns if col in df.columns]
    df_filtered = df[available_columns]
    
    output_excel_filtered = io.BytesIO()
    with pd.ExcelWriter(output_excel_filtered, engine='openpyxl') as writer:
        df_filtered.to_excel(writer, index=False, sheet_name='Filtered')
    excel_filtered_data = output_excel_filtered.getvalue()
    
    c2.download_button(
        "📘 Download Filtered Excel", 
        data=excel_filtered_data, 
        file_name=f"Filter_cardladder_{current_date}.xlsx", 
        use_container_width=True
    )
    
    # 3. CSV Export
    csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
    c3.download_button(
        "📊 Download CSV", 
        data=csv_data, 
        file_name=f"collection_{coll_id}.csv", 
        use_container_width=True
    )
    
    # 4. JSON Export
    json_data = json.dumps(st.session_state.full_data, indent=2).encode('utf-8')
    c4.download_button(
        "💾 Download Raw JSON", 
        data=json_data, 
        file_name=f"collection_{coll_id}.json", 
        use_container_width=True
    )
    
    # Data Preview
    st.subheader("👀 Data Preview")
    st.dataframe(df, use_container_width=True, height=400)
