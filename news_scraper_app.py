# news_scraper_app.py

import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime

# Function to scrape headlines from a given URL
def scrape_news(url):
    try:
        response = requests.get(url)
        soup = BeautifulSoup(response.content, 'html.parser')

        # Attempt to extract headlines (can adjust based on site structure)
        headlines = [h.get_text(strip=True) for h in soup.find_all(['h1', 'h2', 'h3']) if h.get_text(strip=True)]
        timestamps = [datetime.now().strftime("%Y-%m-%d %H:%M:%S")] * len(headlines)
        source = [url] * len(headlines)

        return pd.DataFrame({
            'Headline': headlines,
            'Source': source,
            'Scraped Time': timestamps
        })
    except Exception as e:
        st.error(f"Failed to scrape {url}: {e}")
        return pd.DataFrame()

# Streamlit App
st.set_page_config(page_title="News Scraper Dashboard", layout="wide")
st.title("📰 News Data Scraper & Export Tool")

# Input: Multiple URLs
st.markdown("### Enter News Website URLs (one per line)")
urls_input = st.text_area("News URLs", placeholder="https://example1.com\nhttps://example2.com")

# Process URLs
if st.button("Scrape News"):
    urls = [url.strip() for url in urls_input.splitlines() if url.strip()]
    if urls:
        all_data = pd.DataFrame()
        for url in urls:
            df = scrape_news(url)
            all_data = pd.concat([all_data, df], ignore_index=True)

        if not all_data.empty:
            st.success("✅ News data scraped successfully!")
            st.dataframe(all_data)

            # Excel Export
            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                all_data.to_excel(writer, index=False, sheet_name='News')
                st.download_button(
                    label="📥 Download Excel Report",
                    data=output.getvalue(),
                    file_name='news_scraped_data.xlsx',
                    mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                )
        else:
            st.warning("No headlines found from the provided URLs.")
    else:
        st.warning("Please enter at least one valid URL.")
