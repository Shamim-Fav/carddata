import streamlit as st
import requests
import pandas as pd
import json
import time
from datetime import datetime
from io import BytesIO
import base64

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
st.title("📊 Card Ladder Collection Fetcher")

# Main container - ONE TAB
tab1 = st.container()

with tab1:
    # Split into two columns
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
        
        if st.button("Save Token"):
            if auth_token and auth_token.startswith('Bearer '):
                st.session_state.auth_token = auth_token
                st.success("Token saved!")
            else:
                st.error("Token must start with 'Bearer '")
        
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
        col_fetch1, col_fetch2 = st.columns(2)
        with col_fetch1:
            if st.button("🔍 Test Connection", use_container_width=True):
                if st.session_state.auth_token:
                    with st.spinner("Testing..."):
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
                                st.error(f"Connection failed: {response.status_code}")
                        except:
                            st.error("Connection failed")
                else:
                    st.error("Please save token first")
        
        with col_fetch2:
            fetch_button = st.button("🚀 Fetch Collection", type="primary", use_container_width=True)
    
    with col2:
        # Results and download section
        st.subheader("📊 Results & Download")
        
        if fetch_button and st.session_state.auth_token:
            # Fetch collection
            with st.spinner("Fetching collection..."):
                headers = {
                    'authorization': st.session_state.auth_token,
                    'accept': 'application/json'
                }
                
                all_results = []
                page = 1
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                while True:
                    status_text.text(f"Fetching page {page}...")
                    
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
                                progress = min(100, (page * 10))
                                progress_bar.progress(progress)
                                
                                if len(results) < limit:
                                    break
                                page += 1
                                time.sleep(0.3)
                            else:
                                break
                        else:
                            st.error(f"Error: {response.status_code}")
                            break
                            
                    except Exception as e:
                        st.error(f"Error: {e}")
                        break
                
                progress_bar.progress(100)
                status_text.text(f"✅ Fetched {len(all_results)} cards!")
                time.sleep(0.5)
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
        
        # Show results if available
        if st.session_state.df_cards is not None:
            df = st.session_state.df_cards
            
            # Stats
            st.metric("Total Cards", len(df))
            
            if 'value' in df.columns:
                try:
                    df['value'] = pd.to_numeric(df['value'], errors='coerce')
                    total_value = df['value'].sum()
                    st.metric("Total Value", f"${total_value:,.2f}")
                except:
                    pass
            
            # Download section
            st.divider()
            st.subheader("💾 Download Options")
            
            # Create timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # CSV Download
            csv_data = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv_data,
                file_name=f"cardladder_{timestamp}.csv",
                mime="text/csv",
                use_container_width=True
            )
            
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
            
            # JSON Download
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
        if st.session_state.df_cards is not None:
            if st.button("🗑️ Clear Results", type="secondary"):
                st.session_state.cards_data = None
                st.session_state.df_cards = None
                st.rerun()

# Instructions in sidebar
with st.sidebar:
    st.header("📋 How to Get Token")
    st.markdown("""
    1. Login to [Card Ladder](https://app.cardladder.com)
    2. Open DevTools (F12)
    3. Go to Network tab
    4. Refresh page
    5. Find request to:
       `search-zzvl7ri3bq-uc.a.run.app/search`
    6. Copy `authorization` header
    7. Paste in Bearer Token field
    """)
