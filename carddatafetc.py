import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import base64
import json
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Card Ladder Analytics",
    page_icon="📊",
    layout="wide"
)

# Session state for data
if 'df' not in st.session_state:
    st.session_state.df = None

# Title
st.title("📊 Card Ladder Collection Analytics")

# Sidebar for file upload
with st.sidebar:
    st.header("📁 Upload Data")
    
    uploaded_file = st.file_uploader(
        "Upload your JSON or CSV file",
        type=['json', 'csv']
    )
    
    if uploaded_file:
        try:
            if uploaded_file.name.endswith('.json'):
                data = json.load(uploaded_file)
                if 'cards' in data:
                    cards = data['cards']
                else:
                    cards = data
                
                # Convert to DataFrame
                flat_data = []
                for card in cards:
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
                
                st.session_state.df = pd.DataFrame(flat_data)
                
            else:  # CSV
                st.session_state.df = pd.read_csv(uploaded_file)
            
            st.success(f"✅ Loaded {len(st.session_state.df)} cards")
            
        except Exception as e:
            st.error(f"Error loading file: {e}")
    
    if st.session_state.df is not None:
        st.divider()
        st.metric("Total Cards", len(st.session_state.df))
        if 'value' in st.session_state.df.columns:
            total_value = st.session_state.df['value'].astype(float).sum()
            st.metric("Total Value", f"${total_value:,.2f}")

# Main content tabs
if st.session_state.df is not None:
    tab1, tab2, tab3 = st.tabs(["📊 Analytics", "💾 Export Data", "⚙️ Settings"])
    
    df = st.session_state.df
    
    with tab1:  # Analytics
        st.header("Analytics Dashboard")
        
        # Quick stats
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Cards", len(df))
        with col2:
            if 'value' in df.columns:
                total_value = df['value'].astype(float).sum()
                st.metric("Total Value", f"${total_value:,.2f}")
        with col3:
            if 'year' in df.columns:
                st.metric("Avg Year", f"{df['year'].astype(float).mean():.0f}")
        with col4:
            if 'grade' in df.columns:
                st.metric("Unique Grades", df['grade'].nunique())
        
        st.divider()
        
        # Visualizations
        col_left, col_right = st.columns(2)
        
        with col_left:
            # Grade Distribution
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
                st.plotly_chart(fig_grade, use_container_width=True)
            
            # Year Distribution
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
                st.plotly_chart(fig_year, use_container_width=True)
        
        with col_right:
            # Value Distribution
            if 'value' in df.columns:
                df['value'] = pd.to_numeric(df['value'], errors='coerce')
                fig_value = px.histogram(
                    df,
                    x='value',
                    title='Value Distribution',
                    nbins=30,
                    color_discrete_sequence=['#1E88E5']
                )
                fig_value.update_layout(xaxis_title="Value ($)", yaxis_title="Count")
                st.plotly_chart(fig_value, use_container_width=True)
            
            # Top Players
            if 'player' in df.columns:
                player_counts = df['player'].value_counts().head(10).reset_index()
                player_counts.columns = ['Player', 'Count']
                
                fig_players = px.pie(
                    player_counts,
                    values='Count',
                    names='Player',
                    title='Top 10 Players'
                )
                st.plotly_chart(fig_players, use_container_width=True)
        
        # Data Table
        st.divider()
        st.header("Data Preview")
        st.dataframe(df.head(100), use_container_width=True)
    
    with tab2:  # Export Data
        st.header("Export Options")
        
        col1, col2, col3 = st.columns(3)
        
        # CSV Export
        with col1:
            st.subheader("CSV Format")
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"cardladder_export_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
        
        # Excel Export
        with col2:
            st.subheader("Excel Format")
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, index=False, sheet_name='Cards')
            excel_data = output.getvalue()
            
            st.download_button(
                label="📊 Download Excel",
                data=excel_data,
                file_name=f"cardladder_export_{datetime.now().strftime('%Y%m%d')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
        
        # JSON Export
        with col3:
            st.subheader("JSON Format")
            json_str = df.to_json(orient='records', indent=2)
            st.download_button(
                label="📄 Download JSON",
                data=json_str,
                file_name=f"cardladder_export_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json"
            )
        
        st.divider()
        
        # Custom Export
        st.header("Custom Export")
        
        all_columns = list(df.columns)
        selected_columns = st.multiselect(
            "Select columns to export",
            options=all_columns,
            default=all_columns
        )
        
        if selected_columns:
            df_custom = df[selected_columns]
            st.dataframe(df_custom.head(10), use_container_width=True)
            
            # Custom CSV
            custom_csv = df_custom.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📥 Download Custom CSV",
                data=custom_csv,
                file_name=f"cardladder_custom_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv"
            )
    
    with tab3:  # Settings
        st.header("Settings")
        
        # Display Settings
        st.subheader("Display Settings")
        
        col1, col2 = st.columns(2)
        
        with col1:
            theme = st.selectbox(
                "Chart Theme",
                options=['plotly', 'plotly_white', 'plotly_dark', 'seaborn', 'ggplot2']
            )
            
            preview_rows = st.slider(
                "Preview Rows",
                min_value=10,
                max_value=200,
                value=50
            )
        
        with col2:
            default_export = st.selectbox(
                "Default Export Format",
                options=['CSV', 'Excel', 'JSON']
            )
            
            auto_refresh = st.checkbox(
                "Auto-refresh charts",
                value=True
            )
        
        # Data Settings
        st.subheader("Data Settings")
        
        if st.button("Clear All Data"):
            st.session_state.df = None
            st.rerun()
        
        if st.button("Load Sample Data"):
            # Create sample data
            sample_data = {
                'player': ['Mike Trout', 'Mike Trout', 'Shohei Ohtani', 'Aaron Judge', 'Shohei Ohtani'],
                'year': [2011, 2012, 2018, 2017, 2019],
                'grade': ['PSA 10', 'BGS 9.5', 'PSA 9', 'SGC 10', 'RAW'],
                'value': [1200.50, 850.00, 2500.00, 1800.00, 950.00],
                'setName': ['Topps Update', 'Topps Chrome', 'Bowman Chrome', 'Topps Update', 'Topps Chrome']
            }
            st.session_state.df = pd.DataFrame(sample_data)
            st.rerun()

else:
    # Welcome screen when no data is loaded
    st.info("👈 Upload your Card Ladder data file in the sidebar to begin")
    
    # Show sample of what the app can do
    with st.expander("📋 What this app can do"):
        st.write("""
        ### 📊 Analytics Tab:
        - Grade distribution charts
        - Year distribution analysis  
        - Value distribution histograms
        - Top players visualization
        - Interactive data table
        
        ### 💾 Export Tab:
        - Export to CSV, Excel, or JSON
        - Custom column selection
        - Direct download buttons
        
        ### ⚙️ Settings Tab:
        - Customize chart themes
        - Adjust display settings
        - Clear or load sample data
        """)
    
    # Quick start guide
    with st.expander("🚀 Quick Start"):
        st.write("""
        1. Export your Card Ladder collection as JSON or CSV
        2. Upload it in the sidebar
        3. Explore the analytics dashboard
        4. Export in your preferred format
        """)

# Footer
st.divider()
st.caption("Card Ladder Analytics Tool v1.0 | Upload your collection data to get started")
