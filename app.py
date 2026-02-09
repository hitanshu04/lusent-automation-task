import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import urllib.parse
import random

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="LuSent AI - Automation Agent",
    page_icon="🤖",
    layout="wide"
)

# --- SIDEBAR ---
st.sidebar.title("⚙️ Configuration")
st.sidebar.markdown("**Built by Hitanshu Kumar Singh**")
st.sidebar.info("💡 Automates lead research & outreach.")

api_key = st.sidebar.text_input("Enter Gemini API Key", type="password")

if not api_key:
    st.warning("⬅️ Please enter your Gemini API Key to start.")
    st.stop()

# --- CORE FUNCTIONS ---

def clean_company_name(raw_input):
    """Cleans URL to get a readable Company Name."""
    clean = raw_input.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    clean = clean.split('/')[0].split('.')[0]
    return clean.title()

def extract_emails(text):
    """Finds emails in text."""
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    return list(set(emails))

def scrape_website(url_or_name):
    """Scrapes URL or Guesses URL from Name."""
    target_url = url_or_name
    
    # Smart Guesser
    if "." not in target_url and " " not in target_url:
        target_url = f"https://www.{target_url.lower()}.com"
    elif not target_url.startswith('http'):
        target_url = 'https://' + target_url

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(target_url, headers=headers, timeout=10)
        
        if response.status_code in [403, 401, 503]:
            return {
                "text": "Website protected.",
                "emails": "",
                "contact_email": "Not Found",
                "real_url": target_url
            }
            
        soup = BeautifulSoup(response.content, 'html.parser')
        # Get text but skip scripts and styles
        for script in soup(["script", "style"]):
            script.decompose()
        text = soup.get_text(separator=' ', strip=True)[:5000]
        emails = extract_emails(text)
        
        return {
            "text": text,
            "emails": ", ".join(emails),
            "contact_email": emails[0] if emails else "Not Found",
            "real_url": target_url
        }
    except:
        return {
            "text": "Could not access website.",
            "emails": "",
            "contact_email": "Not Found",
            "real_url": target_url
        }

def smart_fallback_pitch(company_name, text_snippet):
    """
    Creates a cleaner fallback pitch by finding REAL sentences, not menus.
    """
    # 1. Skip the first 500 chars (usually navigation menus)
    useful_text = text_snippet[500:] if len(text_snippet) > 500 else text_snippet
    
    # 2. Find the first nice sentence (ending in .)
    match = re.search(r'([A-Z][^\.]{10,100}\.)', useful_text)
    snippet = match.group(1) if match else "your industry leadership"
    
    return f"""Hi {company_name} Team,

I was researching {company_name} and was impressed by your work: "{snippet}"

Managing operations for a company like yours can be complex. At LuSent AI, we help businesses automate repetitive workflows (like Lead Gen & Data Entry) to save 20+ hours/week.

Based on your profile, I believe we could deploy a custom AI agent for you in 48 hours.

Open to a 10-min chat?

Best,
Hitanshu, LuSent AI Labs"""

def generate_pitch(company_name, company_data, api_key):
    """
    Tries GEMINI 1.5 FLASH -> Fallback to SMART TEMPLATE.
    """
    url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={api_key}"
    
    prompt = f"""
    ACT AS: A Senior B2B Sales Development Rep for 'LuSent AI Labs'.
    TARGET: {company_name}
    CONTEXT: We sell AI Automation (Lead Gen, Chatbots).
    THEIR WEBSITE DATA: "{company_data['text']}"
    INSTRUCTIONS:
    1. Find ONE specific pain point they might have based on the text.
    2. Write a cold email to the Founder.
    3. OPENING: Mention a specific detail from their site (NOT the menu).
    4. PITCH: Explain how LuSent AI can automate that process.
    5. CTA: "Open to a 10 min demo?"
    6. Sign off: Hitanshu, LuSent AI Labs.
    7. Keep it under 150 words.
    """
    
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    
    try:
        response = requests.post(url, json=payload, headers={'Content-Type': 'application/json'})
        if response.status_code == 200:
            return response.json()['candidates'][0]['content']['parts'][0]['text']
        else:
            # API FAILED -> Use the Cleaner Fallback
            return smart_fallback_pitch(company_name, company_data['text'])
    except:
        return smart_fallback_pitch(company_name, company_data['text'])

def create_mailto_link(email, subject, body):
    """Creates the 'Draft Gmail' link."""
    if email == "Not Found": email = ""
    params = {"view": "cm", "fs": "1", "to": email, "su": subject, "body": body}
    return f"https://mail.google.com/mail/u/0/?{urllib.parse.urlencode(params)}"

# --- MAIN UI ---
st.title("🤖 LuSent AI | Auto-Outreach Agent")

tab1, tab2 = st.tabs(["🔗 Single Input", "📂 Bulk Upload"])
inputs = []

with tab1:
    u = st.text_input("Enter Company Name OR URL", placeholder="e.g. Tesla")
    if u: inputs.append(u)

with tab2:
    b = st.text_area("Paste List (One per line)")
    if b: inputs = [line.strip() for line in b.split('\n') if line.strip()]

if st.button("🚀 Run AI Agent", type="primary"):
    if not inputs:
        st.error("Enter a company first.")
    else:
        st.info(f"🔄 Analyzing {len(inputs)} companies...")
        results = []
        
        prog = st.progress(0)
        
        for i, item in enumerate(inputs):
            data = scrape_website(item)
            name = clean_company_name(item)
            pitch = generate_pitch(name, data, api_key)
            link = create_mailto_link(data['contact_email'], f"AI for {name}", pitch)
            
            results.append({
                "Company": name,
                "URL": data['real_url'],
                "Email": data['contact_email'],
                "Pitch": pitch,
                "Link": link
            })
            prog.progress((i + 1) / len(inputs))
            
        st.success("✅ Done! Results below:")
        
        # --- DISPLAY RESULTS (ALWAYS VISIBLE) ---
        for res in results:
            with st.container(border=True):
                st.subheader(f"🏢 {res['Company']}")
                c1, c2 = st.columns([3, 1])
                
                with c1:
                    st.caption("📝 Personalized Pitch (Hover to Copy)")
                    st.code(res['Pitch'], language='text') 
                
                with c2:
                    st.caption("⚡ Action")
                    st.write(f"**Email:** {res['Email']}")
                    st.link_button("📤 Draft Gmail", res['Link'])

        # --- CSV EXPORT FIX (Replaces Enters with Spaces) ---
        df = pd.DataFrame(results).drop(columns=['Link'])
        # THIS LINE FIXES THE EXCEL ISSUE
        df['Pitch'] = df['Pitch'].apply(lambda x: x.replace('\n', ' || '))
        
        st.download_button("📥 Download Report (CSV)", df.to_csv(index=False, encoding='utf-8-sig'), "lusent_leads.csv")
