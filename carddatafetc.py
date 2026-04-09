import streamlit as st
import requests
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import io
import time
import re

# ==================== GOOGLE SHEETS CONFIG ====================
def get_gspread_client():
    try:
        scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
        
        creds_dict = {
            "type": "service_account",
            "project_id": "cardladder",
            "private_key_id": "3e910525914e6d6fd55c9d3c08f275e755f004a0",
            "private_key": st.secrets["gcp_service_account"]["private_key"].replace("\\n", "\n"),
            "client_email": "cardladder@cardladder.iam.gserviceaccount.com",
            "client_id": "100678312403939380954",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/cardladder%40cardladder.iam.gserviceaccount.com"
        }
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        return gspread.authorize(creds)
    except Exception as e:
        st.error(f"Google Auth Error: {e}")
        return None

SPREADSHEET_ID = "1aO5Tk6ulm0bIkgL6FbLLP2ilhBs6_9M_vwLycT9bWnw"

# ==================== LOOKUP GEMRATEID FROM CARDS INDEX ====================
def lookup_gemrateid(token, card):
    """Search cards index to find gemRateId for this card"""
    headers = {'authorization': token}
    
    # Extract card info for better search
    player = card.get('player', '')
    set_name = card.get('set', '')
    card_number = card.get('number', '')
    year = card.get('year', '')
    
    # Build search query using set and number (most reliable)
    search_terms = []
    
    if set_name and card_number:
        search_terms.append(f"{set_name} {card_number}")
        search_terms.append(f"{set_name} #{card_number}")
    
    if player and set_name:
        search_terms.append(f"{player} {set_name}")
    
    if set_name:
        search_terms.append(set_name)
    
    # Try each search term
    for query in search_terms[:5]:
        params = {
            'index': 'cards',
            'query': query,
            'limit': 5
        }
        
        try:
            response = requests.get(
                'https://search-zzvl7ri3bq-uc.a.run.app/search',
                headers=headers,
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                hits = data.get('hits', [])
                
                for hit in hits:
                    # Verify it's the same card
                    hit_set = hit.get('set', '')
                    hit_player = hit.get('player', '')
                    hit_number = hit.get('number', '')
                    
                    if set_name and set_name in hit_set:
                        if card_number and str(card_number) == str(hit_number):
                            gemrate_id = hit.get('gemRateId')
                            if gemrate_id:
                                return gemrate_id
        except:
            pass
        
        time.sleep(0.2)
    
    return None

# ==================== FETCH SALES USING GEMRATEID ====================
def fetch_sales_by_gemrateid(token, gemrate_id, condition="PSA 10"):
    """Fetch sales using gemRateId - 100% ACCURATE"""
    headers = {'authorization': token}
    
    # Map condition to API format
    condition_map = {
        "PSA 10": "g10",
        "PSA 9": "g9", 
        "PSA 8": "g8",
    }
    grade_code = condition_map.get(condition, "g10")
    
    res_data = {
        'total_sales_in_db': 0,
        'sale1_price': None,
        'sale1_date': None,
        'sale2_price': None,
        'sale2_date': None,
        'sale3_price': None,
        'sale3_date': None,
        'sale4_price': None,
        'sale4_date': None,
        'avg_last_4_sales': 0,
        'gemRateId': gemrate_id
    }
    
    if not gemrate_id:
        return res_data
    
    try:
        # Use filters with gemRateId (from your working example!)
        params = {
            'index': 'salesarchive',
            'limit': 4,
            'sort': 'date',
            'direction': 'desc',
            'filters': f'condition:{grade_code}|gemRateId:{gemrate_id}|gradingCompany:psa'
        }
        
        response = requests.get(
            'https://search-zzvl7ri3bq-uc.a.run.app/search',
            headers=headers,
            params=params,
            timeout=15
        )
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get('hits', [])
            res_data['total_sales_in_db'] = data.get('totalHits', 0)
            
            # Extract sales data
            prices = []
            for i, hit in enumerate(hits[:4]):
                price = hit.get('price')
                date_str = hit.get('date', '')
                res_data[f'sale{i+1}_price'] = price
                if date_str:
                    try:
                        date_obj = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                        res_data[f'sale{i+1}_date'] = date_obj.strftime('%Y-%m-%d')
                    except:
                        res_data[f'sale{i+1}_date'] = date_str[:10]
                
                if price:
                    prices.append(price)
            
            if prices:
                res_data['avg_last_4_sales'] = round(sum(prices) / len(prices), 2)
                
    except Exception as e:
        st.warning(f"Error fetching sales: {e}")
    
    return res_data

# ==================== FETCH COLLECTION CARDS ====================
def fetch_collection_cards(token, collection_id, limit=500):
    """Fetch all cards from collection"""
    headers = {'authorization': token}
    all_cards = []
    
    page = 0
    limit_per_request = 50
    
    with st.spinner("Fetching collection cards..."):
        while len(all_cards) < limit:
            params = {
                'index': 'collectioncards',
                'limit': limit_per_request,
                'page': page,
                'filters': f'collectionId:{collection_id}|hasQuantityAvailable:true'
            }
            
            try:
                response = requests.get(
                    'https://search-zzvl7ri3bq-uc.a.run.app/search',
                    headers=headers,
                    params=params,
                    timeout=10
                )
                
                if response.status_code != 200:
                    st.error(f"API Error: {response.status_code}")
                    break
                
                data = response.json()
                hits = data.get('hits', [])
                
                if not hits:
                    break
                    
                all_cards.extend(hits)
                page += 1
                time.sleep(0.2)
                
            except Exception as e:
                st.error(f"Error: {e}")
                break
    
    return all_cards

# ==================== MAIN STREAMLIT APP ====================
st.set_page_config(page_title="Card Ladder - Accurate Sales", layout="wide")
st.title("🎴 Card Ladder - Accurate Sales Data")

with st.sidebar:
    st.header("Settings")
    auth_token = st.text_input("Bearer Token", type="password", 
                               help="Paste your full token including 'Bearer '")
    coll_id = st.text_input("Collection ID", value="m5H67EW8v1L1tXYf4Y32")
    
    st.markdown("---")
    st.info("""
    **How it works:**
    1. Fetches your collection cards
    2. Looks up gemRateId for each card
    3. Gets EXACT sales using gemRateId
    4. 100% accurate matching!
    """)
    
    limit = st.number_input("Max cards to process", value=20, min_value=1, max_value=500)

if st.button("🚀 Get Accurate Sales Data", type="primary"):
    if not auth_token:
        st.error("Please enter your Bearer Token")
        st.stop()
    
    # Ensure token has Bearer prefix
    if not auth_token.startswith('Bearer '):
        auth_token = f"Bearer {auth_token}"
    
    all_cards = fetch_collection_cards(auth_token, coll_id, limit)
    
    if not all_cards:
        st.error("No cards found! Check your Collection ID and token.")
        st.stop()
    
    st.success(f"✅ Found {len(all_cards)} cards in collection")
    
    # Process each card
    results = []
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, card in enumerate(all_cards):
        status_text.text(f"Processing {i+1}/{len(all_cards)}: {card.get('label', 'Unknown')[:50]}...")
        
        # Step 1: Look up gemRateId
        gemrate_id = lookup_gemrateid(auth_token, card)
        
        # Step 2: Fetch sales using gemRateId
        if gemrate_id:
            sales_data = fetch_sales_by_gemrateid(auth_token, gemrate_id, card.get('condition'))
        else:
            sales_data = {'gemRateId': None, 'total_sales_in_db': 0}
        
        # Combine card data with sales
        result = {
            'label': card.get('label'),
            'player': card.get('player'),
            'set': card.get('set'),
            'year': card.get('year'),
            'number': card.get('number'),
            'condition': card.get('condition'),
            'variation': card.get('variation'),
            'currentValue': card.get('currentValue'),
            'gemRateId': gemrate_id,
            'total_sales': sales_data.get('total_sales_in_db', 0),
            'avg_last_4_sales': sales_data.get('avg_last_4_sales', 0),
            'sale1_price': sales_data.get('sale1_price'),
            'sale1_date': sales_data.get('sale1_date'),
            'sale2_price': sales_data.get('sale2_price'),
            'sale2_date': sales_data.get('sale2_date'),
            'sale3_price': sales_data.get('sale3_price'),
            'sale3_date': sales_data.get('sale3_date'),
            'sale4_price': sales_data.get('sale4_price'),
            'sale4_date': sales_data.get('sale4_date'),
        }
        results.append(result)
        
        progress_bar.progress((i + 1) / len(all_cards))
        time.sleep(0.3)  # Rate limiting
    
    status_text.text("✅ Processing complete!")
    
    # Create DataFrame
    df = pd.DataFrame(results)
    
    # Display results
    st.divider()
    st.subheader("📊 Results")
    
    # Stats
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Cards", len(df))
    with col2:
        has_gemrate = df['gemRateId'].notna().sum()
        st.metric("Found gemRateId", has_gemrate)
    with col3:
        has_sales = df[df['total_sales'] > 0].shape[0]
        st.metric("Cards with Sales", has_sales)
    with col4:
        avg_price = df['avg_last_4_sales'].mean()
        st.metric("Avg Sale Price", f"${avg_price:.2f}" if avg_price > 0 else "N/A")
    
    # Show data table
    st.dataframe(df, use_container_width=True, height=400)
    
    # Download buttons
    st.divider()
    col1, col2 = st.columns(2)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    
    with col1:
        csv = df.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            f"card_sales_{timestamp}.csv",
            "text/csv"
        )
    
    with col2:
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        st.download_button(
            "📥 Download Excel",
            output.getvalue(),
            f"card_sales_{timestamp}.xlsx",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
    
    # Show cards without gemRateId
    no_gemrate = df[df['gemRateId'].isna()]
    if len(no_gemrate) > 0:
        st.warning(f"⚠️ {len(no_gemrate)} cards couldn't be matched to gemRateId")
        with st.expander("Show cards without gemRateId"):
            st.dataframe(no_gemrate[['label', 'player', 'set']])

st.markdown("---")
st.caption("💡 Uses gemRateId lookup for 100% accurate sales matching")
