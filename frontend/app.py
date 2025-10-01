import streamlit as st
import requests
import bcrypt
import os
from language import LANG

# --- Load secrets ---
API_URL = st.secrets["API_URL"]
ADMIN_PASSWORD_HASH = st.secrets["ADMIN_PASSWORD_HASH"]

# --- Initialize session state ---
if "show_admin_section" not in st.session_state:
    st.session_state.show_admin_section = False
if "admin_authenticated" not in st.session_state:
    st.session_state.admin_authenticated = False

# --- Initialize chat history ---
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# --- Header with profile + language selector + admin button ---
col1, col2, col3 = st.columns([1, 3, 1])

# Language selection
selected_lang = col3.selectbox("", list(LANG.keys()), index=0, key="lang_selector")
lang = LANG[selected_lang]

# --- Page setup ---
st.set_page_config(page_title=lang["page_title"])

# Admin button in top-right: toggle show/hide admin section
if col3.button("🔒"):
    st.session_state.show_admin_section = not st.session_state.show_admin_section

with col1:
    st.image(os.path.join(os.path.dirname(__file__), "images/profile.png"), width=120)

with col2:
    st.markdown(
        f"""
        # **{lang['title']}**  
        *{lang['subtitle']}*  

        ---
        {lang['linkedin']}
        """,
        unsafe_allow_html=True
    )

# --- Helper function ---
def ask(query: str) -> str:
    with st.spinner(lang["spinner_asking"]):
        response = requests.get(f"{API_URL}/ask?query={query}")
    if response.status_code == 200:
        data = response.json()
        answer = data["answer"]
    else:
        answer = lang["ask_fallback"]

    # Save Q&A to session state
    st.session_state.chat_history.append({"role": "user", "content": query})
    st.session_state.chat_history.append({"role": "ai", "content": answer})
    return answer

# ---  Process a user query or suggested question ---
def handle_question(query: str):
    ask(query)

# --- Handle PDF uploads and send to backend, display metadata ---
def upload_documents():
    # Only allow upload if not already done
    if st.session_state.get("documents_uploaded", False):
        return

    uploaded_files = st.file_uploader(
        "Select .pdf files to upload", type="pdf", accept_multiple_files=True
    )
    if not uploaded_files:
        return

    # Display file info before uploading
    st.markdown("**Files to be uploaded:**")
    for file in uploaded_files:
        st.write(f"- {file.name} ({round(len(file.getvalue())/1024, 2)} KB)")

    files = [
        ("files", (file.name, file.getvalue(), "application/pdf"))
        for file in uploaded_files
    ]
    
    try:
        with st.spinner("Uploading files..."):
            response = requests.post(f"{API_URL}/documents/", files=files)
        if response.status_code == 200:
            st.success("Files uploaded successfully!")
            st.session_state.documents_uploaded = True  # Set flag to prevent retrigger
        else:
            st.error(f"Upload failed: {response.text}")
    except Exception as e:
        st.error(f"Error uploading files: {e}")

# --- Suggested Questions ---
st.markdown(f"### {lang['suggestions_intro']}")
cols = st.columns(len(lang["suggestions"]))
for i, question in enumerate(lang["suggestions"]):
    if cols[i].button(question):
        handle_question(question)

# --- Chat Interface ---
# Add welcome message once if chat history is empty
if not st.session_state.chat_history:
    st.session_state.chat_history.append({"role": "ai", "content": lang["welcome"]})

# --- Chat input ---
query = st.chat_input(placeholder=lang["ask_placeholder"])
if query:
    handle_question(query)

# --- Show the messages ---
for msg in st.session_state.chat_history:
    with st.chat_message(msg["role"]):
        st.write(msg["content"])

# --- Admin Section ---
if st.session_state.show_admin_section:
    # Password check if not yet authenticated
    if not st.session_state.admin_authenticated:
        password = st.text_input("Enter Password:", type="password", key="admin_pw")
        if password:
            if bcrypt.checkpw(password.encode(), ADMIN_PASSWORD_HASH.encode()):
                st.session_state.admin_authenticated = True
                st.success("Authenticated!")
            else:
                st.warning("Incorrect password")

    # Show uploader only after authentication
    if st.session_state.admin_authenticated:
        upload_documents()
