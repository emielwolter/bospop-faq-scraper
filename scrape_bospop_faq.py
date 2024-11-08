import streamlit as st

# Set page config - must be the first Streamlit command
st.set_page_config(
    page_title="Bospop FAQ Generator",
    page_icon="📝",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        'About': """
        # Bospop FAQ Generator
        
        Deze tool haalt automatisch de FAQ van de Bospop website op en zet deze om naar een Excel bestand.
        
        Ontwikkeld voor Bospop door Erik Wolter.
        """
    }
)

import pandas as pd
import requests
from bs4 import BeautifulSoup
import io
import logging
from typing import Optional
from datetime import datetime
import json
import os
from pathlib import Path
import time

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants
URL = "https://bospop.nl/faq/"
HEADERS = {
    'User-Agent': 'BospopFAQBot/1.0',
    'From': 'e.wolter@bospop.nl'
}
DATA_DIR = Path("data")
DATA_FILE = DATA_DIR / "faq_cache.json"

def scrape_bospop_faq() -> Optional[pd.DataFrame]:
    """
    Scrapes FAQ data from Bospop website with error handling and validation.
    Returns None if scraping fails.
    """
    try:
        logger.info(f"Starting FAQ scrape at {datetime.now()}")
        response = requests.get(URL, headers=HEADERS, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        data = {
            'Category': [],
            'Question': [],
            'Answer': []
        }
        
        # Find all category sections
        category_sections = soup.find_all('h2', class_='elementor-heading-title')
        
        for category_section in category_sections:
            category = category_section.text.strip()
            
            # Find the accordion container following this category
            accordion_container = category_section.find_next('div', class_='jupiterx-advanced-accordion-wrapper')
            if accordion_container:
                # Find all FAQ items in this category
                faq_items = accordion_container.find_all('div', class_='jupiterx-single-advanced-accordion-wrapper')
                
                for item in faq_items:
                    # Extract question
                    question = item.find('span', class_='jx-ac-title').text.strip()
                    
                    # Extract answer
                    answer_div = item.find('div', class_='jupiterx-ac-content-is-editor')
                    if answer_div:
                        answer = answer_div.get_text(strip=True)
                    else:
                        answer = ""
                    
                    # Append to lists
                    data['Category'].append(category)
                    data['Question'].append(question)
                    data['Answer'].append(answer)
        
        # Data validation and cleaning
        df = pd.DataFrame(data)
        df = df.dropna(subset=['Question', 'Answer'])  # Remove rows with missing Q&A
        df = df.drop_duplicates()  # Remove any duplicates
        
        # Normalize text
        for col in df.columns:
            df[col] = df[col].str.strip().str.replace('\s+', ' ', regex=True)
        
        logger.info(f"Successfully scraped {len(df)} FAQ items")
        return df
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Scraping failed: {str(e)}")
        return None

def create_excel_file(df: pd.DataFrame) -> io.BytesIO:
    """Separate function to handle Excel file creation"""
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        # Write DataFrame to Excel
        df.to_excel(writer, index=False, sheet_name='FAQ')
        
        # Get workbook and worksheet objects
        workbook = writer.book
        worksheet = writer.sheets['FAQ']
        
        # Define formats
        header_format = workbook.add_format({
            'bold': True,
            'bg_color': '#4F81BD',
            'font_color': 'white',
            'border': 1,
            'text_wrap': True
        })
        
        cell_format = workbook.add_format({
            'text_wrap': True,
            'border': 1
        })
        
        # Set column widths
        worksheet.set_column('A:A', 20)  # Category column
        worksheet.set_column('B:B', 40)  # Question column
        worksheet.set_column('C:C', 60)  # Answer column
        
        # Apply header format
        for col_num, value in enumerate(df.columns.values):
            worksheet.write(0, col_num, value, header_format)
            
        # Apply cell format to all data cells
        for row in range(len(df)):
            for col in range(len(df.columns)):
                worksheet.write(row + 1, col, df.iloc[row, col], cell_format)
    return output

def save_data_to_file(df: pd.DataFrame, timestamp: str):
    """Save DataFrame and timestamp to JSON file"""
    try:
        DATA_DIR.mkdir(exist_ok=True)
        
        data = {
            'faq_data': df.to_dict(orient='records'),
            'last_update': timestamp
        }
        
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Successfully saved data to {DATA_FILE}")
    except Exception as e:
        logger.error(f"Error saving data to file: {str(e)}")
        raise

def load_data_from_file() -> tuple[Optional[pd.DataFrame], Optional[str]]:
    """Load DataFrame and timestamp from JSON file"""
    try:
        if DATA_FILE.exists():
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                df = pd.DataFrame(data['faq_data'])
                return df, data['last_update']
    except Exception as e:
        logger.error(f"Error loading cached data: {str(e)}")
    return None, None

def initialize_session_state():
    """Initialize session state variables if they don't exist"""
    if 'faq_data' not in st.session_state or 'last_update' not in st.session_state:
        # Try to load from file first
        df, timestamp = load_data_from_file()
        
        # If no cached data, fetch new data
        if df is None or timestamp is None:
            df = scrape_bospop_faq()
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if df is not None:
                save_data_to_file(df, timestamp)
        
        # Update session state
        st.session_state.faq_data = df
        st.session_state.last_update = timestamp

def main():
    st.title("Bospop FAQ Generator")
    
    # Initialize data on first load
    initialize_session_state()
    
    st.markdown("""
    Deze tool haalt de FAQ van de Bospop website op en maakt er een Excel bestand van.
    """)
    
    # Show last update time
    st.info(f"Laatste update: {st.session_state.last_update}")
    
    # Button to refresh data - Move it before the data display
    if st.button("Update FAQ Data", type="primary"):
        try:
            with st.spinner("FAQ data aan het ophalen..."):
                new_faq_df = scrape_bospop_faq()
                
                if new_faq_df is None or len(new_faq_df) == 0:
                    st.error("Geen FAQ data gevonden. Probeer het later opnieuw.")
                else:
                    # Update session state and save to file
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    save_data_to_file(new_faq_df, timestamp)
                    st.session_state.faq_data = new_faq_df
                    st.session_state.last_update = timestamp
                    st.success("FAQ data succesvol bijgewerkt!")
                    time.sleep(1)  # Give a moment for the success message to be visible
                    st.rerun()
                
        except Exception as e:
            logger.error(f"Application error: {str(e)}")
            st.error("Er is een onverwachte fout opgetreden. Probeer het later opnieuw.")
    
    # Show current data preview
    if st.session_state.faq_data is not None:
        with st.expander("Bekijk FAQ Data", expanded=True):
            st.dataframe(st.session_state.faq_data)
        
        # Always show download button for current data
        excel_file = create_excel_file(st.session_state.faq_data)
        st.download_button(
            label="Download Excel bestand",
            data=excel_file.getvalue(),
            file_name=f"bospop_faq_{datetime.now().strftime('%Y%m%d')}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

if __name__ == "__main__":
    main()
