import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import urllib.parse
from groq import Groq  # Groq client import

# --- PAGE CONFIGURATION ---
st.set_page_config(page_title="LuSent AI - Automation Agent", page_icon="🤖", layout="wide")

# --- SIDEBAR ---
st.sidebar.title("⚙️ Configuration")
st.sidebar.markdown("**Built by Hitanshu Kumar Singh**")

# Get Groq API Key
api_key = st.sidebar.text_input("Enter Groq API Key", type="password", help="Get free key at console.groq.com")

if not api_key:
    st.warning("⬅️ Please enter Groq API Key to start.")
    st.stop()

# Initialize Groq Client
client = Groq(api_key=api_key)

# --- CORE FUNCTIONS ---

def clean_company_name(raw_input):
    clean = raw_input.lower().replace("https://", "").replace("http://", "").replace("www.", "")
    clean = clean.split('/')[0].split('.')[0]
    return clean.title()

def extract_emails(text):
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    return list(set(emails))

def scrape_website(url_or_name):
    target_url = url_or_name
    if "." not in target_url and " " not in target_url:
        target_url = f"https://www.{target_url.lower()}.com"
    elif not target_url.startswith('http'):
        target_url = 'https://' + target_url

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(target_url, headers=headers, timeout=10)
        
        if response.status_code in [403, 401, 503]:
            return {"text": "Website Protected.", "emails": "", "contact_email": "Not Found", "real_url": target_url}
            
        soup = BeautifulSoup(response.content, 'html.parser')
        for element in soup(['nav', 'header', 'footer', 'script', 'style']):
            element.decompose()
            
        text = soup.get_text(separator=' ', strip=True)[:6000]
        emails = extract_emails(text)
        
        return {
            "text": text,
            "emails": ", ".join(emails),
            "contact_email": emails[0] if emails else "Not Found",
            "real_url": target_url
        }
    except:
        return {"text": "Error accessing site.", "emails": "", "contact_email": "Not Found", "real_url": target_url}

def generate_pitch(company_name, company_data):
    """
    Uses Groq (Llama 3) - Extremely fast and reliable on Cloud.
    """
    prompt = f"""
    ACT AS: A Senior B2B Sales Rep for 'LuSent AI'.
    TARGET: {company_name}
    CONTEXT: We sell AI Automation (Lead Gen, Chatbots).
    WEBSITE DATA: "{company_data['text'][:3000]}"
    
    INSTRUCTIONS:
    1. Analyze the website data. Find ONE likely operational bottleneck.
    2. Write a cold email to the Founder.
    3. OPENING: Mention a specific phrase or goal found in the website data.
    4. PITCH: "I bet managing [Process] is manual. LuSent AI can automate it."
    5. CTA: "Open to a 10 min demo?"
    6. Sign off: Hitanshu, LuSent AI Labs.
    7. Keep it under 150 words.
    """
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama3-8b-8192", # Free and Fast model
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {str(e)}"

def create_mailto_link(email, subject, body):
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
        results = []
        prog = st.progress(0)
        
        for i, item in enumerate(inputs):
            data = scrape_website(item)
            name = clean_company_name(item)
            pitch = generate_pitch(name, data)
            link = create_mailto_link(data['contact_email'], f"AI for {name}", pitch)
            
            results.append({
                "Company": name,
                "URL": data['real_url'],
                "Email": data['contact_email'],
                "Pitch": pitch,
                "Link": link
            })
            prog.progress((i + 1) / len(inputs))
            
        st.success("✅ Done!")
        
        for res in results:
            with st.container(border=True):
                st.subheader(f"🏢 {res['Company']}")
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.caption("📝 Pitch")
                    st.code(res['Pitch'], language='text')
                with c2:
                    st.caption("⚡ Action")
                    st.write(f"**Email:** {res['Email']}")
                    st.link_button("📤 Draft Gmail", res['Link'])
        
        df = pd.DataFrame(results).drop(columns=['Link'])
        df['Pitch'] = df['Pitch'].apply(lambda x: x.replace('\n', '  '))
        st.download_button("📥 Download CSV", df.to_csv(index=False).encode('utf-8'), "lusent_leads.csv")
