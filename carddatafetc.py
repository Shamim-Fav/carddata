import requests
import json
import time
import pandas as pd
import streamlit as st
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import io

# ==================== GOOGLE SHEETS INTEGRATION ====================
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    st.warning("Google Sheets libraries not installed. Run: pip install gspread oauth2client")

# ==================== HARDCODED CREDENTIALS (KEEP AS IS) ====================
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

# ==================== YOUR SPREADSHEET ID ====================
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

# ==================== STREAMLIT PAGE CONFIG ====================
st.set_page_config(
    page_title="Card Ladder Scraper",
    page_icon="📊",
    layout="wide"
)

# ==================== SESSION STATE INITIALIZATION ====================
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'collection_data' not in st.session_state:
    st.session_state.collection_data = []
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'sales_success' not in st.session_state:
    st.session_state.sales_success = 0
if 'logs' not in st.session_state:
    st.session_state.logs = []

# ==================== HELPER FUNCTIONS ====================
def add_log(msg):
    """Add a log message to session state"""
    timestamp = datetime.now().strftime('%H:%M:%S')
    st.session_state.logs.append(f"[{timestamp}] {msg}")

def clear_logs():
    """Clear all logs"""
    st.session_state.logs = []

# ==================== GOOGLE SHEETS MANAGER ====================
class GoogleSheetsManager:
    def __init__(self, credentials_dict=None, spreadsheet_id=None):
        self.credentials_dict = credentials_dict or GOOGLE_CREDENTIALS
        self.spreadsheet_id = spreadsheet_id or SPREADSHEET_ID
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

# ==================== SCRAPING FUNCTIONS ====================
def fetch_collection(coll_id, auth_token, fetch_all=True, record_limit=50):
    """Fetch cards from collection based on user selection"""
    all_cards = []
    page = 0
    limit = 20
    
    headers = {
        'authorization': auth_token,
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0'
    }
    
    add_log(f"=== PHASE 1: Fetching Collection ===")
    
    if fetch_all:
        add_log("📊 Mode: Fetching ALL records from collection")
    else:
        add_log(f"📊 Mode: Fetching up to {record_limit} records")
    
    try:
        while True and not st.session_state.get('stop_processing', False):
            add_log(f"Fetching page {page}...")
            
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
                add_log(f"❌ Error: Server returned {response.status_code}")
                break
                
            data = response.json()
            hits = data.get('hits', [])
            total = data.get('totalHits', 0)
            
            if not hits:
                break
                
            all_cards.extend(hits)
            add_log(f"✅ Page {page}: {len(hits)} cards (Total: {len(all_cards)}/{total})")
            
            # Check if we've reached the user's limit
            if not fetch_all and len(all_cards) >= record_limit:
                all_cards = all_cards[:record_limit]
                add_log(f"📊 Reached user limit of {record_limit} cards")
                break
            
            if fetch_all and (len(all_cards) >= total or len(hits) < limit):
                break
                
            page += 1
            time.sleep(0.3)
        
        if all_cards:
            if fetch_all:
                add_log(f"✅ PHASE 1 COMPLETE: Collected ALL {len(all_cards)} cards from collection")
            else:
                add_log(f"✅ PHASE 1 COMPLETE: Collected {len(all_cards)} cards (User limit: {record_limit})")
            
            return True, all_cards
        else:
            add_log("⚠️ No cards found in collection")
            return False, []
            
    except Exception as e:
        add_log(f"❌ Phase 1 Error: {str(e)}")
        return False, []

def fetch_sales_for_card(card_data, auth_token):
    """Fetch last 3 sales for a single card"""
    try:
        headers = {
            'authorization': auth_token,
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0'
        }
        
        # Use label field for search (exact match)
        label = card_data.get('label', '')
        
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

# ==================== STREAMLIT UI ====================
st.title("📊 Card Ladder Scraper")

# Sidebar for authentication and settings
with st.sidebar:
    st.header("🔐 Authentication")
    
    token_input = st.text_area(
        "Paste Bearer Token:",
        height=150,
        help="Copy the 'authorization' header from DevTools."
    )
    
    if token_input:
        st.session_state.auth_token = token_input if token_input.startswith('Bearer ') else f'Bearer {token_input}'
    
    st.divider()
    
    st.header("⚙️ Settings")
    
    # Collection ID
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    # Record Selection
    fetch_option = st.radio(
        "Fetch Records:",
        ["All Records", "Specific Number"]
    )
    
    if fetch_option == "Specific Number":
        record_limit = st.number_input(
            "Number of records to fetch:",
            min_value=1,
            max_value=10000,
            value=50
        )
        fetch_all = False
    else:
        record_limit = None
        fetch_all = True
    
    # Max Threads
    max_workers = st.slider("Max Threads:", 1, 10, 1)
    
    st.divider()
    
    # Control buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("🚀 Start Process", use_container_width=True):
            if not st.session_state.auth_token:
                st.error("Please provide a Bearer Token!")
            else:
                st.session_state.processing = True
                st.session_state.stop_processing = False
                st.rerun()
    
    with col2:
        if st.button("⏹️ Stop Process", use_container_width=True):
            st.session_state.stop_processing = True
            st.rerun()
    
    if st.button("🗑️ Clear Logs", use_container_width=True):
        clear_logs()
        st.rerun()

# Main content area
if st.session_state.auth_token:
    # Status display
    if st.session_state.processing:
        status_placeholder = st.empty()
        progress_bar = st.progress(0)
    
    # Log display
    st.subheader("📝 Processing Log")
    log_container = st.container(height=400)
    
    with log_container:
        for log in st.session_state.logs:
            st.text(log)
    
    # Process running indicator
    if st.session_state.processing and not st.session_state.get('process_started', False):
        st.session_state.process_started = True
        
        # Run the process in a separate thread
        import threading
        
        def run_process():
            try:
                # Phase 1: Fetch collection
                add_log("Starting Phase 1: Fetching collection...")
                success, collection_data = fetch_collection(
                    coll_id, 
                    st.session_state.auth_token, 
                    fetch_all, 
                    record_limit
                )
                
                if not success or st.session_state.get('stop_processing', False):
                    add_log("Process stopped or failed")
                    st.session_state.processing = False
                    st.session_state.process_started = False
                    st.rerun()
                    return
                
                st.session_state.collection_data = collection_data
                
                # Phase 2: Fetch sales data
                add_log(f"\n=== PHASE 2: Fetching Last 3 Sales ===")
                add_log(f"Processing {len(collection_data)} cards...")
                
                sales_success = 0
                total_cards = len(collection_data)
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    futures = []
                    for idx, card in enumerate(collection_data, 1):
                        if st.session_state.get('stop_processing', False):
                            break
                        
                        futures.append((executor.submit(fetch_sales_for_card, card, st.session_state.auth_token), card, idx))
                    
                    # Process results as they complete
                    completed = 0
                    for future, card, idx in futures:
                        if st.session_state.get('stop_processing', False):
                            break
                        
                        completed += 1
                        result = future.result()
                        
                        if result:
                            # Merge sales data into card
                            card.update(result)
                            sales_success += 1
                            
                            player = card.get('player', f'Card {idx}')
                            sales_found = result.get('sales_found', 0)
                            
                            if sales_found > 0:
                                add_log(f"✅ [{idx}/{total_cards}] {player}: {sales_found} sales found")
                            else:
                                add_log(f"⚠️ [{idx}/{total_cards}] {player}: No sales found")
                        else:
                            player = card.get('player', f'Card {idx}')
                            add_log(f"❌ [{idx}/{total_cards}] {player}: Failed to fetch sales")
                        
                        # Update progress
                        progress = completed / total_cards
                        progress_bar.progress(progress)
                        
                        # Rate limiting
                        time.sleep(0.2)
                
                st.session_state.sales_success = sales_success
                
                # Save results
                if collection_data and not st.session_state.get('stop_processing', False):
                    add_log("\n=== SAVING RESULTS ===")
                    
                    # Create DataFrame
                    df = pd.json_normalize(collection_data)
                    
                    # Add timestamp
                    current_date = datetime.now()
                    scrape_date = current_date.strftime("%Y-%m-%d")
                    
                    # Add Scrape Date column
                    df.insert(0, 'Scrape Date', scrape_date)
                    
                    # Add Card URL column if available
                    if 'collectionCardId' in df.columns:
                        df.insert(1, 'Card Unique URL', df['collectionCardId'].apply(
                            lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true&backTo=Collection" 
                            if pd.notna(x) else None
                        ))
                    
                    # Display results
                    add_log(f"✅ Process Complete!")
                    add_log(f"✅ Total cards: {len(collection_data)}")
                    add_log(f"✅ Cards with sales data: {sales_success}")
                    
                    if len(collection_data) > 0:
                        success_rate = (sales_success / len(collection_data)) * 100
                        add_log(f"✅ Success rate: {success_rate:.1f}%")
                    
                    # Save to session state for download
                    st.session_state.df_full = df
                    
                    # Google Sheets integration
                    if GOOGLE_SHEETS_AVAILABLE and GOOGLE_CREDENTIALS:
                        try:
                            add_log("📊 Saving to Google Sheets...")
                            gs_manager = GoogleSheetsManager()
                            success, message = gs_manager.connect()
                            
                            if success:
                                sheet_name = f"CardLadder_{current_date.strftime('%Y-%b-%d')}"
                                spreadsheet, msg = gs_manager.create_or_open_sheet(sheet_name)
                                
                                if spreadsheet:
                                    # Save full data
                                    gs_manager.save_dataframe_to_sheet(spreadsheet, "Full Data", df)
                                    add_log(f"✅ Google Sheets saved: {spreadsheet.url}")
                                else:
                                    add_log(f"❌ Google Sheets error: {msg}")
                            else:
                                add_log(f"❌ Google Sheets connection failed: {message}")
                        except Exception as e:
                            add_log(f"❌ Google Sheets error: {str(e)}")
                    
                    add_log("✨ Process completed successfully!")
                
            except Exception as e:
                add_log(f"❌ Process Error: {str(e)}")
            finally:
                st.session_state.processing = False
                st.session_state.process_started = False
                st.rerun()
        
        # Start the process thread
        threading.Thread(target=run_process, daemon=True).start()
    
    # Display results and download buttons
    if not st.session_state.processing and hasattr(st.session_state, 'df_full'):
        st.divider()
        st.subheader("📊 Results & Downloads")
        
        df = st.session_state.df_full
        
        # Display metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Cards", len(df))
        with col2:
            st.metric("Cards with Sales", st.session_state.sales_success)
        with col3:
            if len(df) > 0:
                success_rate = (st.session_state.sales_success / len(df)) * 100
                st.metric("Success Rate", f"{success_rate:.1f}%")
        
        # Download buttons
        st.subheader("📥 Download Data")
        
        # Prepare data for download
        current_date = datetime.now().strftime("%Y-%b-%d")
        mode = "ALL_RECORDS" if fetch_all else f"LIMIT_{record_limit}"
        
        # Full Excel
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Collection')
        excel_data = excel_buffer.getvalue()
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.download_button(
                label="📗 Download Excel (.xlsx)",
                data=excel_data,
                file_name=f"Cardladder_{current_date}_{mode}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with col2:
            # CSV
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📊 Download CSV (.csv)",
                data=csv_data,
                file_name=f"Cardladder_{current_date}_{mode}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col3:
            # JSON
            json_data = json.dumps(st.session_state.collection_data, indent=2).encode('utf-8')
            st.download_button(
                label="💾 Download JSON",
                data=json_data,
                file_name=f"Cardladder_{current_date}_{mode}.json",
                mime="application/json",
                use_container_width=True
            )
        
        # Data preview
        st.subheader("👀 Data Preview")
        st.dataframe(df.head(50), use_container_width=True)
else:
    st.info("👈 Please enter your Bearer Token in the sidebar to get started.")

# Footer
st.divider()
st.caption("Card Ladder Scraper • Built with Streamlit")
