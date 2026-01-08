import streamlit as st
import requests
import json
import time
import pandas as pd
import numpy as np
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== GOOGLE SHEETS INTEGRATION ====================
try:
    import gspread
    from oauth2client.service_account import ServiceAccountCredentials
    GOOGLE_SHEETS_AVAILABLE = True
except ImportError:
    GOOGLE_SHEETS_AVAILABLE = False
    st.warning("Google Sheets libraries not installed. Run: `pip install gspread oauth2client`")

# ==================== PASTE YOUR CREDENTIALS HERE ====================
# WARNING: Don't commit credentials to GitHub! Use environment variables instead.
# To make it work, paste your credentials JSON here:
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

# ==================== YOUR SPREADSHEET ID ====================
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

# Initialize session state
if 'collection_data' not in st.session_state:
    st.session_state.collection_data = []
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'sales_success' not in st.session_state:
    st.session_state.sales_success = 0

class GoogleSheetsManager:
    def __init__(self, credentials_dict=None, spreadsheet_id=None):
        self.credentials_dict = credentials_dict
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

# ==================== AUTHENTICATION SECTION ====================
def show_auth_section():
    st.title("🔐 Card Ladder Authentication")
    
    st.write("### Enter Your Bearer Token")
    st.info("Paste your Bearer Token from Card Ladder DevTools below:")
    
    token_input = st.text_area(
        "Bearer Token:",
        height=150,
        placeholder="Paste your token here...\nExample: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
    )
    
    if st.button("Authenticate and Proceed", type="primary"):
        if token_input:
            token = token_input.strip()
            if not token.startswith('Bearer '):
                token = f'Bearer {token}'
            st.session_state.auth_token = token
            st.success("Token saved successfully!")
            st.rerun()
        else:
            st.error("Please enter a valid token")

# ==================== SCRAPER FUNCTIONS ====================
def fetch_collection(collection_id, limit_type, limit_value, auth_token, progress_bar, status_text):
    """Phase 1: Fetch all cards from collection"""
    all_cards = []
    page = 0
    limit = 20
    
    headers = {
        'authorization': auth_token,
        'accept': 'application/json',
        'user-agent': 'Mozilla/5.0'
    }
    
    status_text.text("Phase 1: Fetching collection...")
    
    try:
        while True and st.session_state.processing:
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
                st.error(f"Error: Server returned {response.status_code}")
                break
                
            data = response.json()
            hits = data.get('hits', [])
            total = data.get('totalHits', 0)
            
            if not hits:
                break
                
            all_cards.extend(hits)
            
            # Update progress
            current_count = len(all_cards)
            progress_bar.progress(min(current_count / max(total, 1), 1.0))
            status_text.text(f"Fetched {current_count} of {total} cards...")
            
            # Apply limit if specified
            if limit_type == "Number of Records":
                if current_count >= limit_value:
                    all_cards = all_cards[:limit_value]
                    break
            elif limit_type == "All Records" and current_count >= total:
                break
                
            if len(hits) < limit:
                break
                
            page += 1
            time.sleep(0.3)
        
        if all_cards:
            st.session_state.collection_data = all_cards
            return True, len(all_cards)
        else:
            st.warning("No cards found in collection")
            return False, 0
            
    except Exception as e:
        st.error(f"Phase 1 Error: {str(e)}")
        return False, 0

def fetch_sales_for_card(card_data, auth_token):
    """Phase 2: Fetch last 3 sales for a single card"""
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

def fetch_sales_for_all_cards(max_workers, auth_token, progress_bar, status_text):
    """Phase 2: Fetch sales for all collected cards"""
    if not st.session_state.collection_data:
        st.error("No collection data to process")
        return 0
    
    total_cards = len(st.session_state.collection_data)
    sales_success = 0
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, card in enumerate(st.session_state.collection_data, 1):
            if not st.session_state.processing:
                break
            
            futures.append((executor.submit(fetch_sales_for_card, card, auth_token), card, idx))
        
        # Process results as they complete
        completed = 0
        for future, card, idx in futures:
            if not st.session_state.processing:
                break
            
            completed += 1
            result = future.result()
            
            if result:
                # Merge sales data into card
                card.update(result)
                sales_success += 1
            
            # Update progress
            progress_bar.progress(completed / total_cards)
            status_text.text(f"Processing sales: {completed}/{total_cards} cards")
            
            # Rate limiting
            time.sleep(0.2)
    
    st.session_state.sales_success = sales_success
    return sales_success

def save_results(collection_id, sales_success):
    """Save all data to files - TWO Excel files and Google Sheets"""
    try:
        # Get current date for filename and scrape date column
        current_date = datetime.now()
        scrape_date_filename = current_date.strftime("%Y-%b-%d")
        scrape_date_display = current_date.strftime("%Y-%m-%d")
        
        cid = collection_id.replace(':', '_')
        
        # Create DataFrames with "Scrape Date" column
        df = pd.json_normalize(st.session_state.collection_data)
        
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
            st.warning("'collectionCardId' column not found - Card Unique URLs will be empty")
        
        # ===== 1. SAVE EXCEL FILES =====
        # Save full Excel
        full_excel_name = f"Cardladder_{scrape_date_filename}_full.xlsx"
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
        
        # Save filtered Excel
        filtered_excel_name = f"Filter_cardladder_{scrape_date_filename}.xlsx"
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
        
        return df_full_clean, df_filtered_clean, full_excel_name, filtered_excel_name, sales_success
        
    except Exception as e:
        st.error(f"Error preparing results: {str(e)}")
        return None, None, None, None, 0

# ==================== MAIN APP ====================
def main_app():
    st.title("📦 Card Ladder Complete Scraper")
    
    # Sidebar for settings
    with st.sidebar:
        st.header("Settings")
        
        collection_id = st.text_input(
            "Collection ID:",
            value="zKC3o1sfYEcBGNaTPDRn",
            help="Enter the Card Ladder collection ID"
        )
        
        limit_type = st.selectbox(
            "Number of Records:",
            ["All Records", "Number of Records"]
        )
        
        if limit_type == "Number of Records":
            limit_value = st.number_input(
                "Limit to:",
                min_value=1,
                max_value=500,
                value=5,
                step=1
            )
        else:
            limit_value = None
        
        max_workers = st.slider(
            "Max Threads:",
            min_value=1,
            max_value=10,
            value=1
        )
        
        # Google Sheets credentials
        st.header("Google Sheets (Optional)")
        if GOOGLE_SHEETS_AVAILABLE:
            st.success("Google Sheets available")
            use_google_sheets = st.checkbox("Save to Google Sheets", value=False)
            
            if use_google_sheets:
                credentials_json = st.text_area(
                    "Paste Google Service Account JSON:",
                    height=200,
                    help="Paste your Google Service Account credentials JSON"
                )
        else:
            st.warning("Install gspread and oauth2client for Google Sheets")
            use_google_sheets = False
            credentials_json = None
    
    # Main content area
    if st.button("🚀 START COMPLETE PROCESS", type="primary", use_container_width=True):
        if not st.session_state.auth_token:
            st.error("Please authenticate first!")
            return
        
        st.session_state.processing = True
        
        # Create progress bars
        progress_bar1 = st.progress(0)
        status_text1 = st.empty()
        
        progress_bar2 = st.progress(0)
        status_text2 = st.empty()
        
        log_container = st.empty()
        
        # Phase 1: Fetch collection
        with log_container.container():
            st.subheader("Phase 1: Fetching Collection")
            success, card_count = fetch_collection(
                collection_id, 
                limit_type, 
                limit_value if limit_value else float('inf'),
                st.session_state.auth_token,
                progress_bar1,
                status_text1
            )
        
        if success and st.session_state.processing:
            # Phase 2: Fetch sales data
            with log_container.container():
                st.subheader("Phase 2: Fetching Sales Data")
                sales_success = fetch_sales_for_all_cards(
                    max_workers,
                    st.session_state.auth_token,
                    progress_bar2,
                    status_text2
                )
            
            if st.session_state.processing:
                # Save results
                with log_container.container():
                    st.subheader("Saving Results")
                    
                    df_full, df_filtered, full_name, filtered_name, sales_success = save_results(
                        collection_id, 
                        st.session_state.sales_success
                    )
                    
                    if df_full is not None:
                        # Download buttons
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.download_button(
                                label="📗 Download Full Excel",
                                data=df_full.to_csv(index=False).encode('utf-8'),
                                file_name=full_name.replace('.xlsx', '.csv'),
                                mime="text/csv"
                            )
                        
                        with col2:
                            st.download_button(
                                label="📘 Download Filtered Excel",
                                data=df_filtered.to_csv(index=False).encode('utf-8'),
                                file_name=filtered_name.replace('.xlsx', '.csv'),
                                mime="text/csv"
                            )
                        
                        # Google Sheets integration
                        if use_google_sheets and credentials_json:
                            try:
                                credentials_dict = json.loads(credentials_json)
                                google_sheets = GoogleSheetsManager(credentials_dict)
                                
                                success, message = google_sheets.connect()
                                if success:
                                    sheet_name = f"CardLadder_{datetime.now().strftime('%Y-%b-%d')}"
                                    spreadsheet, msg = google_sheets.create_or_open_sheet(sheet_name)
                                    
                                    if spreadsheet:
                                        # Save Full Data
                                        success, message = google_sheets.save_dataframe_to_sheet(
                                            spreadsheet, "Full Data", df_full
                                        )
                                        if success:
                                            st.success(f"✅ Full data saved to Google Sheets")
                                        
                                        # Save Filtered Data
                                        success, message = google_sheets.save_dataframe_to_sheet(
                                            spreadsheet, "Filtered Data", df_filtered
                                        )
                                        if success:
                                            st.success(f"✅ Filtered data saved to Google Sheets")
                                        
                                        # Show URL
                                        sheet_url = spreadsheet.url
                                        st.info(f"Google Sheets URL: [Click here]({sheet_url})")
                            except Exception as e:
                                st.error(f"Google Sheets error: {str(e)}")
                        
                        # Show summary
                        st.success("✨ PROCESS COMPLETE!")
                        st.metric("Total Cards", len(st.session_state.collection_data))
                        st.metric("Cards with Sales", sales_success)
                        
                        if sales_success > 0:
                            avg_values = []
                            current_values = []
                            for card in st.session_state.collection_data:
                                if 'avg_last_3_sales' in card and card['avg_last_3_sales'] is not None:
                                    avg_values.append(card['avg_last_3_sales'])
                                if 'currentValue' in card and card['currentValue'] is not None:
                                    current_values.append(card['currentValue'])
                            
                            if avg_values:
                                overall_avg = sum(avg_values) / len(avg_values)
                                st.metric("Overall Average of Last 3 Sales", f"${overall_avg:.2f}")
                            
                            if current_values:
                                overall_current = sum(current_values) / len(current_values)
                                st.metric("Overall Average Current Value", f"${overall_current:.2f}")
        
        st.session_state.processing = False
    
    # Stop button
    if st.session_state.processing:
        if st.button("⏹️ Stop Process", type="secondary"):
            st.session_state.processing = False
            st.rerun()

# ==================== MAIN EXECUTION ====================
def main():
    # Set page config
    st.set_page_config(
        page_title="Card Ladder Scraper",
        page_icon="📦",
        layout="wide"
    )
    
    # Check authentication
    if st.session_state.auth_token is None:
        show_auth_section()
    else:
        main_app()
        
        # Logout button in sidebar
        with st.sidebar:
            st.divider()
            if st.button("🔓 Logout"):
                st.session_state.auth_token = None
                st.session_state.collection_data = []
                st.session_state.processing = False
                st.rerun()

if __name__ == "__main__":
    main()
