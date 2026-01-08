import requests
import json
import time
import queue
import threading
import pandas as pd
import tkinter as tk
import numpy as np
from datetime import datetime
from tkinter import ttk, scrolledtext, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== GOOGLE SHEETS INTEGRATION ====================
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    print("Google Sheets libraries not installed. Run: pip install gspread oauth2client")

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
        """Save pandas DataFrame to Google Sheet - SIMPLE VERSION"""
        try:
            # Create a clean DataFrame copy
            df_clean = df.copy()
            
            # Convert all columns to string type (simplest approach)
            # This handles arrays, lists, dicts, etc. just like Excel
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

# ==================== TOKEN INPUT GUI ====================
class TokenInputGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Card Ladder - Bearer Token")
        self.root.geometry("700x500")
        self.root.configure(bg='#2b2b2b')
        self.token = None
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = tk.Frame(self.root, bg='#2b2b2b', padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(main_frame, text="🔐 Card Ladder Authentication", font=('Segoe UI', 16, 'bold'), fg='#ffffff', bg='#2b2b2b').pack(pady=(0, 20))
        
        box = tk.Frame(main_frame, bg='#3c3c3c', padx=10, pady=10)
        box.pack(fill=tk.X, pady=10)
        tk.Label(box, text="Paste Bearer Token from DevTools:", fg='#00ff88', bg='#3c3c3c', font=('Segoe UI', 10, 'bold')).pack(anchor='w')
        
        self.token_text = scrolledtext.ScrolledText(main_frame, height=10, font=('Consolas', 9), bg='#1e1e1e', fg='#ffffff')
        self.token_text.pack(fill=tk.BOTH, expand=True, pady=10)
        
        btn = tk.Button(main_frame, text="Next Step ➡️", command=self.submit, bg='#00aa55', fg='white', font=('Segoe UI', 11, 'bold'), padx=20, pady=10)
        btn.pack(side=tk.RIGHT)

    def submit(self):
        t = self.token_text.get('1.0', tk.END).strip()
        if t:
            self.token = t if t.startswith('Bearer ') else f'Bearer {t}'
            self.root.destroy()
        else:
            messagebox.showerror("Error", "Token is required")

    def get_token(self):
        self.root.mainloop()
        return self.token

# ==================== MAIN SCRAPER GUI ====================
class CardLadderScraper:
    def __init__(self, auth_token):
        self.auth_token = auth_token
        self.root = tk.Tk()
        self.root.title("Card Ladder - Complete Scraper")
        self.root.geometry("1000x800")
        self.root.configure(bg='#2b2b2b')
        
        self.log_queue = queue.Queue()
        self.max_workers = tk.IntVar(value=1)
        
        # Record selection variables
        self.fetch_all = tk.BooleanVar(value=True)  # Default: Fetch all records
        self.record_limit = tk.IntVar(value=50)     # Default limit when not fetching all
        
        # Phase control
        self.phase1_complete = False
        self.collection_data = []
        
        # Google Sheets - auto-enabled if credentials are available
        self.google_sheets = None
        self.spreadsheet = None
        
        # Check if Google Sheets credentials are available
        if GOOGLE_SHEETS_AVAILABLE:
            self.google_sheets = GoogleSheetsManager()
            self.log("✅ Google Sheets library available")
        
        self.setup_ui()
        self.update_logs()
        
    def setup_ui(self):
        main = tk.Frame(self.root, bg='#2b2b2b', padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)
        
        # Header
        tk.Label(main, text="📦 Card Ladder Complete Scraper", font=('Segoe UI', 20, 'bold'), 
                fg='#ffffff', bg='#2b2b2b').pack(pady=(0, 20))
        
        # ===== INPUT SECTION =====
        input_frame = tk.LabelFrame(main, text=" Collection Settings ", font=('Segoe UI', 11, 'bold'),
                                   bg='#3c3c3c', fg='#00ff88', padx=15, pady=15)
        input_frame.pack(fill=tk.X, pady=(0, 20))
        
        # Row 1: Collection ID
        tk.Label(input_frame, text="Collection ID:", fg='white', bg='#3c3c3c', 
                font=('Segoe UI', 10)).grid(row=0, column=0, sticky='w', pady=5)
        self.coll_id_var = tk.StringVar(value="zKC3o1sfYEcBGNaTPDRn")
        tk.Entry(input_frame, textvariable=self.coll_id_var, width=40, 
                font=('Segoe UI', 10)).grid(row=0, column=1, padx=10, sticky='w', pady=5)
        
        # Row 2: Record Selection
        tk.Label(input_frame, text="Fetch Records:", fg='white', bg='#3c3c3c', 
                font=('Segoe UI', 10)).grid(row=1, column=0, sticky='w', pady=5)
        
        # Create frame for record selection options
        record_frame = tk.Frame(input_frame, bg='#3c3c3c')
        record_frame.grid(row=1, column=1, sticky='w', pady=5)
        
        # All records radio button
        self.all_radio = tk.Radiobutton(record_frame, text="All Records", variable=self.fetch_all, 
                                       value=True, bg='#3c3c3c', fg='white',
                                       selectcolor='#3c3c3c', font=('Segoe UI', 10),
                                       command=self.toggle_record_selection)
        self.all_radio.pack(side=tk.LEFT)
        
        # Specific number radio button
        self.limit_radio = tk.Radiobutton(record_frame, text="Specific Number:", variable=self.fetch_all, 
                                         value=False, bg='#3c3c3c', fg='white',
                                         selectcolor='#3c3c3c', font=('Segoe UI', 10),
                                         command=self.toggle_record_selection)
        self.limit_radio.pack(side=tk.LEFT, padx=(20, 5))
        
        # Number entry for specific records
        self.limit_entry = tk.Spinbox(record_frame, from_=1, to=10000, 
                                     textvariable=self.record_limit, width=8,
                                     font=('Segoe UI', 10), state='disabled')
        self.limit_entry.pack(side=tk.LEFT)
        
        # Row 3: Max Threads
        tk.Label(input_frame, text="Max Threads:", fg='white', bg='#3c3c3c', 
                font=('Segoe UI', 10)).grid(row=2, column=0, sticky='w', pady=5)
        tk.Spinbox(input_frame, from_=1, to=10, textvariable=self.max_workers, 
                  width=10, font=('Segoe UI', 10)).grid(row=2, column=1, padx=10, sticky='w', pady=5)
        
        # ===== STATUS DISPLAY =====
        status_frame = tk.Frame(main, bg='#2b2b2b')
        status_frame.pack(fill=tk.X, pady=(0, 20))
        
        self.status_label = tk.Label(status_frame, text="Ready to start...", 
                                    fg='#00ff88', bg='#2b2b2b', font=('Segoe UI', 12))
        self.status_label.pack(anchor='w')
        
        self.progress_label = tk.Label(status_frame, text="", fg='#cccccc', 
                                      bg='#2b2b2b', font=('Segoe UI', 10))
        self.progress_label.pack(anchor='w', pady=(5, 0))
        
        # Google Sheets status
        if self.google_sheets:
            self.google_status_label = tk.Label(status_frame, text="✅ Google Sheets ready", 
                                              fg='#ff9900', bg='#2b2b2b', font=('Segoe UI', 10))
            self.google_status_label.pack(anchor='w', pady=(5, 0))
        
        # ===== LOG DISPLAY =====
        log_frame = tk.LabelFrame(main, text=" Processing Log ", font=('Segoe UI', 11, 'bold'),
                                 bg='#3c3c3c', fg='#00ff88', padx=15, pady=15)
        log_frame.pack(fill=tk.BOTH, expand=True)
        
        self.log_widget = scrolledtext.ScrolledText(log_frame, height=20, 
                                                   bg='#1e1e1e', fg='#00ff00', 
                                                   font=('Consolas', 9))
        self.log_widget.pack(fill=tk.BOTH, expand=True)
        
        # ===== CONTROL BUTTONS =====
        btn_frame = tk.Frame(main, bg='#2b2b2b', pady=20)
        btn_frame.pack(fill=tk.X)
        
        self.start_btn = tk.Button(btn_frame, text="🚀 START COMPLETE PROCESS", 
                                  command=self.start_complete_process, 
                                  bg='#007acc', fg='white', 
                                  font=('Segoe UI', 12, 'bold'), padx=25, pady=10)
        self.start_btn.pack(side=tk.RIGHT, padx=10)
        
        self.stop_btn = tk.Button(btn_frame, text="⏹️ Stop", command=self.stop_process,
                                 bg='#cc0000', fg='white', font=('Segoe UI', 10), 
                                 padx=20, pady=5, state='disabled')
        self.stop_btn.pack(side=tk.LEFT, padx=5)
        
        # Processing control
        self.processing = False
        
    def toggle_record_selection(self):
        """Enable/disable record limit entry based on selection"""
        if self.fetch_all.get():
            # Fetch all records - disable the limit entry
            self.limit_entry.config(state='disabled')
        else:
            # Fetch specific number - enable the limit entry
            self.limit_entry.config(state='normal')
    
    def log(self, msg):
        self.log_queue.put(msg)
    
    def update_logs(self):
        try:
            while True:
                m = self.log_queue.get_nowait()
                self.log_widget.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {m}\n")
                self.log_widget.see(tk.END)
        except queue.Empty:
            pass
        self.root.after(100, self.update_logs)
    
    def update_status(self, message, color='#00ff88'):
        self.status_label.config(text=message, fg=color)
    
    def update_progress(self, message):
        self.progress_label.config(text=message)
    
    # ===== PHASE 1: FETCH COLLECTION =====
    def fetch_collection(self):
        """Phase 1: Fetch cards from collection based on user selection"""
        cid = self.coll_id_var.get()
        all_cards = []
        page = 0
        limit = 20
        
        # Get user's record selection
        fetch_all_records = self.fetch_all.get()
        record_limit = self.record_limit.get() if not fetch_all_records else None
        
        headers = {
            'authorization': self.auth_token,
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0'
        }
        
        self.log(f"=== PHASE 1: Fetching Collection ===")
        
        # Display user's selection
        if fetch_all_records:
            self.log("📊 Mode: Fetching ALL records from collection")
            self.update_status("Phase 1: Fetching ALL collection records...", '#ff9900')
        else:
            self.log(f"📊 Mode: Fetching up to {record_limit} records")
            self.update_status(f"Phase 1: Fetching {record_limit} records...", '#ff9900')
        
        try:
            while True and self.processing:
                self.log(f"Fetching page {page}...")
                self.update_progress(f"Page {page}")
                
                params = {
                    'index': 'collectioncards',
                    'page': page,
                    'limit': limit,
                    'filters': f'collectionId:{cid}|hasQuantityAvailable:true',
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
                    self.log(f"❌ Error: Server returned {response.status_code}")
                    break
                    
                data = response.json()
                hits = data.get('hits', [])
                total = data.get('totalHits', 0)
                
                if not hits:
                    break
                    
                all_cards.extend(hits)
                self.log(f"✅ Page {page}: {len(hits)} cards (Total: {len(all_cards)}/{total})")
                
                # Check if we've reached the user's limit
                if not fetch_all_records and len(all_cards) >= record_limit:
                    all_cards = all_cards[:record_limit]
                    self.log(f"📊 Reached user limit of {record_limit} cards")
                    break
                
                if fetch_all_records and (len(all_cards) >= total or len(hits) < limit):
                    break
                    
                page += 1
                time.sleep(0.3)
            
            if all_cards:
                self.collection_data = all_cards
                self.phase1_complete = True
                
                # Log the final count
                if fetch_all_records:
                    self.log(f"✅ PHASE 1 COMPLETE: Collected ALL {len(all_cards)} cards from collection")
                else:
                    self.log(f"✅ PHASE 1 COMPLETE: Collected {len(all_cards)} cards (User limit: {record_limit})")
                
                self.update_status(f"Phase 1 Complete: {len(all_cards)} cards", '#00ff88')
                return True
            else:
                self.log("⚠️ No cards found in collection")
                self.update_status("No cards found", '#ff4444')
                return False
                
        except Exception as e:
            self.log(f"❌ Phase 1 Error: {str(e)}")
            self.update_status("Phase 1 Failed", '#ff4444')
            return False
    
    # ===== PHASE 2: FETCH SALES DATA =====
    def fetch_sales_for_card(self, card_data):
        """Phase 2: Fetch last 3 sales for a single card"""
        try:
            headers = {
                'authorization': self.auth_token,
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
    
    def fetch_sales_for_all_cards(self):
        """Phase 2: Fetch sales for all collected cards"""
        if not self.collection_data:
            self.log("❌ No collection data to process")
            return 0
        
        self.log(f"\n=== PHASE 2: Fetching Last 3 Sales ===")
        self.update_status("Phase 2: Fetching sales data...", '#ff9900')
        
        total_cards = len(self.collection_data)
        sales_success = 0
        
        with ThreadPoolExecutor(max_workers=self.max_workers.get()) as executor:
            futures = []
            for idx, card in enumerate(self.collection_data, 1):
                if not self.processing:
                    break
                
                futures.append((executor.submit(self.fetch_sales_for_card, card), card, idx))
            
            # Process results as they complete
            completed = 0
            for future, card, idx in futures:
                if not self.processing:
                    break
                
                completed += 1
                result = future.result()
                
                if result:
                    # Merge sales data into card
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
                            self.log(f"✅ [{idx}/{total_cards}] {player}: {sales_found} sales{avg_str} - {', '.join(prices)}")
                        else:
                            self.log(f"✅ [{idx}/{total_cards}] {player}: {sales_found} sales")
                    else:
                        self.log(f"⚠️ [{idx}/{total_cards}] {player}: No sales found")
                else:
                    player = card.get('player', f'Card {idx}')
                    self.log(f"❌ [{idx}/{total_cards}] {player}: Failed to fetch sales")
                
                # Update progress
                if completed % 2 == 0 or completed == total_cards:
                    percent = (completed / total_cards) * 100
                    self.update_progress(f"Phase 2: {completed}/{total_cards} cards ({percent:.1f}%)")
                
                # Rate limiting
                time.sleep(0.2)
        
        return sales_success
    
    # ===== MAIN PROCESS CONTROL =====
    def start_complete_process(self):
        """Start the complete two-phase process"""
        self.processing = True
        self.start_btn.config(state='disabled')
        self.stop_btn.config(state='normal')
        
        # Clear previous data
        self.collection_data = []
        self.phase1_complete = False
        
        # Start processing in separate thread
        threading.Thread(target=self.run_complete_process, daemon=True).start()
    
    def run_complete_process(self):
        """Run both phases sequentially"""
        try:
            # Phase 1: Fetch collection
            phase1_success = self.fetch_collection()
            
            if not phase1_success or not self.processing:
                self.finish_processing()
                return
            
            # Phase 2: Fetch sales data
            sales_success = self.fetch_sales_for_all_cards()
            
            # Save results
            if self.collection_data and self.processing:
                self.save_results(sales_success)
            
        except Exception as e:
            self.log(f"❌ Process Error: {str(e)}")
        finally:
            self.finish_processing()
    
    def save_results(self, sales_success):
        """Save all data to files - TWO Excel files and Google Sheets"""
        try:
            # Get current date for filename and scrape date column
            current_date = datetime.now()
            scrape_date_filename = current_date.strftime("%Y-%b-%d")  # 2026-Jan-08 format for filename
            scrape_date_display = current_date.strftime("%Y-%m-%d")  # For the column
            
            cid = self.coll_id_var.get().replace(':', '_')
            
            # Determine mode for display
            if self.fetch_all.get():
                mode = "ALL_RECORDS"
            else:
                mode = f"LIMIT_{self.record_limit.get()}"
            
            # Create DataFrames with "Scrape Date" column
            df = pd.json_normalize(self.collection_data)
            
            # Add "Scrape Date" column at the beginning
            df.insert(0, 'Scrape Date', scrape_date_display)
            
            # Add "Card Unique URL" column as the second column
            if 'collectionCardId' in df.columns:
                df.insert(1, 'Card Unique URL', df['collectionCardId'].apply(
                    lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true&backTo=Collection" 
                    if pd.notna(x) else None
                ))
            else:
                df.insert(1, 'Card Unique URL', None)
                self.log("⚠️ 'collectionCardId' column not found - Card Unique URLs will be empty")
            
            # ===== 1. SAVE EXCEL FILES =====
            # Save full Excel
            full_excel_name = f"Cardladder_{scrape_date_filename}_{mode}.xlsx"
            # Reorder columns to put sales at end
            cols = list(df.columns)
            sale_price_cols = sorted([c for c in cols if 'sale' in c and 'price' in c])
            sale_date_cols = sorted([c for c in cols if 'sale' in c and 'date' in c])
            sale_listingtype_cols = sorted([c for c in cols if 'sale' in c and 'listingType' in c])
            special_cols = [c for c in cols if 'avg_last_3_sales' in c or 'sales_count_for_avg' in c]
            other_cols = ['Scrape Date', 'Card Unique URL'] + [c for c in cols if c not in (['Scrape Date', 'Card Unique URL'] + sale_price_cols + sale_date_cols + 
                         sale_listingtype_cols + special_cols)]
            ordered_cols = (other_cols + sale_price_cols + sale_date_cols + sale_listingtype_cols + special_cols)
            df_full = df[ordered_cols]
            
            # Clean NaN values for Excel
            df_full_clean = df_full.where(pd.notnull(df_full), None)
            df_full_clean.to_excel(full_excel_name, index=False, engine='openpyxl')
            self.log(f"📗 Full Excel saved: {full_excel_name}")
            
            # Save filtered Excel
            filtered_excel_name = f"Filter_cardladder_{scrape_date_filename}_{mode}.xlsx"
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
            
            # Clean NaN values for Excel
            df_filtered_clean = df_filtered.where(pd.notnull(df_filtered), None)
            df_filtered_clean.to_excel(filtered_excel_name, index=False, engine='openpyxl')
            self.log(f"📘 Filtered Excel saved: {filtered_excel_name}")
            
            # ===== 2. SAVE TO GOOGLE SHEETS =====
            google_sheets_message = ""
            if self.google_sheets and self.processing:
                try:
                    self.log("📊 Connecting to Google Sheets...")
                    
                    # Check if credentials are available
                    if not GOOGLE_CREDENTIALS:
                        self.log("⚠️ Google Sheets credentials not found in script")
                        self.log("ℹ️ Add your credentials to the GOOGLE_CREDENTIALS variable at the top of the script")
                        google_sheets_message = "\n⚠️ Google Sheets: Credentials not configured"
                    else:
                        # Initialize with credentials
                        self.google_sheets.credentials_dict = GOOGLE_CREDENTIALS
                        success, message = self.google_sheets.connect()
                        
                        if success:
                            # Create or open spreadsheet
                            sheet_name = f"CardLadder_{scrape_date_filename}_{mode}"
                            
                            spreadsheet, msg = self.google_sheets.create_or_open_sheet(sheet_name)
                            
                            if spreadsheet:
                                self.spreadsheet = spreadsheet
                                
                                # Save Full Data
                                self.log("📊 Saving full data to Google Sheets...")
                                success, message = self.google_sheets.save_dataframe_to_sheet(
                                    spreadsheet, "Full Data", df_full_clean
                                )
                                if success:
                                    self.log(f"✅ {message}")
                                else:
                                    self.log(f"❌ {message}")
                                
                                # Save Filtered Data
                                self.log("📊 Saving filtered data to Google Sheets...")
                                success, message = self.google_sheets.save_dataframe_to_sheet(
                                    spreadsheet, "Filtered Data", df_filtered_clean
                                )
                                if success:
                                    self.log(f"✅ {message}")
                                else:
                                    self.log(f"❌ {message}")
                                
                                # Save Summary
                                summary_data = {
                                    'Metric': ['Total Cards', 'Cards with Sales', 'Success Rate', 
                                              'Scrape Date', 'Collection ID', 'Fetch Mode'],
                                    'Value': [len(self.collection_data), sales_success,
                                             f"{(sales_success/len(self.collection_data))*100:.1f}%" if len(self.collection_data) > 0 else "N/A",
                                             scrape_date_display, cid, mode]
                                }
                                df_summary = pd.DataFrame(summary_data)
                                success, message = self.google_sheets.save_dataframe_to_sheet(
                                    spreadsheet, "Summary", df_summary
                                )
                                if success:
                                    self.log(f"✅ {message}")
                                
                                # Get URL
                                sheet_url = spreadsheet.url
                                self.log(f"✅ Google Sheets saved: {sheet_url}")
                                google_sheets_message = f"\nGoogle Sheets URL:\n{sheet_url}"
                            else:
                                self.log(f"❌ Failed to create/open spreadsheet: {msg}")
                                google_sheets_message = "\n⚠️ Google Sheets save failed"
                        else:
                            self.log(f"❌ Google Sheets connection failed: {message}")
                            google_sheets_message = "\n⚠️ Google Sheets connection failed"
                            
                except Exception as e:
                    self.log(f"❌ Google Sheets error: {str(e)}")
                    google_sheets_message = f"\n⚠️ Google Sheets error: {str(e)}"
            
            # ===== 3. SHOW SUMMARY =====
            self.log(f"\n{'='*60}")
            self.log("✨ PROCESS COMPLETE!")
            self.log(f"{'='*60}")
            self.log(f"✅ Total cards fetched: {len(self.collection_data)}")
            self.log(f"✅ Cards with sales data: {sales_success}")
            
            # Display fetch mode info
            if self.fetch_all.get():
                self.log(f"📊 Mode: Fetched ALL available records")
            else:
                self.log(f"📊 Mode: Fetched {len(self.collection_data)} records (User limit: {self.record_limit.get()})")
            
            if sales_success > 0:
                avg_values = []
                current_values = []
                for card in self.collection_data:
                    if 'avg_last_3_sales' in card and card['avg_last_3_sales'] is not None:
                        avg_values.append(card['avg_last_3_sales'])
                    if 'currentValue' in card and card['currentValue'] is not None:
                        current_values.append(card['currentValue'])
                if avg_values:
                    overall_avg = sum(avg_values) / len(avg_values)
                    self.log(f"📊 Overall average of last 3 sales: ${overall_avg:.2f}")
                if current_values:
                    overall_current = sum(current_values) / len(current_values)
                    self.log(f"📊 Overall average current value: ${overall_current:.2f}")
            
            if len(self.collection_data) > 0:
                success_rate = (sales_success / len(self.collection_data)) * 100
                self.log(f"✅ Success rate: {success_rate:.1f}%")
            
            self.update_status(f"Complete! {sales_success}/{len(self.collection_data)} cards have sales", '#00ff88')
            
            # Show message box
            mode_text = "All records" if self.fetch_all.get() else f"{len(self.collection_data)} records (limit: {self.record_limit.get()})"
            message = (f"✅ Process Complete!\n\n"
                      f"Fetch Mode: {mode_text}\n"
                      f"Total cards: {len(self.collection_data)}\n"
                      f"Cards with sales: {sales_success}\n"
                      f"Success rate: {(sales_success/len(self.collection_data))*100:.1f}%\n\n"
                      f"Files saved:\n"
                      f"• {full_excel_name}\n"
                      f"• {filtered_excel_name}")
            
            if google_sheets_message:
                message += google_sheets_message
            
            self.root.after(0, lambda: messagebox.showinfo("Success", message))
            
        except Exception as e:
            self.log(f"❌ Error saving results: {str(e)}")
    
    def stop_process(self):
        """Stop the current process"""
        self.processing = False
        self.log("⏹️ Process stopped by user")
        self.update_status("Process Stopped", '#ff4444')
        self.stop_btn.config(state='disabled')
    
    def finish_processing(self):
        """Clean up after processing"""
        self.processing = False
        self.root.after(0, lambda: self.start_btn.config(state='normal'))
        self.root.after(0, lambda: self.stop_btn.config(state='disabled'))

# ==================== MAIN EXECUTION ====================
if __name__ == "__main__":
    # Get token first
    token_gui = TokenInputGUI()
    token = token_gui.get_token()
    
    if token:
        # Run the complete scraper
        scraper = CardLadderScraper(token)
        scraper.root.mainloop()
    else:
        print("No token provided. Exiting.")
