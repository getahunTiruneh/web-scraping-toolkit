import streamlit as st
import pandas as pd
import yfinance as yf
import plotly.graph_objects as go
import plotly.express as px
from io import BytesIO
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import time
from st_aggrid import AgGrid, GridOptionsBuilder

# Configuration
st.set_page_config(
    page_title="Professional Financial Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling - Updated with improved sidebar
st.markdown("""
    <style>
    /* Main content styling */
    .main {
        max-width: 1200px;
    }
    .reportview-container .main .block-container {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(135deg, #2c3e50, #4a6491);
        color: white;
        border-right: 1px solid #4a6491;
    }
    [data-testid="stSidebar"] .st-bb {
        background-color: transparent;
    }
    [data-testid="stSidebar"] .st-at {
        background-color: #4a6491;
    }
    [data-testid="stSidebar"] .stMarkdown h1,
    [data-testid="stSidebar"] .stMarkdown h2,
    [data-testid="stSidebar"] .stMarkdown h3,
    [data-testid="stSidebar"] .stMarkdown h4,
    [data-testid="stSidebar"] .stMarkdown h5,
    [data-testid="stSidebar"] .stMarkdown h6 {
        color: white;
    }
    [data-testid="stSidebar"] .stTextInput label,
    [data-testid="stSidebar"] .stTextArea label,
    [data-testid="stSidebar"] .stSelectbox label,
    [data-testid="stSidebar"] .stMultiselect label,
    [data-testid="stSidebar"] .stDateInput label,
    [data-testid="stSidebar"] .stRadio label,
    [data-testid="stSidebar"] .stCheckbox label {
        color: white !important;
        font-weight: 500;
    }
    [data-testid="stSidebar"] .stTextInput input,
    [data-testid="stSidebar"] .stTextArea textarea {
        background-color: rgba(255,255,255,0.9);
    }
    [data-testid="stSidebar"] .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(255,255,255,0.9);
    }
    [data-testid="stSidebar"] hr {
        border-color: rgba(255,255,255,0.2);
        margin: 1.5rem 0;
    }
    
    /* Button styling */
    .stDownloadButton button {
        background-color: #4CAF50;
        color: white;
        border: none;
        padding: 10px 20px;
        text-align: center;
        text-decoration: none;
        display: inline-block;
        font-size: 16px;
        margin: 4px 2px;
        cursor: pointer;
        border-radius: 5px;
        transition: all 0.3s;
    }
    .stDownloadButton button:hover {
        background-color: #45a049;
        transform: translateY(-1px);
        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background-color: #1f77b4;
    }
    
    /* Footer */
    footer {
        visibility: hidden;
    }
    
    /* Alerts */
    .stAlert {
        padding: 20px;
        border-radius: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# Function to fetch S&P 500 tickers with additional info
@st.cache_data(ttl=24*3600)
def fetch_sp500_tickers():
    try:
        url = "https://en.wikipedia.org/wiki/List_of_S%26P_500_companies"
        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table', {'id': 'constituents'})
        df = pd.read_html(str(table))[0]
        df = df[['Symbol', 'Security', 'GICS Sector', 'GICS Sub-Industry', 'Headquarters Location']]
        df.columns = ['Symbol', 'Company', 'Sector', 'Industry', 'Location']
        return df
    except Exception as e:
        st.error(f"Failed to fetch S&P 500 tickers: {e}")
        return pd.DataFrame(columns=['Symbol', 'Company', 'Sector', 'Industry', 'Location'])

# Function to fetch OHLC data with retry mechanism
def fetch_ohlc_data(ticker, start_date, end_date, retries=3):
    for attempt in range(retries):
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(start=start_date, end=end_date, auto_adjust=False)
            
            if hist.empty:
                return None
                
            hist.index = hist.index.tz_localize(None)
            
            # Get additional info
            info = stock.info
            additional_data = {
                'Company': info.get('longName', ticker),
                'Sector': info.get('sector', 'N/A'),
                'Industry': info.get('industry', 'N/A'),
                'MarketCap': info.get('marketCap', None),
                'PE': info.get('trailingPE', None),
                'Beta': info.get('beta', None),
                '52WeekHigh': info.get('fiftyTwoWeekHigh', None),
                '52WeekLow': info.get('fiftyTwoWeekLow', None)
            }
            
            return {
                'ohlc': hist[['Open', 'High', 'Low', 'Close', 'Volume']].reset_index(),
                'info': additional_data
            }
        except Exception as e:
            if attempt == retries - 1:
                st.error(f"Failed to fetch data for {ticker}: {e}")
                return None
            time.sleep(1)  # Wait before retrying

# Enhanced OHLC plot with volume
def plot_ohlc(data, ticker, company_name):
    fig = go.Figure()
    
    # Candlestick
    fig.add_trace(go.Candlestick(
        x=data['Date'],
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='OHLC',
        increasing_line_color='#2ECC71',
        decreasing_line_color='#E74C3C'
    ))
    
    # Volume as bar chart below
    fig.add_trace(go.Bar(
        x=data['Date'],
        y=data['Volume'],
        name='Volume',
        marker_color='#3498DB',
        yaxis='y2'
    ))
    
    fig.update_layout(
        title=f'{ticker} - {company_name}',
        xaxis_title='Date',
        yaxis_title='Price (USD)',
        xaxis_rangeslider_visible=False,
        hovermode='x unified',
        legend=dict(orientation='h', y=1.1),
        margin=dict(l=50, r=50, b=50, t=50, pad=4),
        yaxis2=dict(
            title='Volume',
            overlaying='y',
            side='right',
            showgrid=False
        ),
        template='plotly_white',
        height=600
    )
    
    return fig

# Performance comparison chart
def plot_performance_comparison(performance_df):
    fig = px.line(
        performance_df,
        x='Date',
        y='Normalized Close',
        color='Ticker',
        title='Normalized Price Performance Comparison',
        labels={'Normalized Close': 'Normalized Price (Base 100)'},
        height=500
    )
    
    fig.update_layout(
        hovermode='x unified',
        legend=dict(orientation='h', y=1.1),
        xaxis_title='Date',
        yaxis_title='Normalized Price',
        template='plotly_white'
    )
    
    return fig

# Correlation heatmap
def plot_correlation_heatmap(correlation_matrix):
    fig = go.Figure(data=go.Heatmap(
        z=correlation_matrix,
        x=correlation_matrix.columns,
        y=correlation_matrix.index,
        colorscale='RdBu',
        zmid=0,
        colorbar=dict(title='Correlation')
    ))
    
    fig.update_layout(
        title='Daily Returns Correlation Matrix',
        xaxis_title='Ticker',
        yaxis_title='Ticker',
        height=600,
        width=800
    )
    
    return fig

# Main App
def main():
    st.title("📊 Financial Data Scraping and Analysis Dashboard")
    st.markdown("""
        **A comprehensive tool for financial data analysis and visualization.**  
        Fetch historical market data, compare performance, and analyze correlations.
    """)
    
    # Sidebar for inputs
    with st.sidebar:
        st.header("Data Parameters")
        
        # Ticker Input Options
        input_option = st.radio(
            "Ticker Source",
            ("Manual Input", "S&P 500 Selection"),
            index=0
        )
        
        if input_option == "Manual Input":
            tickers_input = st.text_area(
                "Enter Stock Tickers (one per line)",
                placeholder="AAPL\nMSFT\nGOOGL\nAMZN",
                help="Enter one ticker per line. Example: AAPL for Apple"
            )
            tickers = [ticker.strip().upper() for ticker in tickers_input.splitlines() if ticker.strip()]
        else:
            sp500_df = fetch_sp500_tickers()
            if not sp500_df.empty:
                selected_sector = st.selectbox(
                    "Filter by Sector",
                    ["All Sectors"] + sorted(sp500_df['Sector'].unique().tolist()))
                
                if selected_sector != "All Sectors":
                    sp500_df = sp500_df[sp500_df['Sector'] == selected_sector]
                
                selected_tickers = st.multiselect(
                    "Select S&P 500 Companies",
                    sp500_df['Company'].unique(),
                    format_func=lambda x: f"{x} ({sp500_df[sp500_df['Company'] == x]['Symbol'].iloc[0]})"
                )
                
                tickers = sp500_df[sp500_df['Company'].isin(selected_tickers)]['Symbol'].tolist()
            else:
                tickers = []
        
        # Date Range
        col1, col2 = st.columns(2)
        with col1:
            start_date = st.date_input(
                "Start Date",
                datetime.now() - timedelta(days=365),
                max_value=datetime.now() - timedelta(days=1))
        with col2:
            end_date = st.date_input(
                "End Date",
                datetime.now(),
                max_value=datetime.now())
        
        # Additional Options
        st.markdown("---")
        st.markdown("**Analysis Options**")
        show_performance_comparison = st.checkbox("Show Performance Comparison", True)
        show_correlation = st.checkbox("Show Correlation Analysis", True)
        show_raw_data = st.checkbox("Show Raw Data", False)
    
    # Main Content
    if st.button("Fetch and Analyze Data", type="primary"):
        if not tickers:
            st.warning("Please enter at least one valid ticker.")
            return
            
        with st.spinner("Fetching data and generating analysis..."):
            progress_bar = st.progress(0)
            all_data = []
            all_info = []
            performance_data = []
            
            for i, ticker in enumerate(tickers):
                progress_bar.progress((i + 1) / len(tickers))
                
                result = fetch_ohlc_data(ticker, start_date, end_date)
                if result is not None:
                    ohlc_data = result['ohlc']
                    info_data = result['info']
                    
                    ohlc_data['Ticker'] = ticker
                    all_data.append(ohlc_data)
                    all_info.append(info_data)
                    
                    # Prepare performance comparison data
                    perf_df = ohlc_data[['Date', 'Close']].copy()
                    perf_df['Normalized Close'] = (perf_df['Close'] / perf_df['Close'].iloc[0]) * 100
                    perf_df['Ticker'] = ticker
                    performance_data.append(perf_df)
            
            if not all_data:
                st.error("No data could be fetched for the provided tickers.")
                return
                
            # Combine all data
            combined_data = pd.concat(all_data)
            combined_data = combined_data[['Ticker', 'Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            
            # Create info dataframe
            info_df = pd.DataFrame(all_info)
            info_df['Ticker'] = tickers[:len(info_df)]
            
            # Display summary info
            st.subheader("📌 Company Overview")
            AgGrid(info_df, height=300, fit_columns_on_grid_load=True)
            
            # Display charts for each ticker
            st.subheader("📈 OHLC Charts with Volume")
            for ticker, data in zip(tickers, all_data):
                with st.expander(f"{ticker} - {info_df[info_df['Ticker'] == ticker]['Company'].values[0]}"):
                    fig = plot_ohlc(data, ticker, info_df[info_df['Ticker'] == ticker]['Company'].values[0])
                    st.plotly_chart(fig, use_container_width=True)
            
            # Performance Comparison
            if show_performance_comparison and len(performance_data) > 1:
                st.subheader("📊 Performance Comparison")
                performance_df = pd.concat(performance_data)
                st.plotly_chart(plot_performance_comparison(performance_df), use_container_width=True)
            
            # Correlation Analysis
            if show_correlation and len(all_data) > 1:
                st.subheader("🔍 Correlation Analysis")
                
                # Create pivot table of closing prices
                closes_df = combined_data.pivot(index='Date', columns='Ticker', values='Close')
                
                # Calculate daily returns and correlation
                returns_df = closes_df.pct_change().dropna()
                correlation_matrix = returns_df.corr()
                
                col1, col2 = st.columns(2)
                with col1:
                    st.plotly_chart(plot_correlation_heatmap(correlation_matrix), use_container_width=True)
                with col2:
                    st.dataframe(correlation_matrix.style.background_gradient(cmap='coolwarm', vmin=-1, vmax=1))
            
            # Raw Data Display
            if show_raw_data:
                st.subheader("📋 Raw Data")
                st.dataframe(combined_data)
            
            # Export Options
            st.subheader("💾 Export Data")
            
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                combined_data.to_excel(writer, sheet_name='OHLC Data', index=False)
                info_df.to_excel(writer, sheet_name='Company Info', index=False)
                if len(performance_data) > 1:
                    performance_df.to_excel(writer, sheet_name='Performance', index=False)
                if len(all_data) > 1:
                    returns_df.to_excel(writer, sheet_name='Daily Returns', index=False)
                    correlation_matrix.to_excel(writer, sheet_name='Correlations')
            
            col1, col2 = st.columns(2)
            with col1:
                st.download_button(
                    label="Download Full Report (Excel)",
                    data=output.getvalue(),
                    file_name=f'financial_report_{datetime.now().strftime("%Y%m%d")}.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
            with col2:
                st.download_button(
                    label="Download OHLC Data (CSV)",
                    data=combined_data.to_csv(index=False).encode('utf-8'),
                    file_name='ohlc_data.csv',
                    mime='text/csv'
                )
    
    # Add some space at the bottom
    st.markdown("---")
    st.markdown("""
        <div style="text-align: center; color: gray; font-size: small;">
            <p>Created with Python, Streamlit, and yfinance</p>
            <p>Data provided by Yahoo Finance</p>
                <p>Developed by Getahun Tiruneh</p>
        </div>
    """, unsafe_allow_html=True)

if __name__ == "__main__":
    main()