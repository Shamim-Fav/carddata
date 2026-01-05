import streamlit as st
import requests
import pandas as pd
import json
import time
from datetime import datetime
from io import BytesIO

# Page configuration
st.set_page_config(
    page_title="Card Ladder Fetcher",
    page_icon="📊",
    layout="wide"
)

# Session state
if 'cards_data' not in st.session_state:
    st.session_state.cards_data = None
if 'df_cards' not in st.session_state:
    st.session_state.df_cards = None
if 'auth_token' not in st.session_state:
    st.session_state.auth_token = ""

# Title
st.title("🚀 Card Ladder Collection Fetcher")

# Main layout - NO TABS
col1, col2 = st.columns([1, 2])

with col1:
    # Authentication section
    st.subheader("🔐 Authentication")
    auth_token = st.text_area(
        "Bearer Token",
        value=st.session_state.auth_token,
        height=100,
        placeholder="Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImEzOGVhNmEwNDA4YjBjYzVkYTE4OWRmYzg4ODgyZDBmMWI3ZmJmMGUiLCJ0eXAiOiJKV1QifQ...",
        help="Get from Card Ladder DevTools"
    )
    
    if st.button("Save Token", use_container_width=True):
        if auth_token and auth_token.startswith('Bearer '):
            st.session_state.auth_token = auth_token
            st.success("✅ Token saved!")
        else:
            st.error("❌ Token must start with 'Bearer '")
    
    st.divider()
    
    # Fetch parameters
    st.subheader("⚙️ Fetch Parameters")
    collection_id = st.text_input(
        "Collection ID",
        value="9Kr6jcPHdz77FNU9TVS4",
        help="Find in your collection URL"
    )
    
    query = st.text_input(
        "Search Query (Optional)",
        placeholder="e.g., Mike Trout, PSA 10"
    )
    
    limit = st.selectbox(
        "Cards per page",
        options=[20, 50, 100],
        index=0
    )
    
    # Fetch buttons
    if st.button("🔍 Test Connection", use_container_width=True):
        if st.session_state.auth_token:
            with st.spinner("Testing connection..."):
                headers = {
                    'authorization': st.session_state.auth_token,
                    'accept': 'application/json'
                }
                params = {
                    'index': 'collectioncards',
                    'limit': 5,
                    'filters': f'collectionId:{collection_id}',
                    'page': 1
                }
                try:
                    response = requests.get(
                        'https://search-zzvl7ri3bq-uc.a.run.app/search',
                        headers=headers,
                        params=params,
                        timeout=10
                    )
                    if response.status_code == 200:
                        st.success("✅ Connection successful!")
                    else:
                        st.error(f"❌ Connection failed: {response.status_code}")
                except Exception as e:
                    st.error(f"❌ Connection error: {e}")
        else:
            st.error("❌ Please save token first")
    
    if st.button("🚀 Fetch Collection", type="primary", use_container_width=True):
        st.session_state.fetch_triggered = True

with col2:
    # Results and download section
    st.subheader("📊 Results")
    
    # Handle fetch if triggered
    if 'fetch_triggered' in st.session_state and st.session_state.fetch_triggered:
        if st.session_state.auth_token:
            # Fetch collection
            with st.spinner("Fetching collection data..."):
                headers = {
                    'authorization': st.session_state.auth_token,
                    'accept': 'application/json'
                }
                
                all_results = []
                page = 1
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                while True:
                    status_text.text(f"📄 Fetching page {page}...")
                    
                    params = {
                        'index': 'collectioncards',
                        'query': query,
                        'limit': limit,
                        'filters': f'collectionId:{collection_id}|hasQuantityAvailable:true',
                        'sort': 'dateAdded',
                        'direction': 'desc',
                        'page': page
                    }
                    
                    try:
                        response = requests.get(
                            'https://search-zzvl7ri3bq-uc.a.run.app/search',
                            headers=headers,
                            params=params,
                            timeout=30
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            
                            # Extract results
                            results = []
                            if 'results' in data:
                                results = data['results']
                            elif 'cards' in data:
                                results = data['cards']
                            elif 'items' in data:
                                results = data['items']
                            else:
                                for key, value in data.items():
                                    if isinstance(value, list):
                                        results = value
                                        break
                            
                            if results:
                                all_results.extend(results)
                                progress = min(100, (page * 20))
                                progress_bar.progress(progress)
                                
                                if len(results) < limit:
                                    break
                                page += 1
                                time.sleep(0.3)
                            else:
                                break
                        else:
                            st.error(f"❌ Error {response.status_code}")
                            break
                            
                    except Exception as e:
                        st.error(f"❌ Error: {e}")
                        break
                
                progress_bar.progress(100)
                status_text.text(f"✅ Fetched {len(all_results)} cards!")
                time.sleep(1)
                progress_bar.empty()
                status_text.empty()
                
                # Store in session state
                if all_results:
                    st.session_state.cards_data = all_results
                    
                    # Convert to DataFrame
                    flat_data = []
                    for card in all_results:
                        flat_card = {}
                        for key, value in card.items():
                            if isinstance(value, dict):
                                for subkey, subvalue in value.items():
                                    flat_card[f"{key}_{subkey}"] = subvalue
                            elif isinstance(value, list):
                                flat_card[key] = '; '.join(map(str, value))
                            else:
                                flat_card[key] = value
                        flat_data.append(flat_card)
                    
                    st.session_state.df_cards = pd.DataFrame(flat_data)
                    st.success(f"✅ Successfully fetched {len(all_results)} cards!")
        
        # Reset trigger
        st.session_state.fetch_triggered = False
    
    # Show results if available
    if st.session_state.df_cards is not None:
        df = st.session_state.df_cards
        
        # Stats
        col_stat1, col_stat2, col_stat3 = st.columns(3)
        with col_stat1:
            st.metric("Total Cards", len(df))
        with col_stat2:
            if 'value' in df.columns:
                try:
                    df['value'] = pd.to_numeric(df['value'], errors='coerce')
                    total_value = df['value'].sum()
                    st.metric("Total Value", f"${total_value:,.2f}")
                except:
                    st.metric("Total Value", "N/A")
        with col_stat3:
            if 'grade' in df.columns:
                st.metric("Unique Grades", df['grade'].nunique())
        
        st.divider()
        
        # Download section
        st.subheader("💾 Download Options")
        
        # Create timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Download buttons in columns
        dl_col1, dl_col2, dl_col3 = st.columns(3)
        
        with dl_col1:
            # CSV Download
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"cardladder_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with dl_col2:
            # Excel Download
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Cards')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📊 Download Excel",
                data=excel_data,
                file_name=f"cardladder_{timestamp}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
        
        with dl_col3:
            # JSON Download
            if st.session_state.cards_data:
                json_data = json.dumps({
                    'metadata': {
                        'total_cards': len(df),
                        'timestamp': timestamp,
                        'collection_id': collection_id
                    },
                    'cards': st.session_state.cards_data
                }, indent=2).encode('utf-8')
                
                st.download_button(
                    label="📄 Download JSON",
                    data=json_data,
                    file_name=f"cardladder_{timestamp}.json",
                    mime="application/json",
                    use_container_width=True
                )
        
        # Data preview
        st.divider()
        st.subheader("📋 Data Preview")
        st.dataframe(df.head(20), use_container_width=True)
        
        # Clear button
        if st.button("🗑️ Clear Results", type="secondary", use_container_width=True):
            st.session_state.cards_data = None
            st.session_state.df_cards = None
            st.rerun()
    
    else:
        # Show empty state
        st.info("👈 Enter your token and fetch parameters on the left, then click 'Fetch Collection'")

# Instructions in sidebar
with st.sidebar:
    st.header("📋 Instructions")
    st.markdown("""
    ### How to get your token:
    1. Login to [Card Ladder](https://app.cardladder.com)
    2. Open DevTools (F12)
    3. Go to Network tab
    4. Refresh the page
    5. Find any request to:
       `search-zzvl7ri3bq-uc.a.run.app/search`
    6. Click on that request
    7. In Headers tab, find 'authorization' header
    8. Copy the ENTIRE value
    
    ### Default Collection ID:
    `9Kr6jcPHdz77FNU9TVS4`
    
    You can find your own Collection ID in your collection URL.
    """)
