import streamlit as st
import requests
import pandas as pd
import json
import time
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import base64
import re

# Page configuration
st.set_page_config(
    page_title="Card Ladder Collection Manager",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.5rem;
        color: #424242;
        margin-bottom: 1rem;
    }
    .success-box {
        background-color: #E8F5E9;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #4CAF50;
    }
    .error-box {
        background-color: #FFEBEE;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #F44336;
    }
    .warning-box {
        background-color: #FFF3E0;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #FF9800;
    }
    .info-box {
        background-color: #E3F2FD;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 5px solid #2196F3;
    }
    .stButton > button {
        width: 100%;
        background-color: #1E88E5;
        color: white;
    }
    .stButton > button:hover {
        background-color: #1565C0;
        color: white;
    }
    .metric-card {
        background-color: #F5F5F5;
        padding: 1rem;
        border-radius: 0.5rem;
        text-align: center;
        margin: 0.5rem;
    }
</style>
""", unsafe_allow_html=True)

class CardLadderAPI:
    def __init__(self, auth_token):
        self.session = requests.Session()
        self.headers = self._create_headers(auth_token)
        
    def _create_headers(self, auth_token):
        """Create headers with auth token"""
        return {
            'accept': 'application/json, text/plain, */*',
            'accept-encoding': 'gzip, deflate, br, zstd',
            'accept-language': 'en-US,en;q=0.9',
            'authority': 'search-zzvl7ri3bq-uc.a.run.app',
            'origin': 'https://app.cardladder.com',
            'referer': 'https://app.cardladder.com/',
            'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not-A.Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'cross-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
            'priority': 'u=1, i',
            'authorization': auth_token
        }
    
    def test_connection(self, collection_id="9Kr6jcPHdz77FNU9TVS4"):
        """Test API connection"""
        params = {
            'index': 'collectioncards',
            'query': '',
            'limit': 5,
            'filters': f'collectionId:{collection_id}|hasQuantityAvailable:true',
            'sort': 'dateAdded',
            'direction': 'desc',
            'page': 1
        }
        
        try:
            response = self.session.get(
                'https://search-zzvl7ri3bq-uc.a.run.app/search',
                headers=self.headers,
                params=params,
                timeout=10
            )
            return response
        except Exception as e:
            return None
    
    def fetch_collection(self, collection_id, query="", sort_by="dateAdded", sort_dir="desc", limit=20):
        """Fetch entire collection with pagination"""
        base_params = {
            'index': 'collectioncards',
            'query': query,
            'limit': limit,
            'filters': f'collectionId:{collection_id}|hasQuantityAvailable:true',
            'sort': sort_by,
            'direction': sort_dir
        }
        
        all_results = []
        page = 1
        has_more = True
        
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        while has_more:
            status_text.text(f"📄 Fetching page {page}...")
            progress_bar.progress((page-1) * 10)  # Simple progress indicator
            
            params = base_params.copy()
            params['page'] = page
            
            try:
                response = self.session.get(
                    'https://search-zzvl7ri3bq-uc.a.run.app/search',
                    headers=self.headers,
                    params=params,
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Find results in response
                    results = self._extract_results(data)
                    
                    if results:
                        all_results.extend(results)
                        st.session_state['last_fetch_count'] = len(all_results)
                        
                        if len(results) < base_params['limit']:
                            has_more = False
                        else:
                            page += 1
                            time.sleep(0.3)  # Rate limiting delay
                    else:
                        has_more = False
                        
                elif response.status_code in [401, 403]:
                    st.error(f"Access denied (Status: {response.status_code})")
                    break
                elif response.status_code == 429:
                    st.warning("Rate limited, waiting 5 seconds...")
                    time.sleep(5)
                    continue
                else:
                    st.error(f"Error {response.status_code}")
                    break
                    
            except Exception as e:
                st.error(f"Request failed: {e}")
                break
        
        progress_bar.progress(100)
        status_text.text(f"✅ Fetch complete! Found {len(all_results)} cards")
        time.sleep(0.5)
        progress_bar.empty()
        status_text.empty()
        
        return all_results
    
    def _extract_results(self, data):
        """Extract results from API response"""
        if 'results' in data:
            return data['results']
        elif 'cards' in data:
            return data['cards']
        elif 'items' in data:
            return data['items']
        elif 'data' in data:
            return data['data']
        elif isinstance(data, list):
            return data
        else:
            for key, value in data.items():
                if isinstance(value, list):
                    return value
        return []

def extract_card_data(cards):
    """Extract and flatten card data for DataFrame"""
    flat_cards = []
    
    for card in cards:
        flat_card = {}
        
        # Flatten nested dictionaries
        for key, value in card.items():
            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    flat_card[f"{key}_{subkey}"] = subvalue
            elif isinstance(value, list):
                flat_card[key] = '; '.join(map(str, value))
            else:
                flat_card[key] = value
        
        # Extract player from name if not present
        if 'player' not in flat_card and 'name' in flat_card:
            # Try to extract player from card name
            name = flat_card['name']
            # Remove set/year/grade info from name to get player
            player = re.sub(r'(\d{4}|PSA \d+|BGS \d+|SGC \d+|RAW).*', '', name).strip()
            flat_card['player'] = player
        
        flat_cards.append(flat_card)
    
    return flat_cards

def create_visualizations(df):
    """Create visualizations for the collection"""
    charts = {}
    
    # 1. Grade Distribution
    if 'grade' in df.columns:
        grade_counts = df['grade'].value_counts().reset_index()
        grade_counts.columns = ['Grade', 'Count']
        
        fig_grade = px.bar(
            grade_counts,
            x='Grade',
            y='Count',
            title='Grade Distribution',
            color='Count',
            color_continuous_scale='Blues'
        )
        charts['grade_dist'] = fig_grade
    
    # 2. Year Distribution
    if 'year' in df.columns:
        year_counts = df['year'].value_counts().reset_index()
        year_counts.columns = ['Year', 'Count']
        year_counts = year_counts.sort_values('Year')
        
        fig_year = px.line(
            year_counts,
            x='Year',
            y='Count',
            title='Cards by Year',
            markers=True
        )
        charts['year_dist'] = fig_year
    
    # 3. Value Distribution
    if 'value' in df.columns:
        df['value'] = pd.to_numeric(df['value'], errors='coerce')
        fig_value = px.histogram(
            df,
            x='value',
            title='Value Distribution',
            nbins=50,
            color_discrete_sequence=['#1E88E5']
        )
        fig_value.update_layout(xaxis_title="Value ($)", yaxis_title="Count")
        charts['value_dist'] = fig_value
    
    # 4. Top Players by Count
    if 'player' in df.columns:
        player_counts = df['player'].value_counts().head(10).reset_index()
        player_counts.columns = ['Player', 'Count']
        
        fig_players = px.pie(
            player_counts,
            values='Count',
            names='Player',
            title='Top 10 Players by Card Count'
        )
        charts['top_players'] = fig_players
    
    return charts

def get_download_link(df, file_format='csv'):
    """Generate download link for DataFrame"""
    if file_format == 'csv':
        csv = df.to_csv(index=False)
        b64 = base64.b64encode(csv.encode()).decode()
        return f'data:file/csv;base64,{b64}'
    elif file_format == 'excel':
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False, sheet_name='Cards')
        b64 = base64.b64encode(output.getvalue()).decode()
        return f'data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64}'
    elif file_format == 'json':
        json_str = df.to_json(orient='records', indent=2)
        b64 = base64.b64encode(json_str.encode()).decode()
        return f'data:application/json;base64,{b64}'

def main():
    # Initialize session state
    if 'auth_token' not in st.session_state:
        st.session_state.auth_token = None
    if 'api_client' not in st.session_state:
        st.session_state.api_client = None
    if 'cards_data' not in st.session_state:
        st.session_state.cards_data = None
    if 'df_cards' not in st.session_state:
        st.session_state.df_cards = None
    
    # Sidebar
    with st.sidebar:
        st.image("https://via.placeholder.com/300x80.png?text=Card+Ladder", use_container_width=True)
        
        st.markdown("### 🔐 Authentication")
        
        auth_token = st.text_area(
            "Bearer Token",
            value=st.session_state.auth_token or "",
            height=150,
            placeholder="Bearer eyJhbGciOiJSUzI1NiIsImtpZCI6ImEzOGVhNmEwNDA4YjBjYzVkYTE4OWRmYzg4ODgyZDBmMWI3ZmJmMGUiLCJ0eXAiOiJKV1QifQ...",
            help="Get this from Card Ladder DevTools (F12 → Network → Find authorization header)"
        )
        
        if st.button("Save Token", type="primary"):
            if auth_token and auth_token.startswith('Bearer '):
                st.session_state.auth_token = auth_token
                st.session_state.api_client = CardLadderAPI(auth_token)
                st.success("Token saved successfully!")
            else:
                st.error("Please enter a valid Bearer token starting with 'Bearer '")
        
        st.markdown("---")
        
        # Quick instructions
        with st.expander("📖 How to get your token"):
            st.markdown("""
            1. Login to [Card Ladder](https://app.cardladder.com)
            2. Open DevTools (F12)
            3. Go to Network tab
            4. Refresh page
            5. Find request to `search-zzvl7ri3bq-uc.a.run.app/search`
            6. Copy `authorization` header value
            """)
        
        if st.session_state.auth_token:
            st.markdown("---")
            if st.button("🗑️ Clear Token & Data"):
                for key in ['auth_token', 'api_client', 'cards_data', 'df_cards']:
                    if key in st.session_state:
                        del st.session_state[key]
                st.rerun()
    
    # Main content
    st.markdown('<h1 class="main-header">📊 Card Ladder Collection Manager</h1>', unsafe_allow_html=True)
    
    # Check authentication
    if not st.session_state.auth_token:
        st.markdown("""
        <div class="info-box">
        <h3>🔐 Authentication Required</h3>
        <p>Please enter your Card Ladder Bearer token in the sidebar to begin.</p>
        </div>
        """, unsafe_allow_html=True)
        
        # Show example response
        with st.expander("📋 Example API Response Structure"):
            st.json({
                "metadata": {
                    "total": 150,
                    "page": 1,
                    "limit": 20
                },
                "results": [
                    {
                        "id": "card_123",
                        "name": "Mike Trout 2011 Topps Update PSA 10",
                        "player": "Mike Trout",
                        "year": 2011,
                        "setName": "Topps Update",
                        "grade": "PSA 10",
                        "value": 1200.50,
                        "dateAdded": "2024-01-15"
                    }
                ]
            })
        return
    
    # Main tabs
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Fetch Collection", "📊 Analytics", "💾 Export Data", "⚙️ Settings"])
    
    with tab1:
        st.markdown('<h2 class="sub-header">Fetch Collection</h2>', unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            collection_id = st.text_input(
                "Collection ID",
                value="9Kr6jcPHdz77FNU9TVS4",
                help="Find this in your collection URL"
            )
        
        with col2:
            query = st.text_input(
                "Search Query (Optional)",
                placeholder="e.g., Mike Trout, PSA 10",
                help="Filter cards by name, player, or grade"
            )
        
        with col3:
            sort_options = st.selectbox(
                "Sort By",
                options=['dateAdded', 'name', 'player', 'year', 'grade', 'value'],
                index=0
            )
        
        col4, col5 = st.columns(2)
        
        with col4:
            sort_direction = st.radio(
                "Sort Direction",
                options=['desc', 'asc'],
                horizontal=True
            )
        
        with col5:
            limit_per_page = st.slider(
                "Cards per page",
                min_value=10,
                max_value=100,
                value=20,
                help="Higher values may cause rate limiting"
            )
        
        # Buttons
        col6, col7, col8 = st.columns(3)
        
        with col6:
            test_btn = st.button("🔍 Test Connection", use_container_width=True)
        
        with col7:
            fetch_btn = st.button("🚀 Fetch Collection", type="primary", use_container_width=True)
        
        with col8:
            if st.session_state.cards_data:
                clear_btn = st.button("🗑️ Clear Results", use_container_width=True)
        
        # Test connection
        if test_btn:
            with st.spinner("Testing connection..."):
                response = st.session_state.api_client.test_connection(collection_id)
                
                if response and response.status_code == 200:
                    st.success("✅ Connection successful!")
                    
                    try:
                        data = response.json()
                        # Find results
                        results = st.session_state.api_client._extract_results(data)
                        
                        if results:
                            st.info(f"Test found {len(results)} cards")
                            # Show sample
                            with st.expander("📋 Sample Card"):
                                st.json(results[0])
                        else:
                            st.warning("Connection successful but no cards found")
                            
                    except:
                        st.info("Connection test passed")
                elif response:
                    st.error(f"❌ Connection failed: {response.status_code}")
                else:
                    st.error("❌ Connection failed - Check token and network")
        
        # Fetch collection
        if fetch_btn:
            if not collection_id:
                st.error("Please enter a Collection ID")
            else:
                with st.spinner("Fetching collection data..."):
                    cards = st.session_state.api_client.fetch_collection(
                        collection_id=collection_id,
                        query=query,
                        sort_by=sort_options,
                        sort_dir=sort_direction,
                        limit=limit_per_page
                    )
                    
                    if cards:
                        st.session_state.cards_data = cards
                        flat_cards = extract_card_data(cards)
                        st.session_state.df_cards = pd.DataFrame(flat_cards)
                        st.success(f"✅ Successfully fetched {len(cards)} cards!")
                    else:
                        st.error("No cards found. Check your collection ID and permissions.")
        
        # Clear results
        if 'clear_btn' in locals() and clear_btn:
            st.session_state.cards_data = None
            st.session_state.df_cards = None
            st.rerun()
    
    # Analytics Tab
    with tab2:
        st.markdown('<h2 class="sub-header">Collection Analytics</h2>', unsafe_allow_html=True)
        
        if st.session_state.df_cards is not None:
            df = st.session_state.df_cards
            
            # Display metrics
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                total_cards = len(df)
                st.metric("Total Cards", f"{total_cards:,}")
            
            with col2:
                if 'value' in df.columns:
                    df['value'] = pd.to_numeric(df['value'], errors='coerce')
                    total_value = df['value'].sum()
                    st.metric("Total Value", f"${total_value:,.2f}")
                else:
                    st.metric("Total Value", "N/A")
            
            with col3:
                if 'year' in df.columns:
                    unique_years = df['year'].nunique()
                    st.metric("Unique Years", unique_years)
                else:
                    st.metric("Unique Years", "N/A")
            
            with col4:
                if 'grade' in df.columns:
                    unique_grades = df['grade'].nunique()
                    st.metric("Unique Grades", unique_grades)
                else:
                    st.metric("Unique Grades", "N/A")
            
            st.markdown("---")
            
            # Visualizations
            charts = create_visualizations(df)
            
            if charts:
                cols = st.columns(2)
                for idx, (chart_name, fig) in enumerate(charts.items()):
                    with cols[idx % 2]:
                        st.plotly_chart(fig, use_container_width=True)
            
            # Data Preview
            st.markdown("### 📋 Data Preview")
            st.dataframe(
                df.head(100),
                use_container_width=True,
                hide_index=True
            )
            
            # Show all columns in expander
            with st.expander("📊 Column Statistics"):
                st.write("**Available Columns:**", list(df.columns))
                st.write("**Data Types:**")
                st.write(df.dtypes)
                
                if not df.empty:
                    st.write("**Summary Statistics:**")
                    st.write(df.describe(include='all'))
        else:
            st.info("No collection data available. Fetch a collection first.")
    
    # Export Tab
    with tab3:
        st.markdown('<h2 class="sub-header">Export Data</h2>', unsafe_allow_html=True)
        
        if st.session_state.df_cards is not None:
            df = st.session_state.df_cards
            
            st.markdown("### Download Options")
            
            col1, col2, col3 = st.columns(3)
            
            with col1:
                st.markdown("#### CSV Format")
                csv_link = get_download_link(df, 'csv')
                st.markdown(
                    f'<a href="{csv_link}" download="cardladder_collection.csv" class="stButton">'
                    '<button style="width: 100%;">📥 Download CSV</button>'
                    '</a>',
                    unsafe_allow_html=True
                )
            
            with col2:
                st.markdown("#### Excel Format")
                excel_link = get_download_link(df, 'excel')
                st.markdown(
                    f'<a href="{excel_link}" download="cardladder_collection.xlsx" class="stButton">'
                    '<button style="width: 100%;">📊 Download Excel</button>'
                    '</a>',
                    unsafe_allow_html=True
                )
            
            with col3:
                st.markdown("#### JSON Format")
                json_link = get_download_link(df, 'json')
                st.markdown(
                    f'<a href="{json_link}" download="cardladder_collection.json" class="stButton">'
                    '<button style="width: 100%;">📄 Download JSON</button>'
                    '</a>',
                    unsafe_allow_html=True
                )
            
            st.markdown("---")
            
            # Column Selection for Export
            st.markdown("### 🎯 Customize Export")
            all_columns = list(df.columns)
            selected_columns = st.multiselect(
                "Select columns to export",
                options=all_columns,
                default=all_columns
            )
            
            if selected_columns:
                df_selected = df[selected_columns]
                
                # Preview custom export
                st.markdown("#### Preview")
                st.dataframe(df_selected.head(10), use_container_width=True)
                
                # Download customized data
                st.markdown("#### Download Custom Selection")
                
                col4, col5, col6 = st.columns(3)
                
                with col4:
                    custom_csv_link = get_download_link(df_selected, 'csv')
                    st.markdown(
                        f'<a href="{custom_csv_link}" download="cardladder_custom.csv">'
                        '<button style="width: 100%;">📥 Custom CSV</button>'
                        '</a>',
                        unsafe_allow_html=True
                    )
                
                with col5:
                    custom_excel_link = get_download_link(df_selected, 'excel')
                    st.markdown(
                        f'<a href="{custom_excel_link}" download="cardladder_custom.xlsx">'
                        '<button style="width: 100%;">📊 Custom Excel</button>'
                        '</a>',
                        unsafe_allow_html=True
                    )
                
                with col6:
                    custom_json_link = get_download_link(df_selected, 'json')
                    st.markdown(
                        f'<a href="{custom_json_link}" download="cardladder_custom.json">'
                        '<button style="width: 100%;">📄 Custom JSON</button>'
                        '</a>',
                        unsafe_allow_html=True
                    )
        else:
            st.info("No data to export. Fetch a collection first.")
    
    # Settings Tab
    with tab4:
        st.markdown('<h2 class="sub-header">Settings</h2>', unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("### API Settings")
            
            rate_limit_delay = st.slider(
                "Rate limit delay (seconds)",
                min_value=0.1,
                max_value=2.0,
                value=0.3,
                step=0.1,
                help="Delay between API requests to avoid rate limiting"
            )
            
            timeout = st.slider(
                "Request timeout (seconds)",
                min_value=10,
                max_value=60,
                value=30,
                help="Timeout for API requests"
            )
            
            st.markdown("---")
            st.markdown("### Data Processing")
            
            auto_flatten = st.checkbox(
                "Auto-flatten nested data",
                value=True,
                help="Automatically flatten nested JSON structures"
            )
            
            extract_players = st.checkbox(
                "Extract player names from card titles",
                value=True,
                help="Try to extract player names when not provided"
            )
        
        with col2:
            st.markdown("### Display Settings")
            
            preview_rows = st.slider(
                "Preview rows in table",
                min_value=10,
                max_value=200,
                value=50,
                help="Number of rows to show in data preview"
            )
            
            chart_theme = st.selectbox(
                "Chart theme",
                options=['plotly', 'plotly_white', 'plotly_dark', 'ggplot2', 'seaborn'],
                index=0
            )
            
            st.markdown("---")
            st.markdown("### Export Settings")
            
            default_export_format = st.selectbox(
                "Default export format",
                options=['CSV', 'Excel', 'JSON'],
                index=0
            )
            
            include_metadata = st.checkbox(
                "Include metadata in exports",
                value=True,
                help="Include collection metadata in exported files"
            )
        
        # Save settings
        if st.button("💾 Save Settings", type="primary"):
            st.success("Settings saved! (Note: In a real app, these would be persisted)")
        
        st.markdown("---")
        st.markdown("### 🛠️ Diagnostics")
        
        if st.button("Run Diagnostics"):
            with st.spinner("Running diagnostics..."):
                diagnostic_info = {
                    "Authentication": "✅ Valid" if st.session_state.auth_token else "❌ Missing",
                    "API Client": "✅ Initialized" if st.session_state.api_client else "❌ Not initialized",
                    "Data Loaded": f"✅ {len(st.session_state.cards_data) if st.session_state.cards_data else 0} cards" 
                    if st.session_state.cards_data else "❌ No data",
                    "DataFrame": "✅ Created" if st.session_state.df_cards is not None else "❌ Not created",
                    "Columns": list(st.session_state.df_cards.columns) if st.session_state.df_cards is not None else []
                }
                
                st.json(diagnostic_info)

if __name__ == "__main__":
    main()
