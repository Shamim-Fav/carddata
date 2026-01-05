import streamlit as st
import requests
import json
import time
import pandas as pd

# --- Page Config ---
st.set_page_config(page_title="Card Ladder Scraper", layout="wide")

if 'full_data' not in st.session_state:
    st.session_state.full_data = []

# --- Sidebar ---
with st.sidebar:
    st.header("🔐 Authentication")
    token_input = st.text_area("Paste Bearer Token:", height=150)
    st.divider()
    if st.button("🗑️ Reset App"):
        st.session_state.full_data = []
        st.rerun()

st.title("📦 Card Ladder Full Collection Scraper")

# --- 1. Settings ---
col1, col2 = st.columns([2, 1])
with col1:
    coll_id = st.text_input("Collection ID", value="AKnq10aqnUmBxKyGKBUK")
with col2:
    st.write(" ")
    st.write(" ")
    run_scrape = st.button("🚀 Scrape Entire Collection", use_container_width=True)

# --- 2. Scraping Engine ---
if run_scrape:
    if not token_input:
        st.error("Please provide a token in the sidebar!")
    else:
        all_results = []
        current_page = 0  # Start at 0 as per your payload
        limit = 20
        has_more = True
        
        headers = {
            'authorization': token_input if "Bearer" in token_input else f"Bearer {token_input}",
            'accept': 'application/json, text/plain, */*',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'Cache-Control': 'no-cache', # Forces fresh data
            'Pragma': 'no-cache'
        }

        status_ui = st.empty()
        progress_bar = st.progress(0)
        
        while has_more:
            status_ui.info(f"Scraping Page {current_page}... Items found: {len(all_results)}")
            
            # Using your exact URL parameters
            params = {
                'index': 'collectioncards',
                'query': '',
                'page': current_page,
                'limit': limit,
                'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true',
                'sort': 'dateAdded',
                'direction': 'asc',
                't': int(time.time()) # Cache buster to avoid 304 status
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
                    
                    # Logic to find the list of cards
                    page_items = []
                    if isinstance(data, list):
                        page_items = data
                    else:
                        # Card Ladder usually wraps the list in a key
                        for key in ['results', 'cards', 'items', 'data']:
                            if key in data and isinstance(data[key], list):
                                page_items = data[key]
                                break
                        # If still not found, take the first list found
                        if not page_items:
                            page_items = next((v for v in data.values() if isinstance(v, list)), [])
                    
                    if not page_items:
                        has_more = False
                    else:
                        all_results.extend(page_items)
                        # If we got fewer than 20 items, we are at the end
                        if len(page_items) < limit:
                            has_more = False
                        else:
                            current_page += 1
                            time.sleep(0.4) # Ethical delay
                
                elif response.status_code == 304:
                    # If it still hits a cache, we must stop or we loop forever
                    status_ui.warning("Server returned cached data (304). Stopping to prevent loop.")
                    has_more = False
                else:
                    st.error(f"Error {response.status_code}: {response.text}")
                    has_more = False
                    
            except Exception as e:
                st.error(f"Request failed: {e}")
                has_more = False
        
        st.session_state.full_data = all_results
        status_ui.success(f"✅ Success! Total cards scraped: {len(all_results)}")
        progress_bar.progress(100)

# --- 3. Display Results ---
if st.session_state.full_data:
    st.divider()
    df = pd.json_normalize(st.session_state.full_data)
    
    # Download Options
    c1, c2 = st.columns(2)
    csv = df.to_csv(index=False).encode('utf-8')
    c1.download_button("📥 Download CSV", data=csv, file_name=f"collection_{coll_id}.csv", use_container_width=True)
    
    json_bytes = json.dumps(st.session_state.full_data, indent=2).encode('utf-8')
    c2.download_button("📥 Download JSON", data=json_bytes, file_name=f"collection_{coll_id}.json", use_container_width=True)

    # Data Table
    st.subheader("Data Preview")
    st.dataframe(df, use_container_width=True)
