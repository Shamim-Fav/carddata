import requests
import json
import time
import queue
import threading
import pandas as pd
import tkinter as tk
import numpy as np
import io
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

# ==================== CREDENTIALS & CONFIG ====================
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
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

class GoogleSheetsManager:
    def __init__(self):
        self.client = None
        self.connected = False
        
    def connect(self):
        try:
            scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
            creds = ServiceAccountCredentials.from_json_keyfile_dict(GOOGLE_CREDENTIALS, scope)
            self.client = gspread.authorize(creds)
            self.connected = True
            return True, "Connected"
        except Exception as e:
            return False, str(e)

    def save_dataframe(self, df, sheet_name):
        try:
            if not self.connected: self.connect()
            sh = self.client.open_by_key(SPREADSHEET_ID)
            try:
                ws = sh.worksheet(sheet_name)
                ws.clear()
            except gspread.exceptions.WorksheetNotFound:
                ws = sh.add_worksheet(title=sheet_name, rows="1000", cols="20")
            
            # Clean data: convert to string and handle NaNs
            df_clean = df.fillna('').astype(str)
            data = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
            ws.update(data, value_input_option='USER_ENTERED')
            return True, "Success"
        except Exception as e:
            return False, str(e)

class CardLadderScraper:
    def __init__(self, token):
        self.token = token if token.startswith('Bearer ') else f'Bearer {token}'
        self.root = tk.Tk()
        self.root.title("Card Ladder Scraper Pro")
        self.root.geometry("900x700")
        self.root.configure(bg='#1e1e1e')
        
        self.processing = False
        self.collection_data = []
        self.log_queue = queue.Queue()
        
        self.setup_ui()
        self.update_logs()

    def setup_ui(self):
        style = ttk.Style()
        style.theme_use('clam')
        
        main = tk.Frame(self.root, bg='#1e1e1e', padx=20, pady=20)
        main.pack(fill=tk.BOTH, expand=True)

        # Header
        tk.Label(main, text="Card Ladder Data Sync", font=('Arial', 18, 'bold'), fg='#00ff88', bg='#1e1e1e').pack(pady=10)

        # Settings Frame
        settings = tk.LabelFrame(main, text=" Configuration ", fg='white', bg='#2d2d2d', padx=10, pady=10)
        settings.pack(fill=tk.X, pady=10)

        tk.Label(settings, text="Collection ID:", fg='white', bg='#2d2d2d').grid(row=0, column=0, sticky='w')
        self.coll_id_var = tk.StringVar(value="zKC3o1sfYEcBGNaTPDRn")
        tk.Entry(settings, textvariable=self.coll_id_var, width=35).grid(row=0, column=1, padx=5, pady=5)

        tk.Label(settings, text="Limit:", fg='white', bg='#2d2d2d').grid(row=1, column=0, sticky='w')
        self.limit_var = tk.IntVar(value=20)
        tk.Spinbox(settings, from_=1, to=1000, textvariable=self.limit_var, width=10).grid(row=1, column=1, sticky='w', padx=5)

        # Log Area
        self.log_widget = scrolledtext.ScrolledText(main, height=20, bg='#000000', fg='#00ff00', font=('Consolas', 9))
        self.log_widget.pack(fill=tk.BOTH, expand=True, pady=10)

        # Buttons
        btn_frame = tk.Frame(main, bg='#1e1e1e')
        btn_frame.pack(fill=tk.X)
        
        self.start_btn = tk.Button(btn_frame, text="🚀 START PROCESS", bg='#0078d4', fg='white', font=('Arial', 10, 'bold'), 
                                   command=self.start_thread, padx=20, pady=10)
        self.start_btn.pack(side=tk.RIGHT)

    def log(self, msg):
        self.log_queue.put(msg)

    def update_logs(self):
        while not self.log_queue.empty():
            msg = self.log_queue.get()
            self.log_widget.insert(tk.END, f"[{datetime.now().strftime('%H:%M:%S')}] {msg}\n")
            self.log_widget.see(tk.END)
        self.root.after(100, self.update_logs)

    def start_thread(self):
        if not self.processing:
            self.processing = True
            self.start_btn.config(state='disabled', text="⌛ PROCESSING...")
            threading.Thread(target=self.run_process, daemon=True).start()

    def run_process(self):
        try:
            self.log("Phase 1: Fetching cards...")
            headers = {'authorization': self.token, 'accept': 'application/json'}
            params = {
                'index': 'collectioncards',
                'limit': self.limit_var.get(),
                'filters': f'collectionId:{self.coll_id_var.get()}|hasQuantityAvailable:true'
            }
            
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
            if res.status_code != 200:
                self.log(f"API Error: {res.status_code}")
                return

            cards = res.json().get('hits', [])
            self.log(f"Found {len(cards)} cards. Fetching sales history...")

            # Phase 2: Parallel Sales Fetch
            def fetch_sales(card):
                label = card.get('label', '')
                try:
                    s_res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                                       headers=headers, 
                                       params={'index': 'salesarchive', 'query': label, 'limit': 3, 'sort': 'date', 'direction': 'desc'})
                    if s_res.status_code == 200:
                        s_data = s_res.json()
                        hits = s_data.get('hits', [])
                        prices = [h.get('price') for h in hits if h.get('price')]
                        card['total_sales_in_db'] = s_data.get('totalHits', 0)
                        card['avg_last_3_sales'] = round(sum(prices)/len(prices), 2) if prices else 0
                        for i in range(3):
                            card[f'sale{i+1}_price'] = prices[i] if i < len(prices) else None
                except: pass
                return card

            with ThreadPoolExecutor(max_workers=5) as exe:
                self.collection_data = list(exe.map(fetch_sales, cards))

            self.save_all()

        except Exception as e:
            self.log(f"Error: {str(e)}")
        finally:
            self.processing = False
            self.start_btn.config(state='normal', text="🚀 START PROCESS")

    def save_all(self):
        self.log("Filtering and saving data...")
        df = pd.json_normalize(self.collection_data)
        
        # 1. Add Custom Columns
        scrape_date = datetime.now().strftime("%Y-%m-%d")
        df.insert(0, 'Scrape Date', scrape_date)
        if 'collectionCardId' in df.columns:
            df.insert(1, 'Card Unique URL', df['collectionCardId'].apply(lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=true"))
        
        # 2. STRICT FILTERING (The "Magic" part)
        target_cols = [
            'Scrape Date', 'Card Unique URL', 'label', 'condition', 
            'variation', 'player', 'currentValue', 'avg_last_3_sales', 
            'total_sales_in_db', 'sale1_price', 'sale2_price', 'sale3_price'
        ]
        # Reindex ensures columns exist and are in the correct order
        df_filtered = df.reindex(columns=target_cols)

        # 3. Save Local Excel
        fname = f"CardLadder_Export_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        df_filtered.fillna('').to_excel(fname, index=False)
        self.log(f"✅ Excel saved: {fname}")

        # 4. Save Google Sheets
        if GOOGLE_SHEETS_AVAILABLE:
            gsm = GoogleSheetsManager()
            success, msg = gsm.save_dataframe(df_filtered, "Scraped Data")
            if success:
                self.log("✅ Google Sheets updated successfully!")
            else:
                self.log(f"❌ Google Sheets failed: {msg}")

if __name__ == "__main__":
    # For simplicity, using a basic input for token first
    root_auth = tk.Tk()
    root_auth.withdraw()
    token = tk.simpledialog.askstring("Auth", "Paste Bearer Token:", show='*')
    if token:
        app = CardLadderScraper(token)
        app.root.mainloop()
