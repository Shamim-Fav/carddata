import streamlit as st
import requests
import json
import time
import pandas as pd
import io
from datetime import datetime

# --- Page Config ---
st.set_page_config(page_title="Card Ladder Full Scraper", page_icon="📦", layout="wide")

# Initialize session state
if 'full_data' not in st.session_state:
    st.session_state.full_data = []

# --- Main UI ---
st.title("📦 Card Ladder Full Collection Scraper")

with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150)
    if st.button("🗑️ Clear Data"):
        st.session_state.full_data = []
        st.rerun()

col1, col2 = st.columns([2, 1])
with col1:
    coll_id = st.text_input("Collection ID", value="Gp4YlnON0enGVD2BBiAR")
with col2:
    st.write(" ")
    st.write(" ")
    run_scrape = st.button("🚀 Start Full Fetch")

if run_scrape:
    if not token_input:
        st.error("Please provide a token!")
    else:
        all_results = []
        current_page = 0  
        limit = 20
        has_more = True
        
        headers = {
            'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}",
            'accept': 'application/json',
            'user-agent': 'Mozilla/5.0',
            'Cache-Control': 'no-cache'
        }

        status_container = st.empty()
        
        while has_more:
            params = {'index': 'collectioncards', 'page': current_page, 'limit': limit, 
                      'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true',
                      'sort': 'dateAdded', 'direction': 'asc'}
            
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
                        status_container.success(f"✅ Collected {len(all_results)} of {total_hits} items")
                        if len(all_results) >= total_hits or len(page_items) < limit:
                            has_more = False
                        else:
                            current_page += 1
                            time.sleep(0.3)
                else:
                    st.error(f"Error {response.status_code}")
                    break
            except Exception as e:
                st.error(f"Connection failed: {e}")
                break
        
        st.session_state.full_data = all_results

# --- Export Section ---
if st.session_state.full_data:
    st.divider()
    df = pd.json_normalize(st.session_state.full_data)
    
    st.subheader("📊 Export Results")
    c1, c2, c3 = st.columns(3)
    
    # --- EXCEL DOWNLOAD (The part that was crashing) ---
    try:
        output_excel = io.BytesIO()
        # Explicitly using openpyxl
        with pd.ExcelWriter(output_excel, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Collection')
        excel_data = output_excel.getvalue()
        c1.download_button("📗 Download Excel (.xlsx)", data=excel_data, 
                           file_name=f"cards_{coll_id}.xlsx", use_container_width=True)
    except ModuleNotFoundError:
        c1.error("❌ Install openpyxl to enable Excel export: `pip install openpyxl`")
    except Exception as e:
        c1.error(f"Excel Error: {e}")

    # --- CSV & JSON ---
    csv_data = df.to_csv(index=False, encoding='utf-8-sig').encode('utf-8')
    c2.download_button("📊 Download CSV (.csv)", data=csv_data, 
                       file_name=f"cards_{coll_id}.csv", use_container_width=True)

    json_data = json.dumps(st.session_state.full_data, indent=2).encode('utf-8')
    c3.download_button("💾 Download Raw JSON", data=json_data, 
                       file_name=f"cards_{coll_id}.json", use_container_width=True)

    # Preview
    st.dataframe(df, use_container_width=True)
