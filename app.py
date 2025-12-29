import streamlit as st
from groq import Groq
import requests
import io
from PIL import Image
import PyPDF2  # Needs: pip install PyPDF2
import time

# --- Configuration ---
st.set_page_config(page_title="BrandGenius Enterprise", layout="wide")

# --- 🔑 API KEYS (Cloud Compatible) ---
# This checks if the keys are in Streamlit Secrets (Cloud) or defaults to None (Local)

import streamlit as st

# 1. GROQ KEY
if "GROQ_API_KEY" in st.secrets:
    GROQ_API_KEY = st.secrets["GROQ_API_KEY"]
else:
    # If running locally without secrets.toml, you can paste your key here TEMPORARILY
    # But for GitHub, keep this blank or use a placeholder
    GROQ_API_KEY = "PASTE_YOUR_GROQ_KEY_HERE_FOR_LOCAL_TESTING_ONLY"

# 2. HUGGING FACE KEY
if "HF_API_TOKEN" in st.secrets:
    HF_API_TOKEN = st.secrets["HF_API_TOKEN"]
else:
    HF_API_TOKEN = "PASTE_YOUR_HF_KEY_HERE_FOR_LOCAL_TESTING_ONLY"

# Stop the app if keys are missing in Cloud
if not GROQ_API_KEY.startswith("gsk_") or not HF_API_TOKEN.startswith("hf_"):
    st.warning("⚠️ API Keys not found! Please set them in Streamlit Cloud Secrets.")

# --- Helper Functions ---

def extract_text_from_pdf(uploaded_file):
    """Extracts raw text from an uploaded PDF file."""
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def generate_brand_aware_copy(prompt, context_text):
    """Generates copy using Llama 3, grounded in the uploaded brand documents."""
    
    system_instruction = f"""
    You are a Senior Brand Strategist. 
    I will provide you with BRAND GUIDELINES / RESEARCH below. 
    You must strictly adhere to the tone, voice, and key findings in that text when writing the copy.
    
    --- BRAND GUIDELINES / RESEARCH ---
    {context_text[:10000]}  # Limit context to avoid token limits
    -----------------------------------
    
    Task: Write creative marketing copy based on the user's request.
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
    Generates an image, appending the 'Brand Style' keywords to the prompt.
    """
    # We enhance the prompt with the style context automatically
    enhanced_prompt = f"{prompt}, {style_context}, 4k, professional commercial photography, award winning"
    
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

# --- Main Streamlit UI ---

st.title("💎 BrandGenius Enterprise")
st.caption("Context-Aware Generative AI: Upload your strategy, generate on-brand assets.")

# --- Layout: 2 Columns (Inputs vs Outputs) ---
col_left, col_right = st.columns([1, 2])

with col_left:
    st.header("1. Brand Assets")
    
    # A. PDF Upload
    st.subheader("📄 Strategy & Guidelines")
    uploaded_pdf = st.file_uploader("Upload Brand Guidelines (PDF)", type="pdf")
    
    brand_context = ""
    if uploaded_pdf:
        with st.status("Processing Document..."):
            brand_context = extract_text_from_pdf(uploaded_pdf)
            st.success("Knowledge Base Updated!")
            st.caption(f"Loaded {len(brand_context)} characters of context.")

    st.divider()

    # B. Image Upload (Visual Reference)
    st.subheader("🖼️ Visual Style Reference")
    uploaded_img = st.file_uploader("Upload Moodboard/Product Shot", type=["jpg", "png"])
    
    visual_style_desc = ""
    if uploaded_img:
        st.image(uploaded_img, caption="Style Reference", use_container_width=True)
        # In a real enterprise app, we would use a Vision Model to analyze this. 
        # For now, we ask the user to tag it to ensure the AI gets it right.
        visual_style_desc = st.text_input("Describe this style (e.g., 'Minimalist, Matte Black, Neon'):", 
                                          value="Minimalist, High Contrast, Luxury")

with col_right:
    st.header("2. Creation Studio")
    
    user_prompt = st.text_area("Campaign Brief", height=150, 
                               placeholder="e.g., Launch a new organic coffee line targeting Gen Z. Focus on sustainability.")

    c1, c2 = st.columns(2)
    do_text = c1.button("✍️ Generate On-Brand Copy", type="primary", use_container_width=True)
    do_img = c2.button("🎨 Generate On-Brand Visuals", type="secondary", use_container_width=True)

    st.divider()

    # --- Results Area ---
    if do_text:
        if not user_prompt:
            st.warning("Please enter a campaign brief.")
        else:
            with st.spinner("Analyzing brand guidelines & writing copy..."):
                # If no PDF is uploaded, we just use a generic instruction
                final_context = brand_context if brand_context else "No specific guidelines provided. Use general professional marketing tone."
                
                res = generate_brand_aware_copy(user_prompt, final_context)
                st.markdown("### 📝 Strategic Copy")
                st.markdown(res)

    if do_img:
        if not user_prompt:
            st.warning("Please enter a campaign brief.")
        else:
            with st.spinner("Rendering visuals..."):
                # Combine User Prompt + Visual Style from the uploaded image description
                image_bytes = generate_image_huggingface(user_prompt, visual_style_desc)
                
                if image_bytes:
                    st.markdown("### 🎨 Campaign Visual")
                    generated_img = Image.open(io.BytesIO(image_bytes))
                    st.image(generated_img, use_container_width=True)
                    
                    # Add a download button for the investor "wow" factor
                    st.download_button("Download Asset", data=image_bytes, file_name="brand_asset.png", mime="image/png")
                else:
                    st.error("Generation failed. The model might be busy.")