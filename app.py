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

# --- 🧠 SESSION STATE ---
if "history" not in st.session_state:
    st.session_state.history = []

# --- 🔑 API KEYS ---
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

# --- Helper Functions ---

def extract_text_from_pdf(uploaded_file):
    try:
        pdf_reader = PyPDF2.PdfReader(uploaded_file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text() + "\n"
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def analyze_image_style(image_bytes):
    """
    Uses Vision AI (BLIP) to 'see' the style of the uploaded image.
    """
    API_URL = "https://api-inference.huggingface.co/models/Salesforce/blip-image-captioning-large"
    headers = {"Authorization": f"Bearer {HF_API_TOKEN}"}
    
    try:
        response = requests.post(API_URL, headers=headers, data=image_bytes)
        if response.status_code == 200:
            description = response.json()[0]['generated_text']
            return f"visual style of {description}, professional lighting, color matched"
        else:
            return "high quality, professional studio lighting"
    except:
        return "high quality, professional studio lighting"

def generate_brand_aware_copy(simple_prompt, context_text):
    """Meta-Prompting for Copy"""
    system_instruction = f"""
    You are a Senior Brand Strategist.
    
    STEP 1: ANALYZE CONTEXT
    --- BRAND GUIDELINES ---
    {context_text[:10000]}
    ------------------------
    
    STEP 2: ACTION
    Interpret the user's request '{simple_prompt}' as a professional marketing task.
    Write the final copy directly. No explanations.
    """
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": simple_prompt}
            ],
            temperature=0.7,
            max_tokens=1500,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"Error: {e}"

def generate_image_huggingface(simple_prompt, style_context=""):
    """Smart Image Generation"""
    enhanced_prompt = f"{simple_prompt}, {style_context}, award winning, 8k, masterpiece"
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
st.caption("Context-Aware Generative AI: Strategy + Creative")

tab1, tab2 = st.tabs(["🛠️ Workstation", "Cc: Campaign History"])

with tab1:
    col_left, col_right = st.columns([1, 2])

    with col_left:
        st.header("1. Brand Assets")
        
        # PDF
        st.subheader("📄 Strategy & Guidelines")
        uploaded_pdf = st.file_uploader("Upload Brand Guidelines (PDF)", type="pdf")
        brand_context = ""
        if uploaded_pdf:
            with st.status("Processing Document..."):
                brand_context = extract_text_from_pdf(uploaded_pdf)
                st.success("Knowledge Base Updated!")

        st.divider()

        # Image Upload & Analysis
        st.subheader("🖼️ Visual Style Reference")
        uploaded_img = st.file_uploader("Upload Moodboard", type=["jpg", "png"])
        
        visual_style_desc = st.text_input("Detected Style:", value="Minimalist, High Contrast", key="style_input")

        if uploaded_img:
            st.image(uploaded_img, caption="Reference Image", use_container_width=True)
            
            if st.button("✨ Analyze Style with Vision AI"):
                with st.spinner("Vision Model is analyzing style..."):
                    bytes_data = uploaded_img.getvalue()
                    detected_style = analyze_image_style(bytes_data)
                    st.info(f"Detected: {detected_style}")
                    # Update the variable to be used in generation
                    visual_style_desc = detected_style 

    with col_right:
        st.header("2. Creation Studio")
        user_prompt = st.text_area("Campaign Brief", height=150, placeholder="e.g., Launch a new organic coffee line...")

        c1, c2 = st.columns(2)
        do_text = c1.button("✍️ Generate On-Brand Copy", type="primary", use_container_width=True)
        do_img = c2.button("🎨 Generate On-Brand Visuals", type="secondary", use_container_width=True)

        st.divider()

        if do_text:
            if not user_prompt:
                st.warning("Please enter a brief.")
            else:
                with st.spinner("Writing copy..."):
                    final_context = brand_context if brand_context else "Professional tone."
                    res = generate_brand_aware_copy(user_prompt, final_context)
                    st.markdown("### 📝 Strategic Copy")
                    st.markdown(res)
                    
                    st.session_state.history.append({
                        "type": "text", 
                        "prompt": user_prompt, 
                        "content": res, 
                        "time": datetime.now().strftime("%H:%M")
                    })

        if do_img:
            if not user_prompt:
                st.warning("Please enter a brief.")
            else:
                with st.spinner(f"Rendering with style: {visual_style_desc}..."):
                    # Pass the detected style variable here
                    image_bytes = generate_image_huggingface(user_prompt, visual_style_desc)
                    
                    if image_bytes:
                        st.markdown("### 🎨 Campaign Visual")
                        generated_img = Image.open(io.BytesIO(image_bytes))
                        st.image(generated_img, use_container_width=True)
                        
                        st.session_state.history.append({
                            "type": "image", 
                            "prompt": user_prompt, 
                            "content": image_bytes, 
                            "time": datetime.now().strftime("%H:%M")
                        })
                    else:
                        st.error("Generation failed. Try again.")

with tab2:
    st.header("🗄️ Session History")
    if len(st.session_state.history) == 0:
        st.info("No assets generated yet.")
    for i, item in enumerate(reversed(st.session_state.history)):
        with st.expander(f"{item['time']} - {item['type'].upper()}: {item['prompt'][:50]}..."):
            if item['type'] == 'text':
                st.markdown(item['content'])
            elif item['type'] == 'image':
                img = Image.open(io.BytesIO(item['content']))
                st.image(img, use_container_width=True)
