import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor

# ==================== AUTH CONFIG ====================
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

def get_gspread_client():
    # This pulls safely from the Streamlit Secrets you set in the dashboard
    creds_dict = {
        "type": "service_account",
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

# ==================== DATA FUNCTIONS ====================
def get_data(token, coll_id, test_limit):
    headers = {'authorization': token if "Bearer" in token else f"Bearer {token}"}
    # Phase 1: Fetch
    res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', 
                       headers=headers, 
                       params={'index': 'collectioncards', 'page': 0, 'limit': test_limit, 
                               'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'})
    if res.status_code != 200: return []
    cards = res.json().get('hits', [])
    
    # Phase 2: Sales
    with ThreadPoolExecutor(max_workers=3) as exe:
        def fetch_s(c):
            r = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                             params={'index': 'salesarchive', 'query': c.get('label', ''), 'page': 0, 'limit': 3})
            if r.status_code == 200:
                h = r.json().get('hits', [])
                p = [x.get('price') for x in h if x.get('price')]
                return {'avg_last_3_sales': round(sum(p)/len(p), 2) if p else None}
            return {}
        results = list(exe.map(fetch_s, cards))
        for i, r in enumerate(results): cards[i].update(r)
    return cards

# ==================== UI ====================
st.title("Card Ladder ⮕ Google Sheets")

token = st.sidebar.text_area("Bearer Token:")
coll_id = st.sidebar.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
test_limit = st.sidebar.number_input("Card Limit", value=5)

if st.button("🚀 Run Scraper"):
    data = get_data(token, coll_id, test_limit)
    if data:
        st.session_state.df = pd.json_normalize(data)
        st.success(f"Fetched {len(data)} cards!")

if 'df' in st.session_state:
    st.dataframe(st.session_state.df.head())
    
    if st.button("📤 Upload to Google Sheets"):
        try:
            client = get_gspread_client()
            sh = client.open_by_key(SPREADSHEET_ID)
            ws = sh.get_worksheet(0) # Updates the first tab
            ws.clear()
            
            df_clean = st.session_state.df.fillna('')
            ws.update([df_clean.columns.values.tolist()] + df_clean.values.tolist())
            st.success("Successfully updated Google Sheet!")
        except Exception as e:
            st.error(f"Upload failed: {e}")
