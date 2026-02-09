import streamlit as st
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

# --- SIDEBAR & CONFIG ---
st.sidebar.title("⚙️ Configuration")
st.sidebar.markdown("**Built by Hitanshu Kumar Singh**")
st.sidebar.info("💡 Automates lead research & outreach.")

api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

# --- CORE FUNCTIONS ---

def extract_emails(text):
    """Finds emails in text using Regex."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    return list(set(emails))

def scrape_website(url_or_name):
    """
    Scrapes URL or Guesses URL from Name.
    """
    target_url = url_or_name
    
    # SMART GUESSER: If input is 'Tesla', try 'https://www.tesla.com'
    if "." not in target_url and " " not in target_url:
        target_url = f"https://www.{target_url.lower()}.com"
    elif not target_url.startswith('http'):
        target_url = 'https://' + target_url

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        response = requests.get(target_url, headers=headers, timeout=10)
        
        if response.status_code in [403, 401, 503]:
            return {
                "text": f"Website {target_url} is protected. Analyzed domain.",
                "emails": "",
                "contact_email": "Not Found",
                "source": "Protected_Site",
                "real_url": target_url
            }
            
        soup = BeautifulSoup(response.content, 'html.parser')
        text = soup.get_text(separator=' ', strip=True)[:4000]
        emails = extract_emails(text)
        
        return {
            "text": text,
            "emails": ", ".join(emails),
            "contact_email": emails[0] if emails else "Not Found",
            "source": "Scraped",
            "real_url": target_url
        }
        
    except Exception as e:
        return {
            "text": f"Could not access automatically. User Input: {url_or_name}.",
            "emails": "",
            "contact_email": "Not Found",
            "source": "Manual_Fallback",
            "real_url": target_url
        }

def generate_pitch(company_name, company_data, api_key):
    """
    Tries AI. If AI fails, uses a High-Quality Template (Fail-Safe).
    """
    # 1. Prepare the AI Request
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    Write a cold email to {company_name}.
    My Company: LuSent AI (We sell AI Automation).
    Their Data: {company_data['text']}
    Keep it under 150 words. Punchy.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    # 2. Try Connecting to AI
    try:
        if not api_key:
            raise Exception("No API Key")
            
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # LOG THE ERROR for debugging (Hidden from main view, shown in sidebar if needed)
            st.sidebar.error(f"API Error ({company_name}): {response.status_code} - {response.text}")
            raise Exception("API Failed")
            
    except Exception as e:
        # 3. THE FAIL-SAFE TEMPLATE
        # If the API key is wrong, quota is full, or model is 404, WE STILL GENERATE A PITCH.
        return f"""Hi {company_name} Team,

I've been following {company_name}'s work in the industry and noticed some opportunities to streamline your operations.

At LuSent AI, we help forward-thinking companies automate repetitive workflows (like lead research and data entry) to save 20+ hours a week.

Based on your current setup, I believe we could deploy a custom AI agent for you in under 48 hours.

Open to a 10-min demo?

Best,
Hitanshu
(LuSent AI Labs)"""

def create_mailto_link(email, subject, body):
    """Creates a clean mailto link."""
    if email == "Not Found": 
        email = ""
    params = {"view": "cm", "fs": "1", "to": email, "su": subject, "body": body}
    return f"https://mail.google.com/mail/u/0/?{urllib.parse.urlencode(params)}"

# --- MAIN UI ---
st.title("🤖 LuSent AI | Auto-Outreach Agent")

# Tabs
tab1, tab2 = st.tabs(["🔗 Single Input", "📂 Bulk Upload"])
inputs_to_process = []

with tab1:
    user_input = st.text_input("Enter Company Name OR URL", placeholder="e.g. Tesla, OpenAI, or https://swiggy.com")
    if user_input: inputs_to_process.append(user_input)

with tab2:
    bulk_input = st.text_area("Paste List (One per line)", height=150, placeholder="Tesla\nSwiggy\nhttps://www.zomato.com")
    if bulk_input: inputs_to_process = [line.strip() for line in bulk_input.split('\n') if line.strip()]

if st.button("🚀 Run AI Agent", type="primary"):
    if not inputs_to_process:
        st.error("Please enter at least one company.")
    else:
        st.info(f"🔄 Processing {len(inputs_to_process)} leads...")
        results = []
        progress_bar = st.progress(0)
        
        for i, item in enumerate(inputs_to_process):
            # 1. Research
            data = scrape_website(item)
            
            # Name Cleaning
            if "http" in item:
                company_name = item.replace("https://", "").replace("http://", "").replace("www.", "").split('.')[0].title()
            else:
                company_name = item.title()
            
            # 2. Generate Pitch (With Fail-Safe)
            pitch = generate_pitch(company_name, data, api_key)
            
            # 3. Email Link
            subject = f"AI Strategy for {company_name}"
            email_link = create_mailto_link(data['contact_email'], subject, pitch)
            
            results.append({
                "Company": company_name,
                "Website": data['real_url'],
                "Contact Email": data['contact_email'],
                "Generated Pitch": pitch,
                "Email Link": email_link,
                "Status": "Success"
            })
            progress_bar.progress((i + 1) / len(inputs_to_process))
            
        st.success("✅ Analysis Complete!")
        
        # --- DISPLAY RESULTS ---
        for res in results:
            with st.expander(f"🏢 {res['Company']} (Click for Details)", expanded=True):
                c1, c2 = st.columns([3, 1])
                
                with c1:
                    st.subheader("📝 Personalized Pitch")
                    st.text_area("Copy Pitch:", value=res['Generated Pitch'], height=200, key=f"p_{res['Company']}")
                
                with c2:
                    st.subheader("⚡ Action")
                    st.write(f"**Email:** {res['Contact Email']}")
                    st.write(f"**URL:** {res['Website']}")
                    # The Button you asked for
                    st.link_button(f"📤 Draft Gmail", res['Email Link'])

        # --- CSV EXPORT ---
        df = pd.DataFrame(results)
        csv_df = df.drop(columns=['Email Link'])
        # utf-8-sig fixes the Excel read-only/symbol issues
        csv = csv_df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button("📥 Download Report (Excel CSV)", csv, "lusent_leads.csv", "text/csv")
