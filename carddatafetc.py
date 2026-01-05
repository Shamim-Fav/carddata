import streamlit as st
import requests
import json
import time
import pandas as pd
from datetime import datetime
from io import BytesIO

# --- Page Config ---
st.set_page_config(page_title="Card Ladder Fetcher", page_icon="📦", layout="wide")

# --- Session State Initialization ---
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

def fetch_data(collection_id, query, sort_by, sort_dir, limit=20):
    headers = create_headers(st.session_state.auth_token)
    base_url = 'https://search-zzvl7ri3bq-uc.a.run.app/search'
    
    all_cards = []
    page = 1
    has_more = True
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    while has_more:
        status_text.text(f"Fetching page {page}...")
        params = {
            'index': 'collectioncards',
            'query': query,
            'limit': limit,
            'filters': f'collectionId:{collection_id}|hasQuantityAvailable:true',
            'sort': sort_by,
            'direction': sort_dir,
            'page': page
        }
        
        try:
            response = requests.get(base_url, headers=headers, params=params, timeout=30)
            if response.status_code == 200:
                data = response.json()
                
                # Dynamic key finding (similar to your original script)
                results = []
                for key, value in data.items():
                    if isinstance(value, list):
                        results = value
                        break
                
                if results:
                    all_cards.extend(results)
                    if len(results) < limit:
                        has_more = False
                    else:
                        page += 1
                        time.sleep(0.3)
                else:
                    has_more = False
            elif response.status_code == 429:
                status_text.warning("Rate limited. Waiting 5 seconds...")
                time.sleep(5)
            else:
                st.error(f"Error {response.status_code}: {response.text}")
                break
        except Exception as e:
            st.error(f"Connection error: {e}")
            break
            
    progress_bar.empty()
    status_text.success(f"Finished! Total cards found: {len(all_cards)}")
    return all_cards

# --- Sidebar: Authentication ---
with st.sidebar:
    st.title("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150, help="Starts with 'Bearer eyJ...'")
    
    if st.button("Save Token"):
        if token_input:
            if not token_input.startswith("Bearer "):
                st.session_state.auth_token = f"Bearer {token_input}"
            else:
                st.session_state.auth_token = token_input
            st.success("Token Saved!")
        else:
            st.error("Please enter a token.")

    st.markdown("---")
    st.markdown("### 📋 Instructions")
    st.caption("1. Login to app.cardladder.com")
    st.caption("2. Open DevTools (F12) > Network")
    st.caption("3. Filter for 'search'")
    st.caption("4. Copy 'authorization' header value")

# --- Main UI ---
st.title("📦 Card Ladder Collection Fetcher")

if not st.session_state.auth_token:
    st.info("Please enter your Bearer Token in the sidebar to begin.")
else:
    # Input Layout
    col1, col2 = st.columns(2)
    with col1:
        collection_id = st.text_input("Collection ID:", value="9Kr6jcPHdz77FNU9TVS4")
        query = st.text_input("Search Query (optional):", value="")
    with col2:
        sort_by = st.selectbox("Sort By:", ['dateAdded', 'name', 'player', 'year', 'grade', 'value'])
        sort_dir = st.radio("Direction:", ['desc', 'asc'], horizontal=True)

    if st.button("🚀 Start Fetching Collection", use_container_width=True):
        st.session_state.all_results = fetch_data(collection_id, query, sort_by, sort_dir)

    # --- Results Handling ---
    if st.session_state.all_results:
        df = pd.json_normalize(st.session_state.all_results)
        
        st.markdown("---")
        st.subheader("📊 Collection Summary")
        
        # Stats
        m1, m2, m3 = st.columns(3)
        m1.metric("Total Cards", len(df))
        if 'grade' in df.columns:
            m2.metric("Unique Grades", len(df['grade'].unique()))
        
        # Download Buttons
        d1, d2 = st.columns(2)
        
        csv = df.to_csv(index=False).encode('utf-8')
        d1.download_button("📥 Download CSV", data=csv, file_name=f"collection_{collection_id}.csv", mime="text/csv", use_container_width=True)
        
        json_str = json.dumps(st.session_state.all_results, indent=2)
        d2.download_button("📥 Download JSON", data=json_str, file_name=f"collection_{collection_id}.json", mime="application/json", use_container_width=True)

        # Data Preview
        st.subheader("👀 Data Preview")
        st.dataframe(df, use_container_width=True)

        # Grade Distribution Chart
        if 'grade' in df.columns:
            st.subheader("📈 Grade Distribution")
            st.bar_chart(df['grade'].value_counts())
