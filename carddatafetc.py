import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io
import time
import re

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
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/cardladder%40cardladder.iam.gserviceaccount.com"
        }
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google Auth Error: {e}")
        return None

SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

# ==================== IMPROVED SEARCH LOGIC ====================
def clean_label_for_search(label):
    """Clean the label to improve search matching"""
    # Remove grade at the end for broader search
    label = re.sub(r'\s+(PSA|BGS|SGC|CGC)\s+\d+$', '', label)
    # Remove "PSA 10" from anywhere
    label = re.sub(r'\s+PSA\s+10\s*', ' ', label)
    return label.strip()

def fetch_sales_smart(token, card):
    """Smart sales fetching with multiple fallback strategies"""
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    
    # Extract card info
    label = card.get('label', '')
    player = card.get('player', '')
    year = card.get('year', '')
    set_name = card.get('set', '')
    condition = card.get('condition', '')
    variation = card.get('variation', '')
    card_number = card.get('number', '')
    
    res_data = {
        'total_sales_in_db': 0,
        'sale1_price': None,
        'sale1_date': None,
        'sale2_price': None,
        'sale2_date': None,
        'sale3_price': None,
        'sale3_date': None,
        'sale4_price': None,
        'sale4_date': None,
        'avg_last_4_sales': 0,
        'search_method_used': 'None',
        'sales_found': False
    }
    
    # Strategy 1: Full Label (original)
    search_queries = [
        ('Full Label', label),
        ('Clean Label', clean_label_for_search(label)),
        ('Player + Set', f"{player} {set_name}" if player and set_name else None),
        ('Player + Year', f"{player} {year}" if player and year else None),
        ('Player + Variation', f"{player} {variation}" if player and variation else None),
        ('Set + Number', f"{set_name} #{card_number}" if set_name and card_number else None),
        ('Player Only', player if player else None),
    ]
    
    best_hits = []
    best_total = 0
    used_strategy = None
    
    for strategy_name, query in search_queries:
        if not query or len(query) < 5:
            continue
            
        try:
            params = {
                'index': 'salesarchive',
                'query': query,
                'limit': 10,  # Get more to filter
                'sort': 'date',
                'direction': 'desc'
            }
            
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search',
                              headers=headers,
                              params=params,
                              timeout=10)
            
            if res.status_code == 200:
                data = res.json()
                hits = data.get('hits', [])
                
                # Filter hits to match card attributes
                filtered_hits = []
                for hit in hits:
                    # Match grade if card has condition
                    if condition and 'PSA' in condition:
                        hit_grade = hit.get('condition', '')
                        if hit_grade not in ['g10', '10', 'GEM MT 10']:
                            # Still include but mark as different grade
                            pass
                    
                    # Match year if available
                    if year:
                        hit_label = hit.get('label', '')
                        if str(year) not in hit_label:
                            # Check if year in label
                            if not re.search(rf'\b{year}\b', hit_label):
                                continue
                    
                    filtered_hits.append(hit)
                
                if len(filtered_hits) > best_total:
                    best_hits = filtered_hits
                    best_total = len(filtered_hits)
                    used_strategy = strategy_name
                    
                    # If we found good matches, break
                    if best_total >= 4:
                        break
                        
        except Exception as e:
            continue
    
    # Process best hits found
    if best_hits:
        res_data['total_sales_in_db'] = len(best_hits)
        res_data['search_method_used'] = used_strategy
        res_data['sales_found'] = True
        
        # Get last 4 sales
        for i in range(min(4, len(best_hits))):
            hit = best_hits[i]
            res_data[f'sale{i+1}_price'] = hit.get('price')
            res_data[f'sale{i+1}_date'] = hit.get('date')
        
        # Calculate average
        prices = [hit.get('price') for hit in best_hits[:4] if hit.get('price')]
        if prices:
            res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
    
    return res_data

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Card Ladder Scraper", layout="wide")
st.title("🕰️ Card Data Scraper - Smart Search")

with st.sidebar:
    st.header("Settings")
    auth_token = st.text_input("Enter Bearer Token", type="password")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    st.markdown("---")
    st.info("🔍 **Smart Search Strategy:**\n"
            "1. Full Label\n"
            "2. Clean Label (no grade)\n"
            "3. Player + Set\n"
            "4. Player + Year\n"
            "5. Player + Variation\n"
            "6. Set + Number\n"
            "7. Player Only")
    
    scrape_all = st.checkbox("Scrape ALL Cards in Collection", value=False)
    if not scrape_all:
        limit = st.number_input("Limit (number of cards)", value=5, min_value=1, max_value=100)
    else:
        st.info("Will fetch entire collection.")
        limit = 50000

if st.button("🚀 Start Scrape", type="primary"):
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
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                             headers=headers, 
                             params=params)
            
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
        
        st.write(f"✅ Found {len(cards)} cards to process")

        # --- PHASE 2: SMART SALES FETCHING ---
        status.write("📈 Fetching Sales History using Smart Search...")
        progress_sales = st.progress(0)
        
        sales_data = []
        total_to_process = len(cards)
        
        # Create placeholder for live results
        results_container = st.empty()
        
        for i, card in enumerate(cards):
            card_label = card.get('label', 'Unknown')
            status.write(f"Processing {i+1}/{total_to_process}: {card_label[:60]}...")
            
            s_result = fetch_sales_smart(auth_token, card)
            sales_data.append(s_result)
            
            # Show live results
            if s_result['sales_found']:
                results_container.info(f"✅ {card_label[:50]}... Found {s_result['total_sales_in_db']} sales using {s_result['search_method_used']}")
            else:
                results_container.warning(f"⚠️ {card_label[:50]}... No sales found")
            
            # Update Progress
            s_prog_val = (i + 1) / total_to_process
            progress_sales.progress(s_prog_val, text=f"Card {i+1}/{total_to_process}")
            
            time.sleep(0.1)  # Small delay to avoid rate limiting
        
        # Merge data
        for i, s in enumerate(sales_data):
            cards[i].update(s)
            
        progress_sales.empty()
        results_container.empty()

        # --- PHASE 3: PROCESSING DATA ---
        status.write("📊 Processing data...")
        df_full = pd.json_normalize(cards)
        scrape_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        df_full.insert(0, 'Scrape Date', scrape_date)
        
        if 'collectionCardId' in df_full.columns:
            df_full.insert(1, 'Card Unique URL', df_full['collectionCardId'].apply(
                lambda x: f"https://app.cardladder.com/card/{x}?profile=collection&showSales=True"))

        # Define columns
        TARGET_COLS = [
            'Scrape Date', 
            'Card Unique URL', 
            'label', 
            'condition', 
            'variation', 
            'player', 
            'year',
            'set',
            'number',
            'currentValue',
            'sales_found',
            'search_method_used',
            'total_sales_in_db',
            'avg_last_4_sales',
            'sale1_price', 
            'sale1_date', 
            'sale2_price', 
            'sale2_date', 
            'sale3_price', 
            'sale3_date', 
            'sale4_price', 
            'sale4_date'
        ]
        
        existing_cols = [col for col in TARGET_COLS if col in df_full.columns]
        df_filtered = df_full.reindex(columns=existing_cols).fillna('')

        # --- PHASE 4: GOOGLE SHEETS SYNC ---
        if st.checkbox("Sync to Google Sheets", value=True):
            status.write("📝 Updating Google Sheets...")
            client = get_gspread_client()
            if client:
                try:
                    sh = client.open_by_key(SPREADSHEET_ID)
                    ws = sh.sheet1
                    ws.clear()
                    
                    data_to_send = [df_filtered.columns.tolist()] + df_filtered.astype(str).values.tolist()
                    ws.update(data_to_send, value_input_option='USER_ENTERED')
                    st.success(f"✅ Sync Complete: {len(df_filtered)} cards sent to Google Sheets!")
                except Exception as e:
                    st.error(f"Google Sheet Error: {e}")
        else:
            status.write("⏭️ Skipping Google Sheets sync")

        status.update(label="Scrape Finished Successfully!", state="complete")

    # --- DOWNLOADS ---
    st.divider()
    st.subheader("📥 Download Results")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("Total Cards", len(df_filtered))
        
    with col2:
        cards_with_sales = df_filtered[df_filtered['sales_found'] == True].shape[0] if 'sales_found' in df_filtered.columns else 0
        st.metric("Cards with Sales", cards_with_sales)
        
    with col3:
        cards_without_sales = len(df_filtered) - cards_with_sales
        st.metric("Cards Without Sales", cards_without_sales)
        
    with col4:
        avg_price = df_filtered[df_filtered['avg_last_4_sales'] > 0]['avg_last_4_sales'].mean() if 'avg_last_4_sales' in df_filtered.columns else 0
        st.metric("Avg Sale Price", f"${avg_price:.2f}" if avg_price > 0 else "N/A")
    
    st.divider()
    
    # Show search strategy breakdown
    if 'search_method_used' in df_filtered.columns:
        st.subheader("📊 Search Strategy Success Rate")
        strategy_counts = df_filtered[df_filtered['search_method_used'] != '']['search_method_used'].value_counts()
        st.bar_chart(strategy_counts)
    
    st.divider()
    
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("📊 Filtered Data (With Sales Info)")
        st.dataframe(df_filtered, height=400, use_container_width=True)
        
        buf1 = io.BytesIO()
        with pd.ExcelWriter(buf1, engine='openpyxl') as writer:
            df_filtered.to_excel(writer, index=False)
        st.download_button(
            "📥 Download Filtered Excel", 
            buf1.getvalue(), 
            f"Filtered_Cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            use_container_width=True
        )

    with c2:
        st.subheader("📋 Cards Without Sales Data")
        if 'sales_found' in df_filtered.columns:
            no_sales_df = df_filtered[df_filtered['sales_found'] == False]
            if len(no_sales_df) > 0:
                st.dataframe(no_sales_df[['label', 'year', 'set', 'player']], height=400, use_container_width=True)
            else:
                st.success("🎉 All cards have sales data!")
        else:
            st.dataframe(df_full.head(10), height=400, use_container_width=True)
        
        buf2 = io.BytesIO()
        with pd.ExcelWriter(buf2, engine='openpyxl') as writer:
            df_full.to_excel(writer, index=False)
        st.download_button(
            "📥 Download FULL Master Excel", 
            buf2.getvalue(), 
            f"Full_Cards_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
            use_container_width=True
        )

st.divider()
st.caption(f"💡 Smart Search tries multiple strategies to find sales data | If a card shows no sales, it means no matches were found in the database")
