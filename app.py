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
st.sidebar.info("💡 Automates lead research & outreach.")

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
    1. Tries to Scrape the URL.
    2. If input is a Name (e.g. 'Tesla'), it GUESSES the URL (www.tesla.com) and Scrapes.
    3. If scraping fails, returns AI Context.
    """
    target_url = url_or_name
    
    # SMART GUESSER: If it looks like a name (no http/www), try to make it a URL
    if "." not in target_url and " " not in target_url:
        target_url = f"https://www.{target_url.lower()}.com"
    elif not target_url.startswith('http'):
        target_url = 'https://' + target_url

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        }
        
        # Try to connect (Real Research)
        response = requests.get(target_url, headers=headers, timeout=10)
        
        # Check for blockers
        if response.status_code in [403, 401, 503]:
            return {
                "text": f"Website {target_url} is protected (Anti-Bot). Analyzed domain: {target_url}.",
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
        # Fallback: If guessing failed (e.g. 'LuSent' -> 'lusent.com' doesn't exist)
        return {
            "text": f"Could not access automatically. User Input: {url_or_name}. Using internal AI database.",
            "emails": "",
            "contact_email": "Not Found",
            "source": "AI_Fallback",
            "real_url": "N/A"
        }

def generate_pitch(company_name, company_data):
    """
    Generates pitch using DIRECT REST API (No Library Errors).
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    ACT AS: A Senior B2B Sales Development Rep for 'LuSent AI Labs'.
    TARGET: {company_name}
    CONTEXT: We sell AI Automation Services (Lead Gen, Chatbots, Workflow Automation).
    
    RESEARCH DATA: 
    {company_data['text']}
    
    INSTRUCTIONS:
    1. Write a cold email to the Founder.
    2. REFERENCE the Research Data to prove you did your homework.
    3. Keep it under 150 words. Punchy.
    4. Focus on how AI can help THEIR specific business.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            return "Error: Unable to generate pitch. Please check API Key."
    except Exception as e:
        return f"Connection Error: {str(e)}"

def create_mailto_link(email, subject, body):
    """Creates a direct Gmail link."""
    if email == "Not Found": email = ""
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
        st.info(f"🔄 Researching {len(inputs_to_process)} leads...")
        results = []
        progress_bar = st.progress(0)
        
        for i, item in enumerate(inputs_to_process):
            # 1. Research (Scrape or Smart Guess)
            data = scrape_website(item)
            
            # Determine Name
            if "http" in item:
                company_name = item.replace("https://", "").replace("http://", "").replace("www.", "").split('.')[0].title()
            else:
                company_name = item.title()
            
            # 2. Generate Pitch
            pitch = generate_pitch(company_name, data)
            
            # 3. Create Action Link
            subject = f"AI Strategy for {company_name}"
            email_link = create_mailto_link(data['contact_email'], subject, pitch)
            
            results.append({
                "Company": company_name,
                "Original Input": item,
                "Identified URL": data['real_url'],
                "Contact Email": data['contact_email'],
                "Generated Pitch": pitch,
                "Email Link": email_link,
                "Status": "Success"
            })
            progress_bar.progress((i + 1) / len(inputs_to_process))
            
        st.success("✅ Research & Analysis Complete!")
        
        # --- DISPLAY RESULTS ---
        for res in results:
            with st.expander(f"🏢 {res['Company']} (Click for Details)", expanded=True):
                c1, c2 = st.columns([3, 1])
                
                with c1:
                    st.subheader("📝 Personalized Pitch")
                    st.text_area("Copy:", value=res['Generated Pitch'], height=150, key=f"p_{res['Company']}")
                
                with c2:
                    st.subheader("⚡ Action")
                    st.write(f"**Email:** {res['Contact Email']}")
                    st.write(f"**URL:** {res['Identified URL']}")
                    st.markdown(f"[**📤 Draft in Gmail**]({res['Email Link']})", unsafe_allow_html=True)

        # --- CSV EXPORT ---
        df = pd.DataFrame(results)
        csv_df = df.drop(columns=['Email Link'])
        csv = csv_df.to_csv(index=False, encoding='utf-8-sig')
        
        st.download_button("📥 Download Report (Excel CSV)", csv, "lusent_leads.csv", "text/csv")
