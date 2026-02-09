import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import urllib.parse
import json

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="LuSent AI - Automation Agent",
    page_icon="🤖",
    layout="wide"
)

# --- SIDEBAR & API KEY ---
st.sidebar.title("⚙️ Configuration")
st.sidebar.markdown("**Built by Hitanshu Kumar Singh**")
st.sidebar.info("💡 This agent automates lead research and outreach drafting.")

api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.warning("⚠️ Please enter your Gemini API Key in the sidebar to proceed.")
    st.stop()

# --- CORE FUNCTIONS ---

def extract_emails(text):
    """Finds emails in text using Regex."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    return list(set(emails))

def scrape_website(url_or_name):
    """
    Scrapes if it's a URL.
    Returns AI context if it's just a Company Name.
    """
    # 1. Check if input is a Name (no 'http' or 'www')
    if "." not in url_or_name or " " in url_or_name:
        return {
            "text": f"User provided Company Name: '{url_or_name}'. No URL provided. Use your internal knowledge.",
            "emails": "",
            "contact_email": "Not Found",
            "source": "Name_Only"
        }

    # 2. Handle URL
    url = url_or_name
    if not url.startswith('http'):
        url = 'https://' + url

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        response = requests.get(url, headers=headers, timeout=10)
        
        if response.status_code in [403, 401, 503]:
            return {
                "text": f"Website {url} is protected. Use internal knowledge for this domain.",
                "emails": "",
                "contact_email": "Not Found",
                "source": "Protected_Site"
            }
            
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)[:4000]
        emails = extract_emails(text)
        
        return {
            "text": text,
            "emails": ", ".join(emails),
            "contact_email": emails[0] if emails else "Not Found",
            "source": "Scraped"
        }
        
    except Exception as e:
        return {
            "text": f"Could not access {url}. Error: {str(e)}",
            "emails": "",
            "contact_email": "Not Found",
            "source": "Error_Fallback"
        }

def generate_pitch(company_name, company_data):
    """
    Generates pitch using DIRECT REST API (No Library = No Version Errors).
    """
    # Using the standard model endpoint
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    ACT AS: A Senior B2B Sales Development Rep for 'LuSent AI Labs'.
    TARGET: {company_name}
    CONTEXT: We sell AI Automation Services (Lead Gen, Chatbots, Workflow Automation).
    
    SOURCE DATA: 
    {company_data['text']}
    
    INSTRUCTIONS:
    1. Write a hyper-personalized cold email to the Founder.
    2. If Source Data is real, reference specific details from it.
    3. If Source Data is generic or missing, use your knowledge about {company_name}.
    4. Keep it under 150 words. Punchy. Professional.
    """
    
    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }]
    }
    
    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # Fallback to Pro if Flash fails (rare)
            url_pro = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={api_key}"
            response = requests.post(url_pro, json=payload, headers={'Content-Type': 'application/json'})
            if response.status_code == 200:
                return response.json()['candidates'][0]['content']['parts'][0]['text']
            else:
                return f"Error from Google: {response.status_code} - {response.text}"
            
    except Exception as e:
        return f"Connection Error: {str(e)}"

def create_mailto_link(email, subject, body):
    """Creates a link to open Gmail."""
    if email == "Not Found": 
        email = ""
    
    # URL Encode the body to handle newlines and special chars
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

# Tabs for Single vs Bulk
tab1, tab2 = st.tabs(["🔗 Single Input", "📂 Bulk Upload"])
inputs_to_process = []

with tab1:
    user_input = st.text_input("Enter Company Name OR Website URL", placeholder="e.g., 'LuSent AI' or 'https://swiggy.com'")
    if user_input: inputs_to_process.append(user_input)

with tab2:
    bulk_input = st.text_area("Paste List (One per line)", height=150, placeholder="Tesla\nhttps://www.zomato.com\nOpenAI")
    if bulk_input: inputs_to_process = [line.strip() for line in bulk_input.split('\n') if line.strip()]

if st.button("🚀 Run AI Agent", type="primary"):
    if not inputs_to_process:
        st.error("Please enter at least one company.")
    else:
        st.info(f"🔄 Processing {len(inputs_to_process)} leads...")
        results = []
        progress_bar = st.progress(0)
        
        for i, item in enumerate(inputs_to_process):
            # 1. Scrape (or Identify)
            data = scrape_website(item)
            
            # Smart Name Extraction
            if "http" in item:
                company_name = item.replace("https://", "").replace("http://", "").replace("www.", "").split('.')[0].title()
            else:
                company_name = item
            
            # 2. Generate Pitch
            pitch = generate_pitch(company_name, data)
            
            # 3. Create Email Link
            subject = f"AI Automation Idea for {company_name}"
            email_link = create_mailto_link(data['contact_email'], subject, pitch)
            
            results.append({
                "Company": company_name,
                "Input": item,
                "Contact Email": data['contact_email'],
                "Generated Pitch": pitch,
                "Email Link": email_link,
                "Status": "Success"
            })
            progress_bar.progress((i + 1) / len(inputs_to_process))
            
        st.success("✅ All Tasks Completed!")
        
        # --- DISPLAY RESULTS (Fixed Syntax) ---
        for res in results:
            with st.expander(f"🏢 {res['Company']} (Click for Details)", expanded=True):
                # Using columns safely
                c1, c2 = st.columns([3, 1])
                
                with c1:
                    st.subheader("📝 Generated Pitch")
                    st.text_area("Copy Pitch:", value=res['Generated Pitch'], height=150, key=f"pitch_{res['Company']}")
                
                with c2:
                    st.subheader("⚡ Action")
                    st.write(f"**Email:** {res['Contact Email']}")
                    st.markdown(f"[**📤 Draft in Gmail**]({res['Email Link']})", unsafe_allow_html=True)

        # --- CSV EXPORT (Fixed for Excel) ---
        df = pd.DataFrame(results)
        csv_df = df.drop(columns=['Email Link']) # Clean for CSV
        csv = csv_df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button(
            label="📥 Download Report (Excel CSV)",
            data=csv,
            file_name="lusent_outreach_leads.csv",
            mime="text/csv"
        )
