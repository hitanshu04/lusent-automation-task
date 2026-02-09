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

api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.warning("⚠️ Please enter your Gemini API Key in the sidebar to proceed.")
    st.stop()

# Configure Gemini
genai.configure(api_key=api_key)

# --- CORE FUNCTIONS ---

def extract_emails(text):
    """Finds emails in text using Regex."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    return list(set(emails))

def scrape_website(url):
    """Scrapes the website. If blocked, returns a 'Smart Fallback'."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5'
        }
        
        if not url.startswith('http'):
            url = 'https://' + url
            
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code in [403, 401, 503]:
            raise Exception("Anti-Bot Protection")
            
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)
        clean_text = text[:4000]
        
        emails = extract_emails(text)
        contact_email = emails[0] if emails else "Not Found"
        
        return {
            "text": clean_text,
            "emails": ", ".join(emails),
            "contact_email": contact_email,
            "error": None,
            "source": "Scraped"
        }
        
    except Exception as e:
        # FALLBACK: If scraping fails, we pass the domain to AI
        domain = url.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
        return {
            "text": f"This website ({url}) blocked the scraper. However, the domain is {domain}. Use your internal knowledge base to pitch services to {domain}.",
            "emails": "",
            "contact_email": "Not Found (Protected)",
            "error": "Access Protected (Using AI Knowledge)",
            "source": "AI_Fallback"
        }

def generate_pitch(company_name, company_data):
    """Generates the pitch with a Fail-Safe mechanism."""
    
    prompt = f"""
    ACT AS: A Senior B2B Sales Development Rep for 'LuSent AI Labs'.
    TARGET COMPANY: {company_name}
    CONTEXT: We sell AI Automation Services (Lead Gen, Chatbots, Workflow Automation).
    
    SOURCE DATA: 
    {company_data['text']}
    
    INSTRUCTIONS:
    1. If the 'SOURCE DATA' contains real website content, use it to personalize the email.
    2. If the 'SOURCE DATA' says "Access Protected", USE YOUR OWN KNOWLEDGE about {company_name} to write the pitch.
    3. Keep it professional, punchy, and under 150 words.
    """
    
    # --- SAFETY NET ---
    # Try the newest model. If it fails (404), switch to the old reliable one.
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        try:
            # Fallback to Pro (Old Reliable)
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e2:
            return f"Error: {e2}"

# --- MAIN UI ---
st.title("🤖 LuSent AI | Auto-Outreach Agent")
st.markdown("Enter a company URL to scrape data and generate a pitch.")

tab1, tab2 = st.tabs(["🔗 Single URL", "📂 Bulk Upload"])

urls_to_process = []

with tab1:
    url_input = st.text_input("Company Website URL", placeholder="e.g. https://www.swiggy.com")
    if url_input:
        urls_to_process.append(url_input)

with tab2:
    bulk_input = st.text_area("Paste URLs (one per line)", height=150)
    if bulk_input:
        urls_to_process = [line.strip() for line in bulk_input.split('\n') if line.strip()]

if st.button("🚀 Run AI Agent", type="primary"):
    if not urls_to_process:
        st.error("Please enter at least one URL.")
    else:
        results = []
        progress_bar = st.progress(0)
        
        for i, url in enumerate(urls_to_process):
            data = scrape_website(url)
            company_name = url.replace("https://", "").replace("http://", "").replace("www.", "").split('.')[0].title()
            
            # Generate Pitch
            pitch = generate_pitch(company_name, data)
            
            status = "Success"
            if data['source'] == "AI_Fallback":
                status = "Success (AI Inference)"
                
            results.append({
                "Company": company_name,
                "Website": url,
                "Contact Email": data['contact_email'],
                "Generated Pitch": pitch,
                "Status": status
            })
            progress_bar.progress((i + 1) / len(urls_to_process))
            
        st.success("✅ Processing Complete!")
        df = pd.DataFrame(results)
        st.subheader("🎯 Results")
        st.dataframe(df, use_container_width=True)
        
        csv = df.to_csv(index=False).encode('utf-8')
        st.download_button("📥 Download Report (CSV)", csv, "lusent_leads.csv", "text/csv")
