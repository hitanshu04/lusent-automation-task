import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
import re
import urllib.parse
from groq import Groq

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="LuSent AI - Automation Agent",
    page_icon="🤖",
    layout="wide"
)

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
    """Scrapes URL. Handles errors gracefully."""
    target_url = url_or_name
    
    # Smart Guesser
    if "." not in target_url and " " not in target_url:
        target_url = f"https://www.{target_url.lower()}.com"
    elif not target_url.startswith('http'):
        target_url = 'https://' + target_url

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(target_url, headers=headers, timeout=10)
        
        # If blocked, return specific flag
        if response.status_code in [403, 401, 503]:
            return {"text": "PROTECTED_MODE", "emails": "", "contact_email": "Not Found", "real_url": target_url}
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove Junk
        for element in soup(['nav', 'header', 'footer', 'script', 'style', 'aside']):
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
        return {"text": "PROTECTED_MODE", "emails": "", "contact_email": "Not Found", "real_url": target_url}

def generate_pitch(company_name, company_data):
    """
    Uses Groq (Llama 3.3).
    SMART LOGIC: Dynamically decides the 'Pain Point' based on the company type.
    """
    
    # CASE 1: Website Scraped Successfully
    if company_data['text'] != "PROTECTED_MODE":
        prompt = f"""
        ACT AS: A Senior B2B Sales Rep for 'LuSent AI'.
        TARGET: {company_name}
        CONTEXT: We sell Custom AI Automation (NOT just Lead Gen. We automate Operations, Support, Hiring, Logistics).
        WEBSITE DATA: "{company_data['text'][:3000]}"
        
        INSTRUCTIONS:
        1. Analyze the WEBSITE DATA. What does {company_name} actually do?
        2. Identify ONE specific, expensive operational bottleneck relevant to THEIR industry.
           - If Logistics/Food -> Pitch Support/Route Optimization.
           - If VC/Finance -> Pitch Application Screening/Data Analysis.
           - If Manufacturing -> Pitch Supply Chain/Internal Ops.
        3. Write a cold email to the Founder.
        
        STRICT RULES:
        1. Output ONLY the email body. NO Subject.
        2. Start with "Hi {company_name} Team,".
        3. Mention a specific detail from their site (Prove you read it).
        4. Pitch: "I imagine [Specific Process] is manual/complex for you. LuSent AI can automate it."
        5. CTA: "Open to a 10 min demo?"
        6. Sign off: Best, Hitanshu, LuSent AI Labs.
        """
    
    # CASE 2: Website Blocked (Smart Guessing)
    else:
        prompt = f"""
        ACT AS: A Senior B2B Sales Rep for 'LuSent AI'.
        TARGET: {company_name}
        CONTEXT: We sell Custom AI Automation.
        
        INSTRUCTIONS:
        1. Use your internal knowledge to identify what {company_name} does.
        2. Pick a relevant bottleneck (e.g. Tesla -> Manufacturing/Support, Swiggy -> Rider Support).
        3. Do NOT mention you couldn't access their website.
        
        STRICT RULES:
        1. Output ONLY the email body. NO Subject.
        2. Start with "Hi {company_name} Team,".
        3. Say: "I've been following {company_name}'s leadership in the industry."
        4. Pitch: "Scaling [Specific Industry Process] often brings bottlenecks. LuSent AI automates workflows to save 20+ hours/week."
        5. CTA: "Open to a 10 min demo?"
        6. Sign off: Best, Hitanshu, LuSent AI Labs.
        """
    
    try:
        completion = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile", 
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        return f"Error: {str(e)}"

def create_mailto_link(email, subject, body):
    if email == "Not Found": email = ""
    params = {"view": "cm", "fs": "1", "to": email, "su": subject, "body": body}
    return f"https://mail.google.com/mail/u/0/?{urllib.parse.urlencode(params)}"

# --- MAIN UI ---
st.title("🤖 LuSent AI | Auto-Outreach Agent")

# === BONUS 3: MULTIPLE INPUTS ===
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
            # 1. Scrape
            data = scrape_website(item)
            name = clean_company_name(item)
            
            # 2. Pitch
            pitch = generate_pitch(name, data)
            
            # 3. Link
            link = create_mailto_link(data['contact_email'], f"AI for {name}", pitch)
            
            results.append({
                "Company": name,
                "Website": data['real_url'],
                "Email": data['contact_email'],
                "Generated Pitch": pitch,
                "Link": link
            })
            prog.progress((i + 1) / len(inputs))
            
        st.success("✅ Done!")
        
        # Display Results
        for res in results:
            with st.container(border=True):
                st.subheader(f"🏢 {res['Company']}")
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.caption("📝 Pitch")
                    st.code(res['Generated Pitch'], language='text')
                with c2:
                    st.caption("⚡ Action")
                    st.write(f"**Email:** {res['Email']}")
                    st.link_button("📤 Draft Gmail", res['Link'])
        
        # === BONUS 1: CSV EXPORT ===
        df = pd.DataFrame(results).drop(columns=['Link'])
        
        # CLEANING: Replace Newlines with ' || ' so it stays in one cell in Excel
        df['Generated Pitch'] = df['Generated Pitch'].apply(lambda x: x.replace('\n', ' || '))
        
        st.download_button(
            label="📥 Download Report (CSV)",
            data=df.to_csv(index=False).encode('utf-8'),
            file_name="lusent_leads.csv",
            mime="text/csv"
        )
