import streamlit as st
import requests
import json
import time
import pandas as pd
import io
from datetime import datetime
import threading
import queue
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- Page Config ---
st.set_page_config(
    page_title="Card Ladder Complete Scraper", 
    page_icon="📦",
    layout="wide"
)

# Initialize session state for data persistence
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

# --- Styling ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    .stButton>button { border-radius: 5px; }
    .stDownloadButton>button { border-radius: 5px; }
    .log-container {
        background-color: #1e1e1e;
        color: #00ff00;
        padding: 10px;
        border-radius: 5px;
        font-family: 'Consolas', monospace;
        font-size: 12px;
        max-height: 400px;
        overflow-y: auto;
    }
    .phase-box {
        background-color: #262730;
        padding: 15px;
        border-radius: 10px;
        border-left: 5px solid #00ff88;
        margin-bottom: 15px;
    }
    </style>
    """, unsafe_allow_html=True)

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

# --- Sidebar: Authentication & Settings ---
with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150, help="Copy the 'authorization' header from DevTools.")
    
    st.divider()
    st.header("⚙️ Settings")
    
    collection_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    col1, col2 = st.columns(2)
    with col1:
        max_threads = st.number_input("Max Threads", min_value=1, max_value=10, value=1)
    with col2:
        request_delay = st.number_input("Request Delay (s)", min_value=0.0, max_value=2.0, value=0.2, step=0.1)
    
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
        st.rerun()

# --- Main UI ---
st.title("📦 Card Ladder Complete Scraper")
st.markdown("This tool fetches cards from your collection and their last 3 sales data.")

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
    start_button = st.button("🚀 Start Complete Process", type="primary", disabled=st.session_state.processing)
with col2:
    if st.button("📝 Clear Logs", disabled=st.session_state.processing):
        clear_logs()
        st.rerun()

# --- Log Display ---
st.subheader("📋 Processing Log")
log_container = st.container()
with log_container:
    if st.session_state.logs:
        st.markdown(f'<div class="log-container">{"<br>".join(st.session_state.logs[-20:])}</div>', unsafe_allow_html=True)
    else:
        st.info("Logs will appear here when the process starts.")

# --- Phase 1: Fetch Collection ---
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

# --- Phase 2: Fetch Sales Data ---
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

# --- Main Process Function ---
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
        
        # Prepare final data
        if st.session_state.full_data and not st.session_state.stop_requested:
            prepare_final_data(sales_success)
            
    except Exception as e:
        add_log(f"❌ Process Error: {str(e)}")
    finally:
        st.session_state.processing = False
        update_status("Complete", "Process finished")
        if st.session_state.stop_requested:
            add_log("⏹️ Process stopped by user")

# --- Prepare Final Data ---
def prepare_final_data(sales_success):
    """Prepare final data for download"""
    try:
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
        
        # Store in session state for download
        st.session_state.final_df = df
        
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

# --- Start Process ---
if start_button and token_input:
    if not st.session_state.processing:
        # Run in separate thread to avoid blocking
        import threading
        thread = threading.Thread(target=run_complete_process, daemon=True)
        thread.start()
        st.rerun()
else:
    if start_button and not token_input:
        st.error("Please provide a token in the sidebar!")

# --- Display Results & Downloads ---
if hasattr(st.session_state, 'final_df') and st.session_state.final_df is not None and not st.session_state.processing:
    st.divider()
    st.subheader("📊 Export Results")
    
    df = st.session_state.final_df
    
    # Create two export options
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

# --- Auto-refresh logs while processing ---
if st.session_state.processing:
    st.rerun()
