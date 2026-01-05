import streamlit as st
import requests
import json
import time
import pandas as pd
import io
from datetime import datetime

# --- Page Setup ---
st.set_page_config(page_title="Card Ladder Scraper", page_icon="🃏", layout="wide")

if 'full_data' not in st.session_state:
    st.session_state.full_data = []

st.title("🃏 Card Ladder Collection Scraper")

# --- Sidebar: Auth ---
with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150)
    st.caption("Tip: Copy the 'authorization' value from the Network tab in your browser.")
    if st.button("🗑️ Reset App"):
        st.session_state.full_data = []
        st.rerun()

# --- Main Inputs ---
col1, col2 = st.columns([2, 1])
with col1:
    coll_id = st.text_input("Collection ID", value="Gp4YlnON0enGVD2BBiAR")
with col2:
    st.write(" ")
    st.write(" ")
    run_scrape = st.button("🚀 Start Fetching 74/74")

# --- Scraper Logic ---
if run_scrape:
    if not token_input:
        st.error("Missing Token!")
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
            
            res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
            
            if res.status_code == 200:
                data = res.json()
                hits = data.get('hits', [])
                total = data.get('totalHits', 0)
                
                if not hits: break
                
                all_results.extend(hits)
                progress = min(len(all_results) / total, 1.0) if total > 0 else 1.0
                bar.progress(progress)
                status.success(f"✅ Collected {len(all_results)} of {total}")
                
                if len(all_results) >= total or len(hits) < limit: break
                page += 1
                time.sleep(0.3)
            else:
                st.error(f"Error: {res.status_code}")
                break
        
        st.session_state.full_data = all_results

# --- Results & Exports ---
if st.session_state.full_data:
    df = pd.json_normalize(st.session_state.full_data)
    
    # 📈 Dashboard Metrics
    st.divider()
    m1, m2, m3 = st.columns(3)
    val = df['currentValue'].sum() if 'currentValue' in df.columns else 0
    cost = df['investment'].sum() if 'investment' in df.columns else 0
    m1.metric("Total Cards", len(df))
    m2.metric("Market Value", f"${val:,.2f}")
    m3.metric("Total Profit/Loss", f"${(val - cost):,.2f}", delta=f"{(((val-cost)/cost)*100 if cost > 0 else 0):.1f}%")

    # 📥 Download Buttons
    st.subheader("📥 Export Your Files")
    d1, d2, d3 = st.columns(3)

    # EXCEL FIX
    try:
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Collection')
        d1.download_button("📗 Download Excel", data=excel_buffer.getvalue(), 
                           file_name="collection.xlsx", mime="application/vnd.ms-excel", use_container_width=True)
    except:
        d1.error("Install openpyxl to enable Excel.")

    # CSV
    csv = df.to_csv(index=False).encode('utf-8')
    d2.download_button("📊 Download CSV", data=csv, file_name="collection.csv", use_container_width=True)

    # JSON
    js = json.dumps(st.session_state.full_data, indent=2).encode('utf-8')
    d3.download_button("💾 Download JSON", data=js, file_name="collection.json", use_container_width=True)

    st.dataframe(df, use_container_width=True)
