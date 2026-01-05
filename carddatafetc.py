import streamlit as st
import requests
import json
import time
import pandas as pd
import io
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Card Ladder Scraper", page_icon="📈", layout="wide")

# Initialize session state
if 'full_data' not in st.session_state:
    st.session_state.full_data = []

# --- Main UI ---
st.title("📈 Card Ladder Collection Dashboard")

with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150, help="Found in DevTools under 'authorization'")
    st.divider()
    if st.button("🗑️ Reset Application"):
        st.session_state.full_data = []
        st.rerun()

# --- Input Section ---
col1, col2 = st.columns([2, 1])
with col1:
    coll_id = st.text_input("Collection ID", value="Gp4YlnON0enGVD2BBiAR")
with col2:
    st.write(" ") # Padding
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
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Cache-Control': 'no-cache'
        }

        status_container = st.empty()
        progress_bar = st.progress(0)
        
        while has_more:
            params = {
                'index': 'collectioncards',
                'page': current_page,
                'limit': limit,
                'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true',
                'sort': 'dateAdded',
                'direction': 'asc'
            }
            
            try:
                response = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
                
                if response.status_code == 200:
                    data = response.json()
                    page_items = data.get('hits', [])
                    total_hits = data.get('totalHits', 0)
                    
                    if not page_items:
                        has_more = False
                    else:
                        all_results.extend(page_items)
                        # Progress Update
                        perc = min(len(all_results) / total_hits, 1.0) if total_hits > 0 else 1.0
                        progress_bar.progress(perc)
                        status_container.success(f"✅ Collected {len(all_results)} / {total_hits}")
                        
                        if len(all_results) >= total_hits or len(page_items) < limit:
                            has_more = False
                        else:
                            current_page += 1
                            time.sleep(0.3)
                else:
                    st.error(f"Server Error: {response.status_code}")
                    break
            except Exception as e:
                st.error(f"Request failed: {e}")
                break
        
        st.session_state.full_data = all_results

# --- Dashboard & Downloads ---
if st.session_state.full_data:
    df = pd.json_normalize(st.session_state.full_data)
    
    # 📊 Metrics Dashboard
    st.divider()
    m1, m2, m3, m4 = st.columns(4)
    
    total_value = df['currentValue'].sum() if 'currentValue' in df.columns else 0
    total_cost = df['investment'].sum() if 'investment' in df.columns else 0
    profit = total_value - total_cost
    
    m1.metric("Total Cards", len(df))
    m2.metric("Market Value", f"${total_value:,.2f}")
    m3.metric("Total Investment", f"${total_cost:,.2f}")
    m4.metric("Estimated P/L", f"${profit:,.2f}", delta=f"{((profit/total_cost)*100 if total_cost > 0 else 0):.1f}%")

    # 📥 Download Buttons
    st.subheader("📥 Export Data")
    d1, d2, d3 = st.columns(3)
    
    # Excel Logic (The fix for your error)
    try:
        buffer = io.BytesIO()
        with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='CollectionData')
        d1.download_button("📗 Download Excel", data=buffer.getvalue(), 
                           file_name=f"card_ladder_{coll_id}.xlsx", 
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                           use_container_width=True)
    except Exception as e:
        d1.error("Excel Error: Missing openpyxl in requirements.txt")

    # CSV Logic
    csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
    d2.download_button("📊 Download CSV", data=csv_data, 
                       file_name=f"card_ladder_{coll_id}.csv", use_container_width=True)

    # JSON Logic
    json_str = json.dumps(st.session_state.full_data, indent=2).encode('utf-8')
    d3.download_button("💾 Download JSON", data=json_str, 
                       file_name=f"card_ladder_{coll_id}.json", use_container_width=True)

    # Preview
    st.subheader("👀 Data Preview")
    st.dataframe(df, use_container_width=True)
