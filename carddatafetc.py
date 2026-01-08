import streamlit as st
import requests
import json
import time
import pandas as pd
import io
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

# ==================== GOOGLE SHEETS CREDENTIALS ====================
GOOGLE_CREDENTIALS = {
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

# --- Page Config ---
st.set_page_config(
    page_title="Card Ladder Complete Scraper",
    page_icon="📦",
    layout="wide"
)

# Initialize session state
if 'full_data' not in st.session_state:
    st.session_state.full_data = []
if 'sales_data_added' not in st.session_state:
    st.session_state.sales_data_added = False
if 'processing' not in st.session_state:
    st.session_state.processing = False
if 'current_phase' not in st.session_state:
    st.session_state.current_phase = ""

# --- Styling ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { border-radius: 5px; }
    .stDownloadButton>button { border-radius: 5px; }
    .metric-card { 
        background-color: white; 
        padding: 15px; 
        border-radius: 10px; 
        border-left: 5px solid #007acc;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar: Authentication & Settings ---
with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area(
        "Paste Bearer Token:", 
        height=150, 
        help="Copy the 'authorization' header from DevTools."
    )
    
    st.divider()
    st.header("⚙️ Settings")
    
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    max_workers = st.slider("Max Threads", min_value=1, max_value=10, value=1)
    
    st.divider()
    
    if st.button("🗑️ Clear All Data", type="secondary"):
        st.session_state.full_data = []
        st.session_state.sales_data_added = False
        st.session_state.processing = False
        st.rerun()
    
    if st.button("🛑 Stop Process", type="secondary"):
        st.session_state.processing = False
        st.rerun()

# --- Main UI ---
st.title("📦 Card Ladder Complete Scraper")
st.info("This tool performs a two-phase scrape: 1) Fetch collection cards, 2) Fetch last 3 sales for each card")

# --- Status Display ---
status_col1, status_col2 = st.columns([3, 1])
with status_col1:
    status_placeholder = st.empty()
with status_col2:
    if st.session_state.processing:
        st.warning("⏳ Processing...")

# Start Button
col1, col2, col3 = st.columns([2, 1, 1])
with col2:
    start_button = st.button("🚀 START COMPLETE PROCESS", type="primary", use_container_width=True)

# --- Functions ---
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
    
    status_placeholder.info("**Phase 1:** Fetching collection cards...")
    
    try:
        while True and st.session_state.processing:
            # Create progress display
            progress_text = f"Fetching page {page}..."
            status_placeholder.info(f"**Phase 1:** {progress_text}")
            
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
                status_placeholder.error(f"Error: Server returned {response.status_code}")
                break
                
            data = response.json()
            hits = data.get('hits', [])
            total = data.get('totalHits', 0)
            
            if not hits:
                break
                
            all_cards.extend(hits)
            
            if len(all_cards) >= total or len(hits) < limit:
                break
                
            page += 1
            time.sleep(0.3)
        
        if all_cards:
            st.session_state.full_data = all_cards
            status_placeholder.success(f"**Phase 1 Complete:** Collected {len(all_cards)} cards")
            return True, len(all_cards)
        else:
            status_placeholder.warning("No cards found in collection")
            return False, 0
            
    except Exception as e:
        status_placeholder.error(f"Phase 1 Error: {str(e)}")
        return False, 0

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
        
        # Search sales archive
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

def fetch_sales_for_all_cards():
    """Phase 2: Fetch sales for all collected cards"""
    if not st.session_state.full_data:
        return 0
    
    total_cards = len(st.session_state.full_data)
    sales_success = 0
    progress_bar = st.progress(0)
    progress_text = st.empty()
    
    status_placeholder.info("**Phase 2:** Fetching sales data...")
    
    # Process cards in batches
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, card in enumerate(st.session_state.full_data, 1):
            if not st.session_state.processing:
                break
            futures.append((executor.submit(fetch_sales_for_card, card), card, idx))
        
        # Process results as they complete
        completed = 0
        results = []
        
        for future, card, idx in futures:
            if not st.session_state.processing:
                break
            
            result = future.result()
            
            if result:
                # Merge sales data into card
                card.update(result)
                sales_success += 1
                
                player = card.get('player', f'Card {idx}')
                sales_found = result.get('sales_found', 0)
                avg_price = result.get('avg_last_3_sales')
                
                if sales_found > 0:
                    result['player'] = player
                    result['idx'] = idx
                    results.append(result)
            else:
                player = card.get('player', f'Card {idx}')
            
            completed += 1
            
            # Update progress
            progress = completed / total_cards
            progress_bar.progress(progress)
            progress_text.text(f"Processed {completed}/{total_cards} cards ({progress*100:.1f}%)")
            
            # Rate limiting
            time.sleep(0.1)
    
    # Update session state
    st.session_state.sales_data_added = (sales_success > 0)
    
    # Display results in an expander
    if results:
        with st.expander("📊 Sales Fetch Results", expanded=True):
            results_df = pd.DataFrame(results)
            st.dataframe(results_df[['idx', 'player', 'sales_found', 'avg_last_3_sales']], use_container_width=True)
    
    progress_bar.empty()
    progress_text.empty()
    
    return sales_success

def create_dataframes():
    """Create full and filtered DataFrames"""
    if not st.session_state.full_data:
        return None, None
    
    # Get current date
    current_date = datetime.now()
    scrape_date_display = current_date.strftime("%Y-%m-%d")
    scrape_date_filename = current_date.strftime("%Y-%b-%d")
    
    # Create DataFrame
    df = pd.json_normalize(st.session_state.full_data)
    
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
    
    # Create full DataFrame with ordered columns
    cols = list(df.columns)
    sale_price_cols = sorted([c for c in cols if 'sale' in c and 'price' in c])
    sale_date_cols = sorted([c for c in cols if 'sale' in c and 'date' in c])
    sale_listingtype_cols = sorted([c for c in cols if 'sale' in c and 'listingType' in c])
    special_cols = [c for c in cols if 'avg_last_3_sales' in c or 'sales_count_for_avg' in c]
    other_cols = ['Scrape Date', 'Card Unique URL'] + [c for c in cols if c not in (['Scrape Date', 'Card Unique URL'] + sale_price_cols + sale_date_cols + 
                 sale_listingtype_cols + special_cols)]
    ordered_cols = (other_cols + sale_price_cols + sale_date_cols + sale_listingtype_cols + special_cols)
    df_full = df[ordered_cols]
    
    # Create filtered DataFrame
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
    
    return df_full, df_filtered, scrape_date_filename

# --- Main Processing Logic ---
if start_button and not st.session_state.processing:
    if not token_input:
        st.error("❌ Please provide a Bearer Token in the sidebar!")
    else:
        st.session_state.processing = True
        st.session_state.current_phase = "Phase 1"
        
        # Run Phase 1
        phase1_success, card_count = fetch_collection()
        
        if phase1_success and st.session_state.processing:
            st.session_state.current_phase = "Phase 2"
            
            # Run Phase 2
            sales_success = fetch_sales_for_all_cards()
            
            if st.session_state.processing:
                # Create DataFrames
                df_full, df_filtered, scrape_date_filename = create_dataframes()
                
                if df_full is not None:
                    # Display summary metrics
                    st.divider()
                    st.subheader("📊 Process Summary")
                    
                    col1, col2, col3, col4 = st.columns(4)
                    with col1:
                        st.metric("Total Cards", card_count)
                    with col2:
                        st.metric("Cards with Sales", sales_success)
                    with col3:
                        success_rate = (sales_success / card_count * 100) if card_count > 0 else 0
                        st.metric("Success Rate", f"{success_rate:.1f}%")
                    with col4:
                        if 'avg_last_3_sales' in df_full.columns:
                            avg_sales = df_full['avg_last_3_sales'].mean()
                            st.metric("Avg Last 3 Sales", f"${avg_sales:.2f}" if pd.notna(avg_sales) else "N/A")
                    
                    # File Download Section
                    st.divider()
                    st.subheader("📥 Download Results")
                    
                    tab1, tab2 = st.tabs(["📗 Full Data", "📘 Filtered Data"])
                    
                    with tab1:
                        st.write(f"**Full dataset** ({len(df_full)} rows, {len(df_full.columns)} columns)")
                        
                        # Excel download
                        output_excel = io.BytesIO()
                        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
                            df_full.to_excel(writer, index=False, sheet_name='Full Data')
                        excel_data = output_excel.getvalue()
                        
                        col1, col2, col3 = st.columns(3)
                        col1.download_button(
                            "Download Excel (.xlsx)",
                            data=excel_data,
                            file_name=f"Cardladder_{scrape_date_filename}_full.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        
                        # CSV download
                        csv_data = df_full.to_csv(index=False).encode('utf-8')
                        col2.download_button(
                            "Download CSV (.csv)",
                            data=csv_data,
                            file_name=f"Cardladder_{scrape_date_filename}_full.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        # JSON download
                        json_data = json.dumps(st.session_state.full_data, indent=2).encode('utf-8')
                        col3.download_button(
                            "Download JSON",
                            data=json_data,
                            file_name=f"Cardladder_{scrape_date_filename}_full.json",
                            mime="application/json",
                            use_container_width=True
                        )
                        
                        # Preview
                        with st.expander("🔍 Preview Full Data"):
                            st.dataframe(df_full.head(20), use_container_width=True)
                    
                    with tab2:
                        st.write(f"**Filtered dataset** ({len(df_filtered)} rows, {len(df_filtered.columns)} columns)")
                        
                        # Excel download
                        output_excel_filtered = io.BytesIO()
                        with pd.ExcelWriter(output_excel_filtered, engine='openpyxl') as writer:
                            df_filtered.to_excel(writer, index=False, sheet_name='Filtered Data')
                        excel_filtered_data = output_excel_filtered.getvalue()
                        
                        col1, col2 = st.columns(2)
                        col1.download_button(
                            "Download Excel (.xlsx)",
                            data=excel_filtered_data,
                            file_name=f"Filter_cardladder_{scrape_date_filename}.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            use_container_width=True
                        )
                        
                        # CSV download
                        csv_filtered_data = df_filtered.to_csv(index=False).encode('utf-8')
                        col2.download_button(
                            "Download CSV (.csv)",
                            data=csv_filtered_data,
                            file_name=f"Filter_cardladder_{scrape_date_filename}.csv",
                            mime="text/csv",
                            use_container_width=True
                        )
                        
                        # Preview
                        with st.expander("🔍 Preview Filtered Data"):
                            st.dataframe(df_filtered, use_container_width=True)
                    
                    st.success(f"✅ Process completed successfully!")
        
        st.session_state.processing = False
        st.session_state.current_phase = ""

# --- Display existing data if available ---
elif st.session_state.full_data:
    st.divider()
    st.subheader("📊 Existing Data")
    
    df_full, df_filtered, _ = create_dataframes()
    
    if df_full is not None:
        st.write(f"You have {len(df_full)} cards loaded in memory.")
        
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Total Cards", len(df_full))
        with col2:
            if 'avg_last_3_sales' in df_full.columns:
                cards_with_sales = df_full['avg_last_3_sales'].count()
                st.metric("Cards with Sales Data", cards_with_sales)
        
        # Quick preview
        with st.expander("🔍 Preview Data"):
            preview_cols = ['Scrape Date', 'player', 'condition', 'currentValue', 'avg_last_3_sales']
            available_preview = [c for c in preview_cols if c in df_full.columns]
            st.dataframe(df_full[available_preview].head(10), use_container_width=True)

# --- Display instructions when idle ---
elif not st.session_state.processing:
    st.divider()
    with st.expander("📋 How to use this tool"):
        st.markdown("""
        1. **Get your Bearer Token:**
           - Open Chrome DevTools (F12)
           - Go to Card Ladder website
           - Look for any network request to `search-zzvl7ri3bq-uc.a.run.app`
           - Copy the `authorization` header value
           - Paste it in the sidebar
        
        2. **Enter Collection ID:**
           - Find your collection ID from Card Ladder URL
           - Default is provided for testing
        
        3. **Configure Settings:**
           - Adjust thread count for speed
        
        4. **Click "START COMPLETE PROCESS"**
           - Phase 1: Fetches all cards from collection
           - Phase 2: Fetches last 3 sales for each card
        
        5. **Download Results:**
           - Full Excel with all data
           - Filtered Excel with key columns
           - CSV and JSON formats available
        """)
