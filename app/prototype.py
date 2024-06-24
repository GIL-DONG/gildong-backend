import streamlit as st
import requests
import os
import base64

from core import setup_logging


# Depending on the chatbot selection, set the appropriate API URL
running_in_docker = os.environ.get('RUNNING_IN_DOCKER', 'false').lower() == 'true'
host = "api" if running_in_docker else "localhost"
setup_logging("logs")

# logo_path = "core/logo.png"

st.markdown("""
    <style>
        body * {
            font-family: 'Noto Sans KR', sans-serif !important;
            font-style: normal !important;
        }
        .stButton>button {
            width: 100%; 
            margin-top: 2rem; 
            padding: 1rem 3rem; 
            font-size: 1.2rem;
        }
    </style>
    """, unsafe_allow_html=True)

# Sidebar for API Key and other references
with st.sidebar:
    # with open(logo_path, "rb") as f:
    #     data = base64.b64encode(f.read()).decode("utf-8")
    
    #     st.markdown(
    #         f"""
    #         <div style="display: table; margin-top: -20%; margin-left: 20%;">
    #             <img src="data:image/png;base64,{data}" width="150">
    #         </div>
    #         """,
    #         unsafe_allow_html=True,
    #     )
    
    # st.markdown("<br>", unsafe_allow_html=True)
    
    # Endpoint 선택
    endpoint_selection = st.selectbox(
        "Choose an Endpoint:",
        ["/detail", "/main_chatbot"]
    )
    
    chatbot_selection = st.radio(
        "Choose a Chatbot:",
        ["Data Recommendation Chatbot", "Kim Gu Chatbot"]
    )
    
    if chatbot_selection == "Data Recommendation Chatbot":
        api_url = f"http://{host}:5040{endpoint_selection}"
    else:
        api_url = f"http://{host}:5040{endpoint_selection}"
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    user_id = "test_id"

    if 'session_id' not in st.session_state:
        st.session_state.session_id = 1
    
    if st.button('+ 새로운 대화', key='new_session'):
        st.session_state.session_id += 1

st.title("💬 AI Chatbot Tester")

if 'user_input' not in st.session_state:
    st.session_state.user_input = ''

user_input = st.text_input("You:", value=st.session_state.user_input, placeholder="Ask me anything ...", key="input")

if user_input:
    st.markdown("----")
    res_box = st.empty()

    report = []

    data = {"user_id": user_id, "session_id": str(st.session_state.session_id), "content": user_input}

    with requests.post(api_url, json=data, stream=True) as r:
        for chunk in r.iter_content(1024):
            report.append(chunk.decode())
            result = "".join(report).strip()
            res_box.markdown(f'{result}')

    st.session_state.user_input = ''

st.markdown("----")