import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import os

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="LuSent AI - Automation Agent",
    page_icon="🤖",
    layout="wide"
)

# --- SIDEBAR & API KEY ---
st.sidebar.title("⚙️ Configuration")
st.sidebar.markdown("**Built by Hitanshu Kumar Singh**")

# Get API Key from Streamlit Secrets (for deployment) or User Input
api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.warning("⚠️ Please enter your Gemini API Key in the sidebar to proceed.")
    st.stop()

genai.configure(api_key=api_key)

# --- CORE FUNCTIONS ---


def extract_emails(text):
    """Finds emails in text using Regex."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    return list(set(emails))

# === BONUS 2: ERROR HANDLING (Robust Scraping) ===


def scrape_website(url):
    """Scrapes the website for text and emails."""
    try:
        # Add headers to mimic a real browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

        # Handle missing http/https
        if not url.startswith('http'):
            url = 'https://' + url

        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Get visible text
        text = soup.get_text(separator=' ', strip=True)
        clean_text = text[:4000]  # Limit text for LLM

        # Find emails
        emails = extract_emails(text)
        contact_email = emails[0] if emails else "Not Found"

        return {
            "text": clean_text,
            "emails": ", ".join(emails),
            "contact_email": contact_email,
            "error": None
        }
    except Exception as e:
        # Graceful error handling
        return {"error": str(e), "text": "", "contact_email": "Error"}


def generate_pitch(company_name, company_data):
    """Uses Gemini to write the outreach message."""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')

        prompt = f"""
        ACT AS: A Senior B2B Sales Development Rep for 'LuSent AI Labs'.
        TARGET: {company_name}
        CONTEXT: We sell AI Automation Services (Lead Gen, Chatbots, Workflow Automation).
        
        WEBSITE DATA: 
        {company_data['text']}
        
        TASK: Write a personalized cold email to the Founder.
        1. Hook: Mention a specific detail from their website.
        2. Pain Point: Ask if manual processes are slowing them down.
        3. Solution: Briefly pitch how LuSent AI can automate their workflows.
        4. CTA: Ask for a 10-min chat.
        
        CONSTRAINT: Keep it under 150 words. No fluff.
        """

        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"LLM Error: {e}"


# --- MAIN UI ---
st.title("🤖 LuSent AI | Auto-Outreach Agent")
st.markdown(
    "Enter a company URL to scrape data, find emails, and generate a hyper-personalized pitch.")

# === BONUS 3: MULTIPLE COMPANY INPUTS ===
# Tabs for Single vs Bulk
tab1, tab2 = st.tabs(["🔗 Single URL", "📂 Bulk Upload"])

urls_to_process = []

with tab1:
    url_input = st.text_input("Company Website URL",
                              placeholder="e.g. https://www.swiggy.com")
    if url_input:
        urls_to_process.append(url_input)

with tab2:
    bulk_input = st.text_area("Paste URLs (one per line)", height=150)
    if bulk_input:
        urls_to_process = [line.strip()
                           for line in bulk_input.split('\n') if line.strip()]

# Action Button
if st.button("🚀 Run AI Agent", type="primary"):
    if not urls_to_process:
        st.error("Please enter at least one URL.")
    else:
        results = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        for i, url in enumerate(urls_to_process):
            status_text.text(f"Processing {url}...")

            # 1. Scrape
            data = scrape_website(url)

            # 2. Extract Name (Simple Logic)
            company_name = url.replace(
                "https://", "").replace("http://", "").replace("www.", "").split('.')[0].title()

            # 3. Generate Pitch (if scraping worked)
            if not data['error']:
                pitch = generate_pitch(company_name, data)
                results.append({
                    "Company": company_name,
                    "Website": url,
                    "Contact Email": data['contact_email'],
                    "Generated Pitch": pitch,
                    "Status": "Success"
                })
            else:
                results.append({
                    "Company": company_name,
                    "Website": url,
                    "Contact Email": "N/A",
                    "Generated Pitch": f"Failed: {data['error']}",
                    "Status": "Failed"
                })

            progress_bar.progress((i + 1) / len(urls_to_process))

        status_text.text("✅ All tasks completed!")

        # --- DISPLAY RESULTS ---
        df = pd.DataFrame(results)

        st.subheader("🎯 Results")
        st.dataframe(df, use_container_width=True)

        # === BONUS 1: SAVE RESULTS TO CSV FILE ===
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Report (CSV)",
            data=csv,
            file_name="lusent_ai_leads.csv",
            mime="text/csv",
        )
