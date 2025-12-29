import streamlit as st
from groq import Groq
import requests
import io
from PIL import Image
import PyPDF2
import time
from datetime import datetime

# --- Configuration ---
st.set_page_config(page_title="BrandGenius Enterprise", layout="wide")

# --- 🧠 SESSION STATE (Memory) ---
# Initialize history list if it doesn't exist
if "history" not in st.session_state:
    st.session_state.history = []

# --- 🔑 API KEYS ---
# Checks for keys in Secrets (Cloud) or stops if missing
if "GROQ_API_KEY" in st.secrets:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
else:
    st.error("🚨 Missing GROQ_API_KEY in Streamlit Secrets!")
    st.stop()

if "HF_API_TOKEN" in st.secrets:
    HF_API_TOKEN = st.secrets["HF_API_TOKEN"]
else:
    st.error("🚨 Missing HF_API_TOKEN in Streamlit Secrets!")
    st.stop()

# --- CLIENT SETUP ---
try:
    client = Groq(api_key=GROQ_API_KEY)
except Exception as e:
    st.error(f"Groq Client Error: {e}")

HF_API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"
hf_headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}

# --- HELPER FUNCTIONS ---

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def generate_brand_aware_copy(prompt, context_text):
    """Generates copy using Llama 3 with context."""
    system_instruction = f"""
    You are a Senior Brand Strategist. 
    Strictly adhere to the tone and guidelines below.
    
    --- BRAND GUIDELINES ---
    {context_text[:10000]} 
    ------------------------
    
    Task: Write creative marketing copy.
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt}
            ],
            temperature=0.6,
            max_tokens=1500,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def generate_image_huggingface(prompt, style_context=""):
    """
    Standard Stable Diffusion XL Generation.
    Reverted to simple prompt concatenation for better control.
    """
    enhanced_prompt = f"{prompt}, {style_context}"
    payload = {"inputs": enhanced_prompt}
    
    for attempt in range(3):
        try:
            response = requests.post(HF_API_URL, headers=hf_headers, json=payload)
            if response.status_code == 200:
                return response.content
            elif response.status_code == 503:
                time.sleep(4)
                continue
            else:
                return None
        except:
            return None
    return None

# --- MAIN PAGE LAYOUT ---

st.title("💎 BrandGenius Enterprise")
st.caption("Context-Aware Generative AI: Strategy + Creative")

# 1. CREATE TABS
# This creates the clickable headers at the top of the page
tab1, tab2 = st.tabs(["🛠️ Workstation", "Cc: Campaign History"])

# 2. FILL TAB 1 (The Workstation)
with tab1:
    # Everything indented here goes into Tab 1
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.header("1. Brand Assets")
        
        # PDF Upload
        st.subheader("📄 Strategy & Guidelines")
        uploaded_pdf = st.file_uploader("Upload Brand Guidelines (PDF)", type="pdf")
        brand_context = ""
        if uploaded_pdf:
            with st.status("Processing Document..."):
                brand_context = extract_text_from_pdf(uploaded_pdf)
                st.success("Knowledge Base Updated!")

        st.divider()

        # Image Upload (Reference)
        st.subheader("🖼️ Visual Style Reference")
        uploaded_img = st.file_uploader("Upload Moodboard", type=["jpg", "png"])
        if uploaded_img:
            st.image(uploaded_img, caption="Reference Image", use_container_width=True)
            
        # Manual Style Input (Simple & Reliable)
        visual_style_desc = st.text_input("Describe style:", value="Minimalist, High Contrast, Luxury, 4k")

    with col_right:
        st.header("2. Creation Studio")
        user_prompt = st.text_area("Campaign Brief", height=150, placeholder="e.g., Launch a new organic coffee line...")

        c1, c2 = st.columns(2)
        do_text = c1.button("✍️ Generate On-Brand Copy", type="primary", use_container_width=True)
        do_img = c2.button("🎨 Generate On-Brand Visuals", type="secondary", use_container_width=True)

        st.divider()

        # Logic for TEXT Generation
        if do_text:
            if not user_prompt:
                st.warning("Please enter a brief.")
            else:
                with st.spinner("Writing copy..."):
                    final_context = brand_context if brand_context else "General professional tone."
                    res = generate_brand_aware_copy(user_prompt, final_context)
                    
                    st.markdown("### 📝 Strategic Copy")
                    st.markdown(res)
                    
                    # Save to History
                    st.session_state.history.append({
                        "type": "text", 
                        "prompt": user_prompt, 
                        "content": res, 
                        "time": datetime.now().strftime("%H:%M")
                    })

        # Logic for IMAGE Generation
        if do_img:
            if not user_prompt:
                st.warning("Please enter a brief.")
            else:
                with st.spinner("Rendering visuals..."):
                    image_bytes = generate_image_huggingface(user_prompt, visual_style_desc)
                    
                    if image_bytes:
                        st.markdown("### 🎨 Campaign Visual")
                        generated_img = Image.open(io.BytesIO(image_bytes))
                        st.image(generated_img, use_container_width=True)
                        
                        # Save to History
                        st.session_state.history.append({
                            "type": "image", 
                            "prompt": user_prompt, 
                            "content": image_bytes,
                            "time": datetime.now().strftime("%H:%M")
                        })
                    else:
                        st.error("Generation failed. Try again.")

# 3. FILL TAB 2 (The History)
with tab2:
    # Everything indented here goes into Tab 2
    st.header("🗄️ Session History")
    
    if len(st.session_state.history) == 0:
        st.info("No assets generated yet. Go to the Workstation to start creating.")
    
    # Loop through history in reverse (newest first)
    for i, item in enumerate(reversed(st.session_state.history)):
        with st.expander(f"{item['time']} - {item['type'].upper()}: {item['prompt'][:50]}..."):
            if item['type'] == 'text':
                st.markdown(item['content'])
            elif item['type'] == 'image':
                img = Image.open(io.BytesIO(item['content']))
                st.image(img, use_container_width=True)
                st.download_button("Download", data=item['content'], file_name=f"history_{i}.png", mime="image/png", key=f"dl_{i}")
