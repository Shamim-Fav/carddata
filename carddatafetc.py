import streamlit as st
import requests
import json
import time
import pandas as pd
import io
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Card Ladder Full Scraper", page_icon="📦")

# Initialize session state for data persistence
if 'full_data' not in st.session_state:
    st.session_state.full_data = []
if 'total_found' not in st.session_state:
    st.session_state.total_found = 0

# --- Styling ---
st.markdown("""
    <style>
    .main { background-color: #f5f7f9; }
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #007acc; color: white; }
    .stDownloadButton>button { width: 100%; border-radius: 5px; background-color: #00aa55; color: white; }
    </style>
    """, unsafe_allow_html=True)

# --- Sidebar: Authentication ---
with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150, help="Copy the 'authorization' header from DevTools.")
    st.divider()
    if st.button("🗑️ Clear All Data"):
        st.session_state.full_data = []
        st.session_state.total_found = 0
        st.rerun()

# --- Main UI ---
st.title("📦 Card Data Scraper")
st.info("This tool fetches every card in a collection and exports them to Excel, CSV, and JSON.")

col1, col2 = st.columns([2, 1])
with col1:
    coll_id = st.text_input("Collection ID", value="Gp4YlnON0enGVD2BBiAR")
with col2:
    st.write(" ")
    st.write(" ")
    run_scrape = st.button("🚀 Start Full Fetch")

# --- Scraping Logic ---
if run_scrape:
    if not token_input:
        st.error("Please provide a token in the sidebar!")
    else:
        all_results = []
        current_page = 0  
        limit = 20
        has_more = True
        
        headers = {
            'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}",
            'accept': 'application/json, text/plain, */*',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Cache-Control': 'no-cache'
        }

        status_container = st.empty()
        progress_bar = st.progress(0)
        
        while has_more:
            status_container.info(f"🛰️ Fetching Page {current_page}...")
            
            params = {
                'index': 'collectioncards',
                'page': current_page,
                'limit': limit,
                'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true',
                'sort': 'dateAdded',
                'direction': 'asc'
            }
            
            try:
                response = requests.get(
                    'https://search-zzvl7ri3bq-uc.a.run.app/search', 
                    headers=headers, 
                    params=params,
                    timeout=20
                )
                
                if response.status_code == 200:
                    data = response.json()
                    page_items = data.get('hits', [])
                    total_hits = data.get('totalHits', 0)
                    st.session_state.total_found = total_hits
                    
                    if not page_items:
                        has_more = False
                    else:
                        all_results.extend(page_items)
                        
                        # Update progress
                        progress = min(len(all_results) / total_hits, 1.0) if total_hits > 0 else 1.0
                        progress_bar.progress(progress)
                        status_container.success(f"✅ Collected {len(all_results)} of {total_hits} items")
                        
                        if len(all_results) >= total_hits or len(page_items) < limit:
                            has_more = False
                        else:
                            current_page += 1
                            time.sleep(0.4) # Respectful delay
                else:
                    st.error(f"Server Error: {response.status_code}")
                    break
            except Exception as e:
                st.error(f"Connection failed: {e}")
                break
        
        st.session_state.full_data = all_results

# --- Data Display & Downloads ---
if st.session_state.full_data:
    st.divider()
    df = pd.json_normalize(st.session_state.full_data)
    
    st.subheader("📊 Export Results")
    c1, c2, c3 = st.columns(3)
    
    # 1. Excel Export (In-memory)
    output_excel = io.BytesIO()
    with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Collection')
    excel_data = output_excel.getvalue()
    c1.download_button("📗 Download Excel (.xlsx)", data=excel_data, file_name=f"collection_{coll_id}.xlsx", use_container_width=True)

    # 2. CSV Export
    csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
    c2.download_button("📊 Download CSV (.csv)", data=csv_data, file_name=f"collection_{coll_id}.csv", use_container_width=True)

    # 3. JSON Export
    json_data = json.dumps(st.session_state.full_data, indent=2).encode('utf-8')
    c3.download_button("💾 Download Raw JSON", data=json_data, file_name=f"collection_{coll_id}.json", use_container_width=True)

    # Preview Table
    st.subheader("👀 Data Preview")
    st.dataframe(df, use_container_width=True)
    
    # Summary Metrics
    st.subheader("📈 Collection Snapshot")
    m1, m2, m3 = st.columns(3)
    m1.metric("Total Cards", len(df))
    if 'currentValue' in df.columns:
        m2.metric("Market Value", f"${df['currentValue'].sum():,.2f}")
    if 'investment' in df.columns:
        m3.metric("Cost Basis", f"${df['investment'].sum():,.2f}")
