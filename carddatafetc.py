import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor

# ==================== SETTINGS ====================
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

def get_gspread_client():
    """Authenticates with strict cleaning of the private key"""
    try:
        s = st.secrets["gcp_service_account"]
        # Convert literal \n strings into actual newlines
        clean_key = s["private_key"].replace("\\n", "\n")

        creds_dict = {
            "type": "service_account",
            "project_id": s["project_id"],
            "private_key_id": s["private_key_id"],
            "private_key": clean_key,
            "client_email": s["client_email"],
            "client_id": s["client_id"],
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Auth Setup Failed: {e}")
        return None

def fetch_data(token, coll_id, limit):
    """Scrapes collection data and 3-sale averages"""
    headers = {'authorization': f"Bearer {token}" if "Bearer" not in token else token}
    
    # Get Collection
    res = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                       params={'index': 'collectioncards', 'page': 0, 'limit': limit, 
                               'filters': f'collectionId:{coll_id}|hasQuantityAvailable:true'})
    if res.status_code != 200:
        return None, f"Card Ladder Error: {res.status_code}"
    
    cards = res.json().get('hits', [])
    
    # Get Sales
    with ThreadPoolExecutor(max_workers=5) as exe:
        def get_s(c):
            r = requests.get('https://search-zzvl7ri3bq-uc.a.run.app/search', headers=headers, 
                             params={'index': 'salesarchive', 'query': c.get('label',''), 'limit': 3})
            p = [h.get('price') for h in r.json().get('hits', []) if h.get('price')] if r.status_code==200 else []
            return {'avg_last_3_sales': round(sum(p)/len(p), 2) if p else 0}
        
        results = list(exe.map(get_s, cards))
        for i, r in enumerate(results): cards[i].update(r)
        
    return cards, None

# ==================== INTERFACE ====================
st.set_page_config(page_title="Card Ladder Scraper", layout="wide")
st.title("📦 Card Ladder to Google Sheets")

with st.sidebar:
    token = st.text_area("Bearer Token")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    limit = st.number_input("Limit", value=20)

if st.button("🚀 Start Process"):
    if not token:
        st.error("Missing Token")
    else:
        with st.spinner("Processing..."):
            data, err = fetch_data(token, coll_id, limit)
            
            if err:
                st.error(err)
            elif data:
                df = pd.json_normalize(data)
                
                try:
                    client = get_gspread_client()
                    if client:
                        sh = client.open_by_key(SPREADSHEET_ID)
                        ws = sh.get_worksheet(0)
                        ws.clear()
                        
                        # Clean and Upload
                        df_clean = df.fillna('')
                        payload = [df_clean.columns.values.tolist()] + df_clean.values.tolist()
                        ws.update(payload)
                        
                        st.balloons()
                        st.success("✅ Success! Sheet Updated.")
                        st.dataframe(df_clean.head())
                except Exception as e:
                    st.error(f"Sheets Error: {e}")
