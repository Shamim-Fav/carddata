import streamlit as st
import requests
import json
import time
import pandas as pd
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Card Ladder Fetcher", page_icon="📦", layout="wide")

# --- Session State ---
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = None
if 'all_results' not in st.session_state:
    st.session_state.all_results = []

def create_headers(token):
    return {
        'accept': 'application/json, text/plain, */*',
        'origin': 'https://app.cardladder.com',
        'referer': 'https://app.cardladder.com/',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'authorization': token
    }

# --- Sidebar: Authentication ---
with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150)
    
    if st.button("Apply Token"):
        if token_input:
            st.session_state.auth_token = token_input if token_input.startswith("Bearer ") else f"Bearer {token_input}"
            st.success("Token Active")
    
    st.markdown("---")
    st.markdown("### 📋 Quick Help")
    st.caption("1. Login to Card Ladder")
    st.caption("2. F12 > Network > Search for 'search'")
    st.caption("3. Copy the 'authorization' header")

# --- Main Page ---
st.title("📦 Card Ladder Collection Manager")

if not st.session_state.auth_token:
    st.warning("Please enter your Bearer Token in the sidebar to start.")
else:
    # 1. Input Section
    with st.container():
        st.subheader("Filter & Sort Settings")
        col1, col2, col3 = st.columns([2, 2, 1])
        
        with col1:
            collection_id = st.text_input("Collection ID", value="9Kr6jcPHdz77FNU9TVS4")
            query = st.text_input("Search Query (Optional)")
        with col2:
            sort_by = st.selectbox("Sort By", ['dateAdded', 'name', 'player', 'year', 'grade', 'value'])
            sort_dir = st.radio("Order", ['desc', 'asc'], horizontal=True)
        with col3:
            st.write(" ") # Alignment spacer
            st.write(" ")
            fetch_btn = st.button("🚀 Start Fetch", use_container_width=True)

    # 2. Execution Logic
    if fetch_btn:
        headers = create_headers(st.session_state.auth_token)
        all_cards = []
        page = 1
        limit = 20
        
        progress_text = st.empty()
        bar = st.progress(0)
        
        while True:
            progress_text.text(f"Fetching page {page}...")
            params = {
                'index': 'collectioncards', 'query': query, 'limit': limit,
                'filters': f'collectionId:{collection_id}|hasQuantityAvailable:true',
                'sort': sort_by, 'direction': sort_dir, 'page': page
            }
            
            try:
                res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    # Find list in response
                    results = next((v for v in data.values() if isinstance(v, list)), [])
                    
                    if not results: break
                    all_cards.extend(results)
                    
                    if len(results) < limit: break
                    page += 1
                    time.sleep(0.2)
                else:
                    st.error(f"Error {res.status_code}")
                    break
            except Exception as e:
                st.error(f"Failed: {e}")
                break
        
        st.session_state.all_results = all_cards
        progress_text.success(f"Done! Found {len(all_cards)} items.")
        bar.empty()

    # 3. Results Section (Only shows if data exists)
    if st.session_state.all_results:
        st.markdown("---")
        df = pd.json_normalize(st.session_state.all_results)
        
        # Top Row: Stats & Downloads
        stat1, stat2, dl1, dl2 = st.columns([1, 1, 1, 1])
        stat1.metric("Total Items", len(df))
        stat2.metric("Unique Players", len(df['player'].unique()) if 'player' in df.columns else "N/A")
        
        csv_data = df.to_csv(index=False).encode('utf-8')
        dl1.download_button("📥 Download CSV", data=csv_data, file_name="collection.csv", use_container_width=True)
        
        json_data = json.dumps(st.session_state.all_results, indent=2)
        dl2.download_button("📥 Download JSON", data=json_data, file_name="collection.json", use_container_width=True)

        # Bottom Row: Preview & Simple Chart
        st.subheader("Data Preview")
        st.dataframe(df, use_container_width=True)
        
        if 'grade' in df.columns:
            st.subheader("Grade Distribution")
            st.bar_chart(df['grade'].value_counts())
