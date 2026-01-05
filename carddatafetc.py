import streamlit as st
import requests
import json
import time
import pandas as pd

# --- Page Config ---
st.set_page_config(page_title="Card Ladder Scraper", layout="wide")

# --- Initialize Session ---
if 'data' not in st.session_state:
    st.session_state.data = []
if 'token' not in st.session_state:
    st.session_state.token = ""

# --- Sidebar ---
with st.sidebar:
    st.title("🔐 Auth")
    token_input = st.text_area("Paste Bearer Token:", value=st.session_state.token, height=150)
    if st.button("Save Token"):
        st.session_state.token = token_input
        st.success("Token saved!")
    
    st.divider()
    st.info("The script will now automatically loop through all pages to find every item.")

# --- Main App ---
st.title("📦 Card Ladder Full Collection Scraper")

# 1. Settings Row
col1, col2, col3 = st.columns([2, 1, 1])
with col1:
    coll_id = st.text_input("Collection ID", "9Kr6jcPHdz77FNU9TVS4")
with col2:
    sort_by = st.selectbox("Sort By", ['dateAdded', 'value', 'grade', 'name', 'player'])
with col3:
    st.write(" ") # spacer
    fetch_all = st.button("🚀 Scrape Everything", use_container_width=True)

# 2. Scraping Logic with Pagination
if fetch_all:
    if not st.session_state.token:
        st.error("Please enter your token in the sidebar first!")
    else:
        all_results = []
        current_page = 1
        limit_per_page = 20
        
        status_container = st.empty()
        progress_bar = st.progress(0)
        
        headers = {
            'authorization': st.session_state.token,
            'accept': 'application/json, text/plain, */*',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        }

        try:
            while True:
                status_container.info(f"Scraping Page {current_page}... (Items found so far: {len(all_results)})")
                
                params = {
                    'index': 'collectioncards',
                    'limit': limit_per_page,
                    'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true',
                    'sort': sort_by,
                    'direction': 'desc',
                    'page': current_page
                }
                
                res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params, timeout=30)
                
                if res.status_code == 200:
                    data_json = res.json()
                    
                    # Extract the list of cards from the response
                    # Usually looks for keys like 'results', 'cards', or 'items'
                    page_items = next((v for v in data_json.values() if isinstance(v, list)), [])
                    
                    if not page_items:
                        break # No more items found, exit loop
                    
                    all_results.extend(page_items)
                    
                    # If we got fewer items than the limit, we've reached the end
                    if len(page_items) < limit_per_page:
                        break
                        
                    current_page += 1
                    time.sleep(0.3) # Short delay to prevent rate limiting
                
                elif res.status_code == 429:
                    status_container.warning("Rate limited! Sleeping for 5 seconds...")
                    time.sleep(5)
                    continue
                else:
                    st.error(f"Error {res.status_code}: {res.text}")
                    break

            st.session_state.data = all_results
            status_container.success(f"✅ Finished! Total items scraped: {len(all_results)}")
            progress_bar.progress(100)

        except Exception as e:
            st.error(f"An error occurred: {e}")

# 3. Display Results
if st.session_state.data:
    st.divider()
    df = pd.json_normalize(st.session_state.data)
    
    # Summary Metrics
    m1, m2 = st.columns(2)
    m1.metric("Total Items", len(df))
    if 'player' in df.columns:
        m2.metric("Unique Players", len(df['player'].unique()))

    # Downloads
    c1, c2 = st.columns(2)
    csv_data = df.to_csv(index=False).encode('utf-8')
    c1.download_button("📥 Download CSV", csv_data, f"collection_{coll_id}.csv", "text/csv", use_container_width=True)
    
    json_data = json.dumps(st.session_state.data, indent=2)
    c2.download_button("📥 Download JSON", json_data, f"collection_{coll_id}.json", "application/json", use_container_width=True)
    
    # Preview
    st.subheader("Data Preview")
    st.dataframe(df, use_container_width=True)
