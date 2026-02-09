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

# Get API Key
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
    """
    Scrapes the website.
    IMPORTANT: If scraping fails (Anti-Bot), it returns a 'Fallback' signal 
    so the AI can still write the pitch using internal knowledge.
    """
    # 1. Handle URL formatting
    target_url = url
    if not target_url.startswith('http'):
        target_url = 'https://' + target_url

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(target_url, headers=headers, timeout=10)
        
        # If blocked (403/401), trigger fallback
        if response.status_code in [403, 401, 503]:
            return {
                "text": "Website Protected (Anti-Bot). Use AI Internal Knowledge.",
                "emails": "",
                "contact_email": "Not Found",
                "source": "AI_Fallback"
            }

        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Remove scripts and styles for cleaner text
        for script in soup(["script", "style"]):
            script.decompose()
            
        text = soup.get_text(separator=' ', strip=True)[:5000]
        emails = extract_emails(text)
        
        return {
            "text": text,
            "emails": ", ".join(emails),
            "contact_email": emails[0] if emails else "Not Found",
            "source": "Scraped"
        }
        
    except Exception as e:
        # Graceful fallback instead of crashing
        return {
            "text": f"Scraping Failed ({str(e)}). Use AI Internal Knowledge.",
            "emails": "",
            "contact_email": "Not Found",
            "source": "AI_Fallback"
        }

def generate_pitch(company_name, company_data):
    """
    Uses Gemini to write the outreach message.
    Includes Automatic Failover: Tries Flash -> Falls back to Pro.
    """
    prompt = f"""
    ACT AS: A Senior B2B Sales Development Rep for 'LuSent AI Labs'.
    TARGET: {company_name}
    CONTEXT: We sell AI Automation Services (Lead Gen, Chatbots, Workflow Automation).
    
    SOURCE DATA: 
    {company_data['text']}
    
    INSTRUCTIONS:
    1. If 'SOURCE DATA' is real, use it to personalize the hook.
    2. If 'SOURCE DATA' says "Protected" or "Failed", use your INTERNAL TRAINING DATA about {company_name} to write the pitch.
    3. Pain Point: Ask if manual processes are slowing them down.
    4. Solution: Briefly pitch how LuSent AI can automate their workflows.
    5. CTA: Ask for a 10-min chat.
    
    CONSTRAINT: Keep it under 150 words. No fluff.
    """

    try:
        # Try the faster, cheaper model first
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        return response.text
    except Exception:
        try:
            # Fallback to the standard model if Flash fails
            model = genai.GenerativeModel('gemini-pro')
            response = model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating pitch: {e}"

def create_mailto_link(email, subject, body):
    """Creates a clickable link to open Gmail."""
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
st.markdown("Enter a company URL to scrape data and generate a hyper-personalized pitch.")

# Tabs
tab1, tab2 = st.tabs(["🔗 Single URL", "📂 Bulk Upload"])
urls_to_process = []

with tab1:
    url_input = st.text_input("Company Website URL", placeholder="e.g. https://www.swiggy.com")
    if url_input: urls_to_process.append(url_input)

with tab2:
    bulk_input = st.text_area("Paste URLs (one per line)", height=150)
    if bulk_input: 
        urls_to_process = [line.strip() for line in bulk_input.split('\n') if line.strip()]

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

            # 1. Scrape (Or Fallback)
            data = scrape_website(url)

            # 2. Smart Name Extraction
            # Handles "https://www.google.com" -> "Google"
            # Handles "Tesla" -> "Tesla"
            clean_url = url.replace("https://", "").replace("http://", "").replace("www.", "")
            company_name = clean_url.split('/')[0].split('.')[0].title()

            # 3. Generate Pitch (ALWAYS runs, even if scraping failed)
            pitch = generate_pitch(company_name, data)
            
            # 4. Create Email Link
            subject = f"AI Automation for {company_name}"
            email_link = create_mailto_link(data['contact_email'], subject, pitch)

            results.append({
                "Company": company_name,
                "Website": url,
                "Contact Email": data['contact_email'],
                "Generated Pitch": pitch,
                "Link": email_link,
                "Status": "Success"
            })

            progress_bar.progress((i + 1) / len(urls_to_process))

        status_text.text("✅ All tasks completed!")

        # --- DISPLAY RESULTS ---
        # Display Cards for better UI
        for res in results:
            with st.container(border=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.subheader(f"🏢 {res['Company']}")
                    st.caption("📝 Generated Pitch (Hover top-right to copy)")
                    st.code(res['Generated Pitch'], language='text')
                with c2:
                    st.subheader("⚡ Action")
                    st.write(f"**Email:** {res['Contact Email']}")
                    st.link_button("📤 Draft Gmail", res['Link'])

        # --- CSV EXPORT FIX ---
        df = pd.DataFrame(results)
        # Drop the link column for CSV
        csv_df = df.drop(columns=['Link'])
        # Replace Newlines with ' || ' so Excel doesn't break
        csv_df['Generated Pitch'] = csv_df['Generated Pitch'].apply(lambda x: x.replace('\n', ' || '))
        
        csv = csv_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Report (Excel Compatible CSV)",
            data=csv,
            file_name="lusent_ai_leads.csv",
            mime="text/csv",
        )
