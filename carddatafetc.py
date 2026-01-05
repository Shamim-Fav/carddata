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
    if st.button("🗑️ Clear Results"):
        st.session_state.full_data = []
        st.rerun()

st.title("📦 Card Ladder Full Collection Scraper")

# --- 1. Settings ---
col1, col2 = st.columns([2, 1])
with col1:
    # Based on your response snippet, the collection ID is Gp4YlnON0enGVD2BBiAR
    coll_id = st.text_input("Collection ID", value="Gp4YlnON0enGVD2BBiAR")
with col2:
    st.write(" ")
    st.write(" ")
    run_scrape = st.button("🚀 Scrape All 74+ Items", use_container_width=True)

# --- 2. Scraping Engine ---
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
            'accept': 'application/json, text/plain, */*',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36'
        }

        status_ui = st.empty()
        
        while has_more:
            status_ui.info(f"Scraping Page {current_page}... (Progress: {len(all_results)} items collected)")
            
            params = {
                'index': 'collectioncards',
                'query': '',
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
                    
                    # TARGETING THE "hits" KEY
                    page_items = data.get('hits', [])
                    total_hits = data.get('totalHits', 0)
                    
                    if not page_items:
                        has_more = False
                    else:
                        all_results.extend(page_items)
                        
                        # Stop if we have collected everything the server says it has
                        if len(all_results) >= total_hits:
                            has_more = False
                            status_ui.success(f"✅ Success! All {total_hits} items scraped.")
                        else:
                            current_page += 1
                            time.sleep(0.5)
                else:
                    st.error(f"Error {response.status_code}")
                    break
            except Exception as e:
                st.error(f"Error: {e}")
                break
        
        st.session_state.full_data = all_results

# --- 3. Display Results ---
if st.session_state.full_data:
    st.divider()
    df = pd.json_normalize(st.session_state.full_data)
    
    # Download Section
    c1, c2 = st.columns(2)
    csv = df.to_csv(index=False).encode('utf-8')
    c1.download_button("📥 Download CSV", data=csv, file_name="full_collection.csv", use_container_width=True)
    
    json_bytes = json.dumps(st.session_state.full_data, indent=2).encode('utf-8')
    c2.download_button("📥 Download JSON", data=json_bytes, file_name="full_collection.json", use_container_width=True)

    # Summary Stats
    st.subheader("Collection Summary")
    s1, s2, s3 = st.columns(3)
    s1.metric("Total Cards", len(df))
    if 'currentValue' in df.columns:
        s2.metric("Total Value", f"${df['currentValue'].sum():,.2f}")
    if 'investment' in df.columns:
        s3.metric("Total Investment", f"${df['investment'].sum():,.2f}")

    # Preview
    st.dataframe(df, use_container_width=True)
