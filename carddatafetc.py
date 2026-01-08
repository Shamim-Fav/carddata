import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor

# ==================== CONFIG ====================
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

def get_gspread_client():
    """Builds credentials from Streamlit Secrets"""
    creds_dict = {
        "type": "service_account",
        "project_id": st.secrets["gcp_service_account"]["project_id"],
        "private_key_id": st.secrets["gcp_service_account"]["private_key_id"],
        "private_key": st.secrets["gcp_service_account"]["private_key"],
        "client_email": st.secrets["gcp_service_account"]["client_email"],
        "client_id": st.secrets["gcp_service_account"]["client_id"],
        "token_uri": "https://oauth2.googleapis.com/token",
    }
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    return gspread.authorize(creds)

def fetch_data(token, coll_id, limit):
    """Scrapes collection and 3-sale averages"""
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    
    # 1. Get Collection
    res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                       params={'index': 'collectioncards', 'page': 0, 'limit': limit, 
                               'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'})
    if res.status_code != 200:
        return None, f"Error: {res.status_code}"
    
    cards = res.json().get('hits', [])
    
    # 2. Get Sales (Parallel)
    with ThreadPoolExecutor(max_workers=5) as exe:
        def get_s(c):
            r = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                             params={'index': 'salesarchive', 'query': c.get('label',''), 'limit': 3})
            p = [h.get('price') for h in r.json().get('hits', []) if h.get('price')] if r.status_code==200 else []
            return {'avg_last_3_sales': round(sum(p)/len(p), 2) if p else 0}
        
        results = list(exe.map(get_s, cards))
        for i, r in enumerate(results): cards[i].update(r)
        
    return cards, None

# ==================== UI ====================
st.set_page_config(page_title="Card Scraper", layout="wide")
st.title("🎴 Card Scraper to Google Sheets")

token = st.sidebar.text_area("Bearer Token")
coll_id = st.sidebar.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
limit = st.sidebar.number_input("Card Limit", value=20)

if st.button("🚀 Scrape & Auto-Upload"):
    if not token:
        st.error("Missing Bearer Token")
    else:
        with st.spinner("Processing..."):
            data, error = fetch_data(token, coll_id, limit)
            
            if error:
                st.error(error)
            elif data:
                df = pd.json_normalize(data)
                st.success(f"Scraped {len(df)} cards")
                
                # Upload to Sheets
                try:
                    client = get_gspread_client()
                    sh = client.open_by_key(SPREADSHEET_ID)
                    ws = sh.get_worksheet(0)
                    ws.clear()
                    
                    df_clean = df.fillna('')
                    upload_payload = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
                    ws.update(upload_payload)
                    
                    st.balloons()
                    st.success("✅ Successfully updated Google Sheets!")
                    st.dataframe(df.head())
                except Exception as e:
                    st.error(f"Google Upload Failed: {e}")
