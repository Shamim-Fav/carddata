import streamlit as st
import requests
import json
import time
import pandas as pd
import io
from datetime import datetime
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== GOOGLE SHEETS INTEGRATION ====================
try:
    import gspread
    from google.oauth2.service_account import ServiceAccountCredentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False

# ==================== GOOGLE CREDENTIALS - USING STREAMLIT SECRETS ====================
# For local development, you can hardcode here. For Streamlit Cloud, use secrets.
# In Streamlit Cloud: Go to Settings -> Secrets and paste your credentials

def get_google_credentials():
    """Get Google credentials from Streamlit secrets or local fallback"""
    try:
        # Try to get from Streamlit secrets (for Streamlit Cloud)
        if 'GOOGLE_CREDENTIALS' in st.secrets:
            return st.secrets['GOOGLE_CREDENTIALS']
    except:
        pass
    
    # Fallback: Your hardcoded credentials (REMOVE BEFORE DEPLOYING TO CLOUD)
    # For production, always use Streamlit Secrets
    GOOGLE_CREDENTIALS = {
  "type": "service_account",
  "project_id": "cardladder",
  "private_key_id": "3e910525914e6d6fd55c9d3c08f275e755f004a0",
  "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQCrEOsApOIkbFk2\nqC+dTy0Pp+AtXoeGLI3xUHqMujmzQJ/eS2t/PxPPXUKgDPD4y6zgWCt6/Pen4UUT\nJxxpMCnzkJCclbHYQx1FDTyUIiJg5iAAppfnusFVGO9LM/mHGBTvV8RoRI5u8RXk\nXK+zMsYbm3VR5GBEi1s45E9LOK4A6Rc0CVDkRsgk7Gbii5jYpj+NFVTu1DuNj26a\nGJBDp9+Vk6IBc/uk/4/PDNd9bjkpFOuPJK/SB6c1d3CN3VEYVfFtiltvCl0hhj7U\npqll+Rgukm/GYUSww8lWvnZgTFKOy/ODXEyGri32MWRA7BAPwDk0phTiruX4Gtdb\nQhwku4PvAgMBAAECggEAQNB9KdZPNJu0xae9uq2oFhl2L9p0INs6wKbMeAuLFyay\nK+iJh0HgAJ6GQtwEZU/OZYYim0vDjeEladdUxWoRSw6ILDvvkVAEhAg63ql8OxiW\nIYj9Xzh8TgDPkb/UmGIAdJrdeOAY02IW+FpB2/St6QHi1q9f5jiizJB8lrSYARGw\n6OKq9VfLuNz8g7+iGAigVe6HaN7DFk4o/mVbqVCv0uHwGWyIiXY7+YorG7hMuaVY\nHQUABILi2Y8cp2oQFk6k97IzMlGMkQx8obF8qsnF4Ae7IZYZUG4ucDq/bJK3Ri3v\n4lY03jCG6eWnfjG8Oc/Idm7N1edqEOjRwdLoHp6AMQKBgQDfEI91yqvAdqOlG9oD\nUD+onSzdb0zeD+Y3t9bTHVUGBE9wkokPRektfxpFCdSKhtLD3shQRbYt85FdCMjr\nVUROlI3wsNuj6Opz0GQ+SdLUxtPViD+0MVpGC77SKOEFZXtWCVjcH8xlp+bGQT3H\nd9L7guZ4UObZlGChFH55DKB7eQKBgQDEUueqgAEF6930dhnuHfyp+9PVZQ08rKZo\nNcBaA9rQC7TuBlcFV3CkEeG4J79pOsI5es0BmdXTZpoE+k3Grfpf5zt2O5zk4wb5\n1MLvcT27THgaaNeAKWSt0PNV1B1fPEBq/15OfT1XfidNbhhi+GedPgpAQmzWvrDl\nPvPy6qy4pwKBgQCasThb/s43Lc907Ci3zYooG8AGXG5ZPXtxPnurcpcJEiopLmYA\ngoIfvBpysEuGOdOmZDRUftPFcDlp5HK5ySsSt7DrryrSs+8LnAQ4sieUycIUPmW3\nR9aL5w9RXWoXvPXYh6jpFuA/yz2eVZZLY0ycgX3lCG3fjCeq7bR7rAcLOQKBgQDB\nmdAC/0ADCtpSXLStcLzdFA2N/pzTHJ7tXTRWkD6Tsze1EmN2TQgzg77Hz8qehudJ\nr6PC1GVcl22DQyK3rpGdSXYF3juWK5uRexLQ9ScfMQWvZXw+UpOKJOgR158vb0dH\nPJVPaYm4Yht36/34e2YSVj/dpqOWEW54Y2BGSM4TOQKBgQCxvBuQZAIx2sfGwU1Q\neCRFuTBoYRWirYR3WTo/lK8gRy46uo2rH/V44n9ffnqTMX8y4B46rsQ/0jHeafoB\nQ/ot2lCHfYJDAhk6ElbjukINU5nhDpN+qs8J+xHedBJfQzcxKQYHMRN2M5pu5bT0\nzJrwdPSeU69otasQlvh/D5yPUw==\n-----END PRIVATE KEY-----\n",
  "client_email": "cardladder@cardladder.iam.gserviceaccount.com",
  "client_id": "100678312403939380954",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/cardladder%40cardladder.iam.gserviceaccount.com",
  "universe_domain": "googleapis.com"
}

    
    return GOOGLE_CREDENTIALS

# ==================== SPREADSHEET ID ====================
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Card Ladder Complete Scraper", 
    page_icon="📦",
    layout="wide"
)

# ==================== SESSION STATE ====================
if 'full_data' not in st.session_state:
    st.session_state.full_data = []
if 'sales_data' not in st.session_state:
    st.session_state.sales_data = {}
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'current_phase' not in st.session_state:
    st.session_state.current_phase = ""
if 'logs' not in st.session_state:
    st.session_state.logs = []
if 'stop_requested' not in st.session_state:
    st.session_state.stop_requested = False
if 'google_sheets_manager' not in st.session_state:
    st.session_state.google_sheets_manager = None
if 'spreadsheet_url' not in st.session_state:
    st.session_state.spreadsheet_url = ""
if 'final_df' not in st.session_state:
    st.session_state.final_df = None
if 'google_connected' not in st.session_state:
    st.session_state.google_connected = False

# ==================== HELPER FUNCTIONS ====================
def add_log(message):
    """Add message to logs"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    st.session_state.logs.append(f"[{timestamp}] {message}")
    # Keep only last 100 logs
    if len(st.session_state.logs) > 100:
        st.session_state.logs = st.session_state.logs[-100:]

def clear_logs():
    """Clear all logs"""
    st.session_state.logs = []

def update_status(phase, message):
    """Update current phase status"""
    st.session_state.current_phase = f"{phase}: {message}"

# ==================== GOOGLE SHEETS MANAGER ====================
class GoogleSheetsManager:
    def __init__(self, credentials_dict=None, spreadsheet_id=None):
        self.credentials_dict = credentials_dict
        self.spreadsheet_id = spreadsheet_id
        self.client = None
        self.connected = False
        
    def connect(self):
        """Connect to Google Sheets API"""
        try:
            if not GOOGLE_SHEETS_AVAILABLE:
                return False, "Google Sheets libraries not installed"
                
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
                # Replace NaN with None first
                df_clean[col] = df_clean[col].where(pd.notnull(df_clean[col]), None)
                
                # Convert everything to string for Google Sheets compatibility
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
                pass  # Formatting is optional
            
            return True, f"Data saved to {sheet_name}"
            
        except Exception as e:
            return False, f"Error saving to sheet: {str(e)}"
    
    def get_spreadsheet_url(self, spreadsheet):
        """Get the URL of the spreadsheet"""
        return spreadsheet.url

def connect_to_google_sheets():
    """Connect to Google Sheets"""
    try:
        # Get credentials from secrets or fallback
        credentials = get_google_credentials()
        
        st.session_state.google_sheets_manager = GoogleSheetsManager(
            credentials_dict=credentials,
            spreadsheet_id=SPREADSHEET_ID
        )
        
        success, message = st.session_state.google_sheets_manager.connect()
        
        if success:
            st.session_state.google_connected = True
            add_log(f"✅ {message}")
            return True, message
        else:
            add_log(f"❌ {message}")
            return False, message
            
    except Exception as e:
        add_log(f"❌ Google Sheets connection error: {str(e)}")
        return False, str(e)

# ==================== SIDEBAR ====================
with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150, 
                             help="Copy the 'authorization' header from DevTools.")
    
    st.divider()
    st.header("📊 Google Sheets")
    
    if not GOOGLE_SHEETS_AVAILABLE:
        st.error("Google Sheets libraries not available.")
    else:
        google_status = st.empty()
        
        if st.button("🔗 Connect to Google Sheets", disabled=st.session_state.google_connected):
            with st.spinner("Connecting to Google Sheets..."):
                success, message = connect_to_google_sheets()
                if success:
                    google_status.success("✅ Connected to Google Sheets")
                else:
                    google_status.error(f"❌ {message}")
        
        if st.session_state.google_connected:
            st.success("✅ Google Sheets Connected")
            if st.session_state.spreadsheet_url:
                st.markdown(f"[📊 Open Spreadsheet]({st.session_state.spreadsheet_url})")
    
    st.divider()
    st.header("⚙️ Settings")
    
    collection_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    col1, col2 = st.columns(2)
    with col1:
        max_threads = st.number_input("Max Threads", min_value=1, max_value=10, value=1)
    with col2:
        request_delay = st.number_input("Request Delay (s)", min_value=0.0, max_value=2.0, 
                                      value=0.2, step=0.1)
    
    # Record limit options
    st.subheader("📊 Record Limit")
    limit_option = st.radio(
        "How many records to scrape?",
        ["All Records", "Specific Number"],
        index=0
    )
    
    if limit_option == "Specific Number":
        record_limit = st.number_input("Number of records to scrape:", min_value=1, value=100)
    else:
        record_limit = None
    
    st.divider()
    
    if st.button("🗑️ Clear All Data", type="secondary"):
        st.session_state.full_data = []
        st.session_state.sales_data = {}
        st.session_state.logs = []
        st.session_state.final_df = None
        st.rerun()

# ==================== MAIN UI ====================
st.title("📦 Card Ladder Complete Scraper")
st.markdown("This tool fetches cards from your collection and their last 3 sales data.")

# Google Sheets Status
if st.session_state.google_connected:
    st.success("✅ **Google Sheets Connected** - Data will be saved automatically")
    if st.session_state.spreadsheet_url:
        st.markdown(f"[📊 Open Spreadsheet]({st.session_state.spreadsheet_url})")

# --- Status Display ---
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    if st.session_state.current_phase:
        st.info(f"🔄 **{st.session_state.current_phase}**")
with col2:
    if st.session_state.processing:
        if st.button("⏹️ Stop Process", type="secondary"):
            st.session_state.stop_requested = True
            add_log("Stop requested by user")

# --- Control Buttons ---
col1, col2 = st.columns([1, 3])
with col1:
    start_button = st.button("🚀 Start Complete Process", type="primary", 
                           disabled=st.session_state.processing or not token_input)
with col2:
    if st.button("📝 Clear Logs", disabled=st.session_state.processing):
        clear_logs()
        st.rerun()

# --- Log Display ---
st.subheader("📋 Processing Log")
log_container = st.container()
with log_container:
    if st.session_state.logs:
        log_text = "\n".join(st.session_state.logs[-20:])
        st.code(log_text, language='text')
    else:
        st.info("Logs will appear here when the process starts.")

# ==================== PHASE 1: FETCH COLLECTION ====================
def fetch_collection_phase():
    """Phase 1: Fetch all cards from collection"""
    add_log("=== PHASE 1: Fetching Collection ===")
    update_status("Phase 1", "Fetching collection...")
    
    all_cards = []
    page = 0
    limit = 20
    cards_fetched = 0
    
    headers = {
        'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}",
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0'
    }
    
    try:
        while True and not st.session_state.stop_requested:
            add_log(f"Fetching page {page}...")
            
            params = {
                'index': 'collectioncards',
                'page': page,
                'limit': limit,
                'filters': f'collectionId:{collection_id}|hasQuantityAvailable:true',
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
                add_log(f"❌ Error: Server returned {response.status_code}")
                break
                
            data = response.json()
            hits = data.get('hits', [])
            total = data.get('totalHits', 0)
            
            if not hits:
                break
                
            all_cards.extend(hits)
            cards_fetched += len(hits)
            add_log(f"✅ Page {page}: {len(hits)} cards (Total: {cards_fetched}/{total})")
            
            # Apply record limit if specified
            if record_limit and cards_fetched >= record_limit:
                all_cards = all_cards[:record_limit]
                add_log(f"⚠️ Record limit reached: Limiting to {record_limit} cards")
                break
            
            if cards_fetched >= total or len(hits) < limit:
                break
                
            page += 1
            time.sleep(0.3)
        
        if all_cards:
            st.session_state.full_data = all_cards
            add_log(f"✅ PHASE 1 COMPLETE: Collected {len(all_cards)} cards")
            update_status("Phase 1 Complete", f"{len(all_cards)} cards")
            return True
        else:
            add_log("⚠️ No cards found in collection")
            update_status("Phase 1 Failed", "No cards found")
            return False
            
    except Exception as e:
        add_log(f"❌ Phase 1 Error: {str(e)}")
        update_status("Phase 1 Failed", "Error occurred")
        return False

# ==================== PHASE 2: FETCH SALES DATA ====================
def fetch_sales_for_card(card_data):
    """Fetch last 3 sales for a single card"""
    try:
        headers = {
            'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}",
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0'
        }
        
        # Use label field for search (exact match)
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
            
            # Calculate average of last 3 sales (only for non-None prices)
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
    if not st.session_state.full_data:
        add_log("❌ No collection data to process")
        return 0
    
    add_log(f"\n=== PHASE 2: Fetching Last 3 Sales ===")
    update_status("Phase 2", "Fetching sales data...")
    
    total_cards = len(st.session_state.full_data)
    sales_success = 0
    completed = 0
    
    # Create progress bar
    progress_bar = st.progress(0)
    
    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        futures = []
        for idx, card in enumerate(st.session_state.full_data, 1):
            if st.session_state.stop_requested:
                break
            
            futures.append((executor.submit(fetch_sales_for_card, card), card, idx))
        
        # Process results as they complete
        for future, card, idx in futures:
            if st.session_state.stop_requested:
                break
            
            completed += 1
            result = future.result()
            
            if result:
                # Store sales data in session state
                if idx not in st.session_state.sales_data:
                    st.session_state.sales_data[idx] = {}
                st.session_state.sales_data[idx] = result
                
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
                        add_log(f"✅ [{idx}/{total_cards}] {player}: {sales_found} sales{avg_str} - {', '.join(prices)}")
                    else:
                        add_log(f"✅ [{idx}/{total_cards}] {player}: {sales_found} sales")
                else:
                    add_log(f"⚠️ [{idx}/{total_cards}] {player}: No sales found")
            else:
                player = card.get('player', f'Card {idx}')
                add_log(f"❌ [{idx}/{total_cards}] {player}: Failed to fetch sales")
            
            # Update progress
            progress = completed / total_cards
            progress_bar.progress(progress)
            
            # Rate limiting
            time.sleep(request_delay)
    
    progress_bar.empty()
    return sales_success

# ==================== SAVE RESULTS TO GOOGLE SHEETS ====================
def save_results_to_google_sheets(sales_success):
    """Save results to Google Sheets"""
    if not st.session_state.google_connected:
        return "Google Sheets not connected"
    
    try:
        add_log("📊 Saving to Google Sheets...")
        
        current_date = datetime.now()
        scrape_date_filename = current_date.strftime("%Y-%b-%d")
        scrape_date_display = current_date.strftime("%Y-%m-%d")
        
        # Combine collection data with sales data
        combined_data = []
        for idx, card in enumerate(st.session_state.full_data, 1):
            card_copy = card.copy()
            if idx in st.session_state.sales_data:
                card_copy.update(st.session_state.sales_data[idx])
            card_copy['Scrape Date'] = scrape_date_display
            combined_data.append(card_copy)
        
        # Create DataFrame
        df = pd.json_normalize(combined_data)
        
        # Add Card Unique URL if collectionCardId exists
        if 'collectionCardId' in df.columns:
            df['Card Unique URL'] = df['collectionCardId'].apply(
                lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true&backTo=Collection" 
                if pd.notna(x) else None
            )
            # Move to second position
            cols = list(df.columns)
            cols.remove('Card Unique URL')
            cols.insert(1, 'Card Unique URL')
            df = df[cols]
        
        # Add Scrape Date at beginning
        df.insert(0, 'Scrape Date', scrape_date_display)
        
        # Create full dataframe
        cols = list(df.columns)
        sale_price_cols = sorted([c for c in cols if 'sale' in c and 'price' in c])
        sale_date_cols = sorted([c for c in cols if 'sale' in c and 'date' in c])
        sale_listingtype_cols = sorted([c for c in cols if 'sale' in c and 'listingType' in c])
        special_cols = [c for c in cols if 'avg_last_3_sales' in c or 'sales_count_for_avg' in c]
        other_cols = ['Scrape Date', 'Card Unique URL'] + [c for c in cols if c not in (['Scrape Date', 'Card Unique URL'] + sale_price_cols + sale_date_cols + 
                     sale_listingtype_cols + special_cols)]
        ordered_cols = (other_cols + sale_price_cols + sale_date_cols + sale_listingtype_cols + special_cols)
        df_full = df[ordered_cols]
        
        # Clean NaN values
        df_full_clean = df_full.where(pd.notnull(df_full), None)
        
        # Create filtered dataframe
        filtered_columns = ['Scrape Date', 'Card Unique URL', 'label', 'condition', 'variation', 
                          'player', 'currentValue', 'avg_last_3_sales', 'total_sales_in_db']
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
        
        # Create summary dataframe
        summary_data = {
            'Metric': ['Total Cards', 'Cards with Sales', 'Success Rate', 
                      'Scrape Date', 'Collection ID', 'Mode'],
            'Value': [len(st.session_state.full_data), sales_success,
                     f"{(sales_success/len(st.session_state.full_data))*100:.1f}%" if len(st.session_state.full_data) > 0 else "N/A",
                     scrape_date_display, collection_id, "LIMITED" if record_limit else "FULL"]
        }
        df_summary = pd.DataFrame(summary_data)
        
        # Save to Google Sheets
        sheet_name = f"CardLadder_{scrape_date_filename}"
        spreadsheet, msg = st.session_state.google_sheets_manager.create_or_open_sheet(sheet_name)
        
        if spreadsheet:
            st.session_state.spreadsheet_url = spreadsheet.url
            
            # Save Full Data
            success, message = st.session_state.google_sheets_manager.save_dataframe_to_sheet(
                spreadsheet, "Full Data", df_full_clean
            )
            if success:
                add_log(f"✅ {message}")
            else:
                add_log(f"❌ {message}")
            
            # Save Filtered Data
            success, message = st.session_state.google_sheets_manager.save_dataframe_to_sheet(
                spreadsheet, "Filtered Data", df_filtered_clean
            )
            if success:
                add_log(f"✅ {message}")
            else:
                add_log(f"❌ {message}")
            
            # Save Summary
            success, message = st.session_state.google_sheets_manager.save_dataframe_to_sheet(
                spreadsheet, "Summary", df_summary
            )
            if success:
                add_log(f"✅ {message}")
            else:
                add_log(f"❌ {message}")
            
            add_log(f"✅ Google Sheets saved: {st.session_state.spreadsheet_url}")
            return f"Data saved to Google Sheets: {st.session_state.spreadsheet_url}"
        else:
            add_log(f"❌ Failed to create/open spreadsheet: {msg}")
            return f"Failed: {msg}"
            
    except Exception as e:
        add_log(f"❌ Google Sheets error: {str(e)}")
        return f"Error: {str(e)}"

# ==================== MAIN PROCESS ====================
def run_complete_process():
    """Run the complete process"""
    st.session_state.processing = True
    st.session_state.stop_requested = False
    st.session_state.sales_data = {}
    
    try:
        # Phase 1: Fetch collection
        phase1_success = fetch_collection_phase()
        
        if not phase1_success or st.session_state.stop_requested:
            return
        
        # Phase 2: Fetch sales data
        sales_success = fetch_sales_for_all_cards()
        
        # Prepare final data for display and download
        if st.session_state.full_data and not st.session_state.stop_requested:
            prepare_final_data(sales_success)
            
    except Exception as e:
        add_log(f"❌ Process Error: {str(e)}")
    finally:
        st.session_state.processing = False
        update_status("Complete", "Process finished")
        if st.session_state.stop_requested:
            add_log("⏹️ Process stopped by user")

def prepare_final_data(sales_success):
    """Prepare final data for display and download"""
    try:
        current_date = datetime.now()
        scrape_date_display = current_date.strftime("%Y-%m-%d")
        
        # Combine collection data with sales data
        combined_data = []
        for idx, card in enumerate(st.session_state.full_data, 1):
            card_copy = card.copy()
            if idx in st.session_state.sales_data:
                card_copy.update(st.session_state.sales_data[idx])
            card_copy['Scrape Date'] = scrape_date_display
            combined_data.append(card_copy)
        
        # Create DataFrame
        df = pd.json_normalize(combined_data)
        
        # Add Card Unique URL if collectionCardId exists
        if 'collectionCardId' in df.columns:
            df['Card Unique URL'] = df['collectionCardId'].apply(
                lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true&backTo=Collection" 
                if pd.notna(x) else None
            )
            # Move to second position
            cols = list(df.columns)
            cols.remove('Card Unique URL')
            cols.insert(1, 'Card Unique URL')
            df = df[cols]
        
        # Store in session state
        st.session_state.final_df = df
        
        # Save to Google Sheets if connected
        if st.session_state.google_connected:
            google_sheets_result = save_results_to_google_sheets(sales_success)
            add_log(google_sheets_result)
        
        # Show summary
        add_log(f"\n{'='*60}")
        add_log("✨ PROCESS COMPLETE!")
        add_log(f"{'='*60}")
        add_log(f"✅ Total cards: {len(combined_data)}")
        add_log(f"✅ Cards with sales data: {sales_success}")
        
        if sales_success > 0:
            avg_values = []
            current_values = []
            for card in combined_data:
                if 'avg_last_3_sales' in card and card['avg_last_3_sales'] is not None:
                    avg_values.append(card['avg_last_3_sales'])
                if 'currentValue' in card and card['currentValue'] is not None:
                    current_values.append(card['currentValue'])
            if avg_values:
                overall_avg = sum(avg_values) / len(avg_values)
                add_log(f"📊 Overall average of last 3 sales: ${overall_avg:.2f}")
            if current_values:
                overall_current = sum(current_values) / len(current_values)
                add_log(f"📊 Overall average current value: ${overall_current:.2f}")
        
        if len(combined_data) > 0:
            success_rate = (sales_success / len(combined_data)) * 100
            add_log(f"✅ Success rate: {success_rate:.1f}%")
        
        update_status("Complete", f"{sales_success}/{len(combined_data)} cards have sales")
        
    except Exception as e:
        add_log(f"❌ Error preparing data: {str(e)}")

# ==================== START PROCESS ====================
if start_button and token_input:
    if not st.session_state.processing:
        # Run in separate thread to avoid blocking
        thread = threading.Thread(target=run_complete_process, daemon=True)
        thread.start()
        st.rerun()
else:
    if start_button and not token_input:
        st.error("Please provide a token in the sidebar!")

# ==================== DISPLAY RESULTS & DOWNLOADS ====================
if st.session_state.final_df is not None and not st.session_state.processing:
    st.divider()
    st.subheader("📊 Export Results")
    
    df = st.session_state.final_df
    
    # Create export options
    col1, col2, col3 = st.columns(3)
    
    # 1. Full Excel Export
    full_excel_name = f"Cardladder_{datetime.now().strftime('%Y-%b-%d')}_full.xlsx"
    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Collection')
    excel_data = output_excel.getvalue()
    col1.download_button("📗 Download Full Excel", data=excel_data, file_name=full_excel_name)
    
    # 2. Filtered Excel Export
    filtered_excel_name = f"Filter_cardladder_{datetime.now().strftime('%Y-%b-%d')}.xlsx"
    filtered_columns = ['Scrape Date', 'Card Unique URL', 'label', 'condition', 'variation', 
                       'player', 'currentValue', 'avg_last_3_sales', 'total_sales_in_db']
    # Find available columns
    available_columns = []
    for col in filtered_columns:
        if col in df.columns:
            available_columns.append(col)
        else:
            matching_cols = [c for c in df.columns if col.lower() in c.lower()]
            if matching_cols:
                available_columns.append(matching_cols[0])
    
    if available_columns:
        df_filtered = df[available_columns]
        output_filtered = io.BytesIO()
        with pd.ExcelWriter(output_filtered, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False, sheet_name='Filtered')
        filtered_data = output_filtered.getvalue()
        col2.download_button("📘 Download Filtered Excel", data=filtered_data, file_name=filtered_excel_name)
    
    # 3. JSON Export
    json_name = f"collection_{datetime.now().strftime('%Y%m%d')}.json"
    # Prepare data for JSON export
    export_data = []
    for idx, card in enumerate(st.session_state.full_data, 1):
        card_copy = card.copy()
        if idx in st.session_state.sales_data:
            card_copy.update(st.session_state.sales_data[idx])
        export_data.append(card_copy)
    
    json_data = json.dumps(export_data, indent=2).encode('utf-8')
    col3.download_button("💾 Download Raw JSON", data=json_data, file_name=json_name)
    
    # Google Sheets URL
    if st.session_state.spreadsheet_url:
        st.markdown(f"**Google Sheets:** [📊 Open Spreadsheet]({st.session_state.spreadsheet_url})")
    
    # Data Preview
    st.subheader("👀 Data Preview")
    st.dataframe(df.head(50), use_container_width=True)
    
    # Summary Metrics
    st.subheader("📈 Collection Snapshot")
    col1, col2, col3, col4 = st.columns(4)
    
    total_cards = len(df)
    col1.metric("Total Cards", total_cards)
    
    if 'currentValue' in df.columns:
        market_value = df['currentValue'].sum()
        col2.metric("Market Value", f"${market_value:,.2f}")
    
    if 'avg_last_3_sales' in df.columns:
        avg_sales = df['avg_last_3_sales'].mean()
        col3.metric("Avg Last 3 Sales", f"${avg_sales:,.2f}" if not pd.isna(avg_sales) else "N/A")
    
    if 'investment' in df.columns:
        cost_basis = df['investment'].sum()
        col4.metric("Cost Basis", f"${cost_basis:,.2f}")

# ==================== AUTO-REFRESH ====================
if st.session_state.processing:
    st.rerun()
