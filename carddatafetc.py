import streamlit as st
import requests
import json
import time
import pandas as pd
import io
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Card Ladder Scraper", page_icon="🃏", layout="wide")

if 'full_data' not in st.session_state:
    st.session_state.full_data = []

st.title("🃏 Card Ladder Collection Scraper")

# --- Sidebar ---
with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150)
    if st.button("🗑️ Reset Application"):
        st.session_state.full_data = []
        st.rerun()

# --- Inputs ---
col1, col2 = st.columns([2, 1])
with col1:
    coll_id = st.text_input("Collection ID", value="Gp4YlnON0enGVD2BBiAR")
with col2:
    st.write(" ")
    st.write(" ")
    run_scrape = st.button("🚀 Start Full Fetch (74 Items)")

# --- Scraper Logic ---
if run_scrape:
    if not token_input:
        st.error("Please provide a token!")
    else:
        all_results = []
        page = 0
        limit = 20
        headers = {
            'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}",
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0',
        }
        
        status = st.empty()
        bar = st.progress(0)
        
        while True:
            params = {
                'index': 'collectioncards',
                'page': page,
                'limit': limit,
                'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true',
                'sort': 'dateAdded',
                'direction': 'asc'
            }
            
            try:
                res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
                if res.status_code == 200:
                    data = res.json()
                    hits = data.get('hits', [])
                    total = data.get('totalHits', 74) # Uses 74 based on your logs
                    
                    if not hits: break
                    
                    all_results.extend(hits)
                    progress = min(len(all_results) / total, 1.0)
                    bar.progress(progress)
                    status.success(f"✅ Collected {len(all_results)} of {total}")
                    
                    if len(all_results) >= total or len(hits) < limit: break
                    page += 1
                    time.sleep(0.3)
                else:
                    st.error(f"Error {res.status_code}: Check your token.")
                    break
            except Exception as e:
                st.error(f"Request failed: {e}")
                break
        
        st.session_state.full_data = all_results

# --- Dashboard & Downloads ---
if st.session_state.full_data:
    df = pd.json_normalize(st.session_state.full_data)
    st.divider()
    
    # Metrics
    m1, m2, m3 = st.columns(3)
    val = df['currentValue'].sum() if 'currentValue' in df.columns else 0
    m1.metric("Total Cards", len(df))
    m2.metric("Market Value", f"${val:,.2f}")
    m3.info("Files ready for download below")

    # Exports
    st.subheader("📥 Export Data")
    d1, d2 = st.columns(2)

    # EXCEL EXPORT (The fix)
    try:
        excel_buffer = io.BytesIO()
        # We specify engine='openpyxl' which is now in your requirements.txt
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cards')
        
        d1.download_button(
            label="📗 Download Excel (.xlsx)",
            data=excel_buffer.getvalue(),
            file_name=f"cards_{coll_id}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )
    except Exception as e:
        d1.error(f"Excel error: {e}")

    # CSV EXPORT
    csv = df.to_csv(index=False).encode('utf-8-sig')
    d2.download_button("📊 Download CSV (.csv)", data=csv, 
                       file_name=f"cards_{coll_id}.csv", use_container_width=True)

    st.dataframe(df, use_container_width=True)
