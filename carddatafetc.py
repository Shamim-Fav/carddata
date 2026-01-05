import streamlit as st
import requests
import json
import time
import pandas as pd
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Card Ladder Scraper", layout="wide")

# Initialize Session States
if 'full_data' not in st.session_state:
    st.session_state.full_data = []

# --- Custom Styling ---
st.markdown("""
    <style>
    .stMetric { background-color: #f0f2f6; padding: 10px; border-radius: 10px; }
    </style>
""", unsafe_allow_html=True)

# --- Sidebar: Authentication ---
with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150, help="Copy from Network tab (starts with 'Bearer ')")
    
    if st.button("Clear Saved Results"):
        st.session_state.full_data = []
        st.rerun()

# --- Main App ---
st.title("📦 Card Ladder Full Collection Scraper")

# 1. Configuration Row
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    coll_id = st.text_input("Collection ID", value="9Kr6jcPHdz77FNU9TVS4")
with col2:
    sort_by = st.selectbox("Sort By", ['dateAdded', 'name', 'player', 'year', 'grade', 'value'])
with col3:
    st.write(" ") # alignment
    st.write(" ")
    start_btn = st.button("🚀 Scrape All Items", use_container_width=True)

# 2. Scraper Engine
if start_btn:
    if not token_input:
        st.error("Please paste your Bearer Token in the sidebar!")
    else:
        # Preparation
        all_results = []
        page = 1
        limit = 20 # Standard page size
        has_more = True
        
        headers = {
            'accept': 'application/json, text/plain, */*',
            'origin': 'https://app.cardladder.com',
            'referer': 'https://app.cardladder.com/',
            'authorization': token_input if token_input.startswith("Bearer ") else f"Bearer {token_input}",
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        }

        # Progress UI
        status_msg = st.empty()
        progress_bar = st.progress(0)
        
        while has_more:
            status_msg.info(f"Scraping Page {page}... (Total cards found: {len(all_results)})")
            
            params = {
                'index': 'collectioncards',
                'limit': limit,
                'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true',
                'sort': sort_by,
                'direction': 'desc',
                'page': page
            }
            
            try:
                response = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Logic to find the list regardless of key name (results, items, cards)
                    page_items = next((v for v in data.values() if isinstance(v, list)), [])
                    
                    if not page_items:
                        has_more = False
                    else:
                        all_results.extend(page_items)
                        # If we got less than the limit, there are no more pages
                        if len(page_items) < limit:
                            has_more = False
                        else:
                            page += 1
                            time.sleep(0.3) # Avoid triggering firewalls
                elif response.status_code == 429:
                    status_msg.warning("Rate limited! Waiting 5 seconds...")
                    time.sleep(5)
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
                    break
            except Exception as e:
                st.error(f"Connection failed: {e}")
                break
        
        st.session_state.full_data = all_results
        status_msg.success(f"✅ Scrape Complete! Found {len(all_results)} total items.")
        progress_bar.progress(100)

# 3. Results Display (Always visible if data exists)
if st.session_state.full_data:
    st.divider()
    df = pd.json_normalize(st.session_state.full_data)
    
    # Dashboard Header
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Cards", len(df))
    m2.metric("Unique Players", len(df['player'].unique()) if 'player' in df.columns else "N/A")
    m3.metric("Last Scraped", datetime.now().strftime("%H:%M:%S"))

    # Download Buttons
    dl1, dl2 = st.columns(2)
    csv = df.to_csv(index=False).encode('utf-8')
    dl1.download_button("📥 Download CSV", data=csv, file_name=f"cards_{coll_id}.csv", use_container_width=True)
    
    json_str = json.dumps(st.session_state.full_data, indent=2)
    dl2.download_button("📥 Download JSON", data=json_str, file_name=f"cards_{coll_id}.json", use_container_width=True)

    # Preview Table
    st.subheader("Data Preview")
    st.dataframe(df, use_container_width=True)
