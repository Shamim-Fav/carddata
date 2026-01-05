import streamlit as st
import requests
import json
import time
import pandas as pd

# --- Page Config ---
st.set_page_config(page_title="Card Ladder", layout="wide")

# --- Initialize Session ---
if 'data' not in st.session_state:
    st.session_state.data = []
if 'token' not in st.session_state:
    st.session_state.token = ""

# --- Sidebar ---
with st.sidebar:
    st.title("🔐 Auth")
    token_input = st.text_area("Paste Token:", value=st.session_state.token)
    if st.button("Save Token"):
        st.session_state.token = token_input
        st.success("Token saved!")

# --- Main App (No Tabs) ---
st.title("📦 Card Ladder Manager")

# 1. Settings Row
col1, col2, col3 = st.columns(3)
with col1:
    coll_id = st.text_input("Collection ID", "9Kr6jcPHdz77FNU9TVS4")
with col2:
    sort_by = st.selectbox("Sort", ['dateAdded', 'value', 'grade'])
with col3:
    st.write(" ") # spacer
    fetch = st.button("🚀 Fetch Data", use_container_width=True)

# 2. Fetching Logic
if fetch:
    if not st.session_state.token:
        st.error("Missing Token in Sidebar!")
    else:
        with st.spinner("Fetching..."):
            headers = {'authorization': st.session_state.token}
            params = {
                'index': 'collectioncards',
                'limit': 20,
                'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true',
                'sort': sort_by,
                'direction': 'desc',
                'page': 1
            }
            try:
                res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, params=params)
                if res.status_code == 200:
                    # Logic to find the list in the JSON response
                    data_json = res.json()
                    st.session_state.data = next((v for v in data_json.values() if isinstance(v, list)), [])
                    st.success(f"Found {len(st.session_state.data)} items!")
                else:
                    st.error(f"Error {res.status_code}")
            except Exception as e:
                st.error(f"Error: {e}")

# 3. Results Row (Shows directly under the buttons)
if st.session_state.data:
    st.divider()
    df = pd.json_normalize(st.session_state.data)
    
    # Download Buttons
    c1, c2 = st.columns(2)
    c1.download_button("📥 Download CSV", df.to_csv(index=False), "data.csv", "text/csv")
    c2.download_button("📥 Download JSON", json.dumps(st.session_state.data), "data.json", "application/json")
    
    # Preview
    st.subheader("Data Preview")
    st.dataframe(df, use_container_width=True)
