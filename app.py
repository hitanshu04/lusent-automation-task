import streamlit as st
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import urllib.parse

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

# Configure Gemini (Using the official library which is now updated)
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
        }
        
        if not url.startswith('http'):
            url = 'https://' + url
            
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code in [403, 401, 503]:
            raise Exception("Anti-Bot Protection")
            
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)[:5000]
        emails = extract_emails(text)
        
        return {
            "text": text,
            "emails": ", ".join(emails),
            "contact_email": emails[0] if emails else "Not Found",
            "source": "Scraped"
        }
        
    except Exception:
        domain = url.replace("https://", "").replace("http://", "").replace("www.", "").split('/')[0]
        return {
            "text": f"Domain: {domain}. (Access Protected)",
            "emails": "",
            "contact_email": "Not Found",
            "source": "AI_Fallback"
        }

def generate_pitch(company_name, company_data):
    """Generates pitch using the Official Library (Safest Method)."""
    
    prompt = f"""
    ACT AS: A Senior B2B Sales Development Rep for 'LuSent AI Labs'.
    TARGET COMPANY: {company_name}
    CONTEXT: We sell AI Automation Services (Lead Gen, Chatbots, Workflow Automation).
    
    SOURCE DATA: 
    {company_data['text']}
    
    INSTRUCTIONS:
    1. Write a cold email to the Founder.
    2. Keep it under 150 words.
    3. Make it punchy and personalized based on the source data.
    4. Do not include placeholders like [Name].
    """
    
    try:
        # We use the standard Flash model. Since requirements.txt is updated, this WILL work.
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        # If Flash fails (rare), fallback to Pro
        try:
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        except:
            return f"Hi {company_name} Team,\n\nI noticed you're leading the market. At LuSent AI, we help companies like yours automate workflows.\n\nOpen to a chat?\n\nBest,\nHitanshu"

def create_mailto_link(email, subject, body):
    """Creates a direct 'Send Email' link for Gmail."""
    if email == "Not Found":
        email = ""
    params = {
        "view": "cm",
        "fs": "1",
        "to": email,
        "su": subject,
        "body": body
    }
    return f"https://mail.google.com/mail/u/0/?{urllib.parse.urlencode(params)}"

# --- MAIN UI ---
st.title("🤖 LuSent AI | Auto-Outreach Agent")

# Tabs
tab1, tab2 = st.tabs(["🔗 Single URL", "📂 Bulk Upload"])
urls_to_process = []

with tab1:
    url_input = st.text_input("Company Website URL", placeholder="https://www.ycombinator.com")
    if url_input: urls_to_process.append(url_input)

with tab2:
    bulk_input = st.text_area("Paste URLs (one per line)")
    if bulk_input: urls_to_process = [line.strip() for line in bulk_input.split('\n') if line.strip()]

if st.button("🚀 Run AI Agent", type="primary"):
    if not urls_to_process:
        st.error("Please enter a URL.")
    else:
        st.info("🔄 Analyzying companies... please wait.")
        results = []
        progress_bar = st.progress(0)
        
        for i, url in enumerate(urls_to_process):
            # 1. Scrape
            data = scrape_website(url)
            company_name = url.replace("https://", "").replace("http://", "").replace("www.", "").split('.')[0].title()
            
            # 2. Generate Pitch
            pitch = generate_pitch(company_name, data)
            
            # 3. Create Email Link
            subject = f"Idea for {company_name} + AI"
            email_link = create_mailto_link(data['contact_email'], subject, pitch)
            
            results.append({
                "Company": company_name,
                "Website": url,
                "Contact Email": data['contact_email'],
                "Generated Pitch": pitch,
                "Email Link": email_link
            })
            progress_bar.progress((i + 1) / len(urls_to_process))
            
        st.success("✅ Analysis Complete!")
        
        # --- DISPLAY RESULTS CARD ---
        for res in results:
            with st.expander(f"🏢 {res['Company']} (Click to Expand)", expanded=True):
                col1, col2 = st.columns([2, 1])
                
                with col1:
                    st.subheader("📧 Generated Pitch")
                    # This creates a copyable text box
                    st.text_area("Copy this:", value=res['Generated Pitch'], height=200, key=res['Company'])
                
                with col
