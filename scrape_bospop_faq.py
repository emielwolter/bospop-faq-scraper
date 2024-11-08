import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import io



def scrape_bospop_faq():
    # Get the FAQ page
    url = "https://bospop.nl/faq/"
    headers = {
        'User-Agent': 'BospopFAQBot/1.0',
        'From': 'e.wolter@bospop.nl'  # Optional: identify yourself to the site owner
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Initialize lists to store data
    categories = []
    questions = []
    answers = []

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
                categories.append(category)
                questions.append(question)
                answers.append(answer)

    # Create DataFrame
    df = pd.DataFrame({
        'Category': [cat.capitalize() for cat in categories],  # Normalize category capitalization
        'Question': questions,
        'Answer': answers
    })

    return df

def main():
    st.set_page_config(
        page_title="Bospop FAQ Generator",
        page_icon="📊",
        layout="wide"
    )
    
    st.title("Bospop FAQ Generator")
    st.markdown("""
    Deze tool haalt de FAQ van de Bospop website op en maakt er een Excel bestand van.
    
    Klik op de knop hieronder om het FAQ Excel bestand te genereren en te downloaden.
    """)
    
    if st.button("Genereer FAQ Excel Bestand"):
        try:
            with st.spinner("FAQ data aan het ophalen..."):
                faq_df = scrape_bospop_faq()
                st.subheader("Voorbeeld van FAQ Data")
                st.dataframe(faq_df)
                
                if len(faq_df) == 0:
                    st.error("Geen FAQ data gevonden. Controleer of de website structuur is gewijzigd.")
                    return
                
                # Generate Excel file in memory
                output = io.BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    # Write DataFrame to Excel
                    faq_df.to_excel(writer, index=False, sheet_name='FAQ')
                    
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
                    for col_num, value in enumerate(faq_df.columns.values):
                        worksheet.write(0, col_num, value, header_format)
                        
                    # Apply cell format to all data cells
                    for row in range(len(faq_df)):
                        for col in range(len(faq_df.columns)):
                            worksheet.write(row + 1, col, faq_df.iloc[row, col], cell_format)
                
                # Offer download button
                st.download_button(
                    label="Download Excel bestand",
                    data=output.getvalue(),
                    file_name="bospop_faq.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                
                st.success("Excel bestand succesvol gegenereerd!")
                
        except requests.exceptions.RequestException:
            st.error("Kan geen verbinding maken met de Bospop website. Controleer je internetverbinding.")
        except Exception as e:
            st.error(f"Er is een fout opgetreden: {str(e)}")

if __name__ == "__main__":
    main()
