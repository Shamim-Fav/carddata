import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from concurrent.futures import ThreadPoolExecutor

# ==================== CONFIGURATION ====================
# The ID of your spreadsheet from the URL
SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

def get_gspread_client():
    """Builds credentials from Streamlit Secrets with Auto-Cleaning"""
    try:
        # Pull from Secrets
        secret_data = st.secrets["gcp_service_account"]
        
        # Clean the private key to handle newline/Base64 issues
        raw_key = secret_data["private_key"]
        clean_key = raw_key.replace("\\n", "\n").strip()

        creds_dict = {
            "type": "service_account",
            "project_id": secret_data["project_id"],
            "private_key_id": secret_data["private_key_id"],
            "private_key": clean_key,
            "client_email": secret_data["client_email"],
            "client_id": secret_data["client_id"],
            "token_uri": "https://oauth2.googleapis.com/token",
        }
        
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Authentication Setup Failed: {e}")
        return None

def fetch_card_ladder_data(token, coll_id, limit):
    """Scrapes collection and 3-sale averages"""
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
        return None, f"Card Ladder API Error: {res.status_code}"

    cards = res.json().get('hits', [])
    
    # 2. Fetch Sales (Multi-threaded)
    with ThreadPoolExecutor(max_workers=5) as exe:
        def get_sales(card):
            label = card.get('label', '')
            r = requests.get(
                'https://search-zzvl7ri3bq-uc.a.run.app/search', 
                headers=headers, 
                params={'index': 'salesarchive', 'query': label, 'limit': 3}
            )
            prices = []
            if r.status_code == 200:
                hits = r.json().get('hits', [])
                prices = [h.get('price') for h in hits if h.get('price')]
            
            avg = round(sum(prices)/len(prices), 2) if prices else 0
            return {'avg_last_3_sales': avg}
        
        sales_results = list(exe.map(get_sales, cards))
        for i, result in enumerate(sales_results):
            cards[i].update(result)
            
    return cards, None

# ==================== STREAMLIT UI ====================
st.set_page_config(page_title="Card Ladder ⮕ Sheets", layout="wide")
st.title("🚀 Card Ladder to Google Sheets")

with st.sidebar:
    st.header("Credentials")
    token = st.text_area("Bearer Token")
    coll_id = st.text_input("Collection ID", value="zKC3o1sfYEcBGNaTPDRn")
    limit = st.number_input("Card Limit", min_value=1, value=25)

if st.button("Start Scrape & Upload"):
    if not token:
        st.warning("Please enter your Bearer Token.")
    else:
        # Step 1: Scrape
        with st.spinner("Scraping data..."):
            data, err = fetch_card_ladder_data(token, coll_id, limit)
        
        if err:
            st.error(err)
        elif data:
            df = pd.json_normalize(data)
            st.success(f"Successfully scraped {len(df)} cards!")
            
            # Step 2: Upload
            with st.spinner("Uploading to Google Sheets..."):
                client = get_gspread_client()
                if client:
                    try:
                        sh = client.open_by_key(SPREADSHEET_ID)
                        ws = sh.get_worksheet(0)
                        
                        # Clear old data
                        ws.clear()
                        
                        # Prepare for upload
                        df_upload = df.fillna('')
                        final_data = [df_upload.columns.values.tolist()] + df_upload.values.tolist()
                        
                        ws.update(final_data)
                        st.balloons()
                        st.success("✅ Upload Complete! Check your Google Sheet.")
                        st.dataframe(df_upload.head(10))
                    except Exception as e:
                        st.error(f"Google Sheets Upload Failed: {e}")
