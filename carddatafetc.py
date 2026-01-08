import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor

# ==================== CONFIGURATION ====================
# You can change this ID if you move to a different spreadsheet
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

def get_gspread_client():
    """Authenticates using Streamlit Secrets"""
    creds_dict = {
        "type": "service_account",
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def fetch_card_ladder_data(token, coll_id, limit):
    """Scrapes collection and sales data"""
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    
    # 1. Fetch Collection
    res = requests.get(
        'https://search-zzvl7ri3bq-uc.a.run.app/search', 
        headers=headers, 
        params={
            'index': 'collectioncards', 
            'page': 0, 
            'limit': limit, 
            'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'
        }
    )
    
    if res.status_code != 200:
        st.error(f"Failed to fetch collection. Status: {res.status_code}")
        return []

    cards = res.json().get('hits', [])
    
    # 2. Fetch Last 3 Sales for each card (Multi-threaded for speed)
    with ThreadPoolExecutor(max_workers=5) as exe:
        def get_sales(card):
            label = card.get('label', '')
            r = requests.get(
                'https://search-zzvl7ri3bq-uc.a.run.app/search', 
                headers=headers, 
                params={'index': 'salesarchive', 'query': label, 'limit': 3}
            )
            if r.status_code == 200:
                hits = r.json().get('hits', [])
                prices = [h.get('price') for h in hits if h.get('price')]
                avg = round(sum(prices)/len(prices), 2) if prices else 0
                return {'avg_last_3_sales': avg}
            return {'avg_last_3_sales': 0}
        
        # Map the sales results back to the cards
        sales_results = list(exe.map(get_sales, cards))
        for i, result in enumerate(sales_results):
            cards[i].update(result)
            
    return cards

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Card Ladder to Sheets", layout="wide")
st.title("🎴 Card Ladder ⮕ Google Sheets")

with st.sidebar:
    st.header("Settings")
    token = st.text_area("Bearer Token")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    limit = st.number_input("Card Limit", min_value=1, value=10)
    st.info("The data will be sent to the spreadsheet ID defined in the code.")

if st.button("🚀 Scrape Data & Auto-Upload"):
    if not token:
        st.warning("Please provide a Bearer Token.")
    else:
        with st.spinner("Step 1: Scraping Card Ladder..."):
            data = fetch_card_ladder_data(token, coll_id, limit)
            
        if data:
            df = pd.json_normalize(data)
            st.success(f"Scraped {len(df)} cards successfully!")
            st.dataframe(df.head(10)) # Show preview
            
            with st.spinner("Step 2: Uploading to Google Sheets..."):
                try:
                    client = get_gspread_client()
                    sh = client.open_by_key(SPREADSHEET_ID)
                    ws = sh.get_worksheet(0) # Target the first tab
                    
                    # Clear and Update
                    ws.clear()
                    # Pre-process: handle NaN values and convert to list format
                    df_clean = df.fillna('')
                    upload_data = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
                    
                    ws.update(upload_data)
                    st.balloons()
                    st.success("✅ Data is now live in your Google Sheet!")
                except Exception as e:
                    st.error(f"Google Sheets Error: {e}")
