import streamlit as st
import requests
import pandas as pd
import io
import time
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor

# ==================== PAGE CONFIG ====================
st.set_page_config(
    page_title="Card Ladder Scraper",
    page_icon="📦",
    layout="wide"
)

# Initialize session state
if 'collection_data' not in st.session_state:
    st.session_state.collection_data = []
if 'processing' not in st.session_state:
    st.session_state.processing = False

# ==================== SIDEBAR ====================
with st.sidebar:
    st.title("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150)
    
    st.divider()
    st.title("⚙️ Settings")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    
    col1, col2 = st.columns(2)
    with col1:
        test_mode = st.checkbox("Test Mode", value=True)
    with col2:
        max_workers = st.slider("Max Threads", 1, 10, 3)
    
    test_limit = st.number_input("Test Limit", min_value=1, value=5, disabled=not test_mode)
    
    if st.button("🗑️ Clear Data"):
        st.session_state.collection_data = []
        st.rerun()

# ==================== SCRAPING LOGIC ====================
def fetch_collection():
    all_cards = []
    page, limit = 0, 20
    headers = {'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}", 'accept': 'application/json'}
    
    try:
        while st.session_state.processing:
            params = {'index': 'collectioncards', 'page': page, 'limit': limit, 'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'}
            response = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params, timeout=15)
            
            if response.status_code != 200: break
            data = response.json()
            hits = data.get('hits', [])
            if not hits: break
            
            all_cards.extend(hits)
            if test_mode and len(all_cards) >= test_limit:
                all_cards = all_cards[:test_limit]
                break
            if len(all_cards) >= data.get('totalHits', 0) or len(hits) < limit: break
            page += 1
            time.sleep(0.2)
        return all_cards
    except:
        return []

def fetch_sales_for_card(card_data):
    headers = {'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}", 'accept': 'application/json'}
    label = card_data.get('label', f"{card_data.get('year')} {card_data.get('player')}")
    params = {'index': 'salesarchive', 'query': label, 'page': 0, 'limit': 3, 'sort': 'date', 'direction': 'desc'}
    
    try:
        res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params, timeout=10)
        if res.status_code == 200:
            hits = res.json().get('hits', [])
            prices = [h.get('price') for h in hits if h.get('price')]
            sales_info = {'avg_last_3_sales': round(sum(prices)/len(prices), 2) if prices else None}
            for i, s in enumerate(hits[:3], 1):
                sales_info[f'sale{i}_price'] = s.get('price')
                sales_info[f'sale{i}_date'] = s.get('date', '').split('T')[0]
            return sales_info
    except:
        return None

# ==================== MAIN UI ====================
st.title("📦 Card Ladder Scraper")

if st.button("🚀 Start Scrape", type="primary") and token_input:
    st.session_state.processing = True
    
    # Phase 1
    cards = fetch_collection()
    st.session_state.collection_data = cards
    
    # Phase 2
    if cards:
        bar = st.progress(0)
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {executor.submit(fetch_sales_for_card, c): i for i, c in enumerate(cards)}
            for i, future in enumerate(futures):
                result = future.result()
                if result: st.session_state.collection_data[i].update(result)
                bar.progress((i + 1) / len(cards))
        
    st.session_state.processing = False
    st.success("Scrape Complete!")

# ==================== EXPORT SECTION ====================
if st.session_state.collection_data and not st.session_state.processing:
    df = pd.json_normalize(st.session_state.collection_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Full Excel
        out_full = io.BytesIO()
        df.to_excel(out_full, index=False)
        st.download_button("📗 Download Full Excel", out_full.getvalue(), "cardladder_full.xlsx", use_container_width=True)
        
    with col2:
        # Filtered Excel
        cols = ['label', 'condition', 'player', 'currentValue', 'avg_last_3_sales']
        df_filt = df[[c for c in cols if c in df.columns]]
        out_filt = io.BytesIO()
        df_filt.to_excel(out_filt, index=False)
        st.download_button("📘 Download Filtered Excel", out_filt.getvalue(), "cardladder_filtered.xlsx", use_container_width=True)

    st.subheader("Preview")
    st.dataframe(df.head(10))
