import json
from google import genai
from google.genai import types
import streamlit as st

from twilio.rest import Client as TwilioClient


GEMINI_API_KEY=st.secrets["GEMINI_API_KEY"]
TWILLIO_ACCOUNT_SID = st.secrets["TWILLIO_ACCOUNT_SID"]
TWILLIO_AUTH_TOKEN = st.secrets["TWILLIO_AUTH_TOKEN"]
TWILLIO_WHATSAPP_FROM = st.secrets["TWILLIO_WHATSAPP_FROM"] 
TWILLIO_AUTH_TOKEN = st.secrets["TWILLIO_AUTH_TOKEN"]


@st.cache_resource
def get_gemini_client():
    return genai.Client(api_key= GEMINI_API_KEY)

@st.cache_resource
def get_twilio_client():
    return TwilioClient(TWILLIO_ACCOUNT_SID, TWILLIO_AUTH_TOKEN)



twilio_client = get_twilio_client()
gemini_client = get_gemini_client()
MODEL_NAME= "gemini-3.8-flash"


def clean_whatsapp_text(text):
    if not text:
        return "No summary available."
    text =" ".join(text.split())
    return text[:1500]+"..." if len(text)>1500 else text




def send_whatsapp(to_number, user_name, summary):
    try:
        content_variables = json.dumps(
            {"1": user_name, "2": clean_whatsapp_text(summary)}, ensure_ascii=False
        )
        message = twilio_client.messages.create(
            from_ =TWILLIO_WHATSAPP_FROM,
            to = f"whatsapp:{to_number}",
            content_sid = st.secrets["TWILLIO_CONTENT_SID"],
            content_variables = content_variables,
        )
        return True, message.sid
    except Exception as error:
        return False, str(error)




from prompts import (SYSTEM_PROMPT, WELCOME_MESSAGE_TEMPLATE, SUMMARY_REQUEST_PROMPT)


def  render_message(message):
    role = message["role"]
    kind = message["kind"]
    content = message["content"]
    with st.chat_message(message["role"]):
        if message["kind"]=="text":
            st.write(message["content"])
        elif message["kind"]=="image":
            st.image(message["content"])
        

def add_message(role, kind, content):
    st.session_state.messages.append({"role": role, "kind": kind, "content": content})
    render_message(st.session_state.messages[-1])

def ask_gemini(parts): 
    try:
        return st.session_state.chat.send_message(parts).text 
    except Exception as error:
        return f"sorry, Something went wrong :{error}"   

#step1: onborading(username and phone no)

if 'onboarded' not in st.session_state:
    st.title("  Foodsnap🍛       ")
    st.caption(" Snap it📷, Track it🚇. Text yourself the results.") 

    with st.form("onboarding_form"):
        
        username = st.text_input("Enter your name:")
        whatsapp_number = st.text_input(
            "Enter your whatsapp number :", placeholder="+91XXXXXXXXXX", 
        help="This is the number foodsnap will text your summary too." \
        )
        submitted = st.form_submit_button("Submit🚀")
        if submitted:
            if not username.strip() or not whatsapp_number.strip():
                st.warning("Please fill in both your name and whatsapp number before submitting.")
            else:
                st.session_state.username = username.strip()
                st.session_state.whatsapp_number = whatsapp_number.strip()
                #activate my ai
                st.session_state.chat= gemini_client.chats.create(
                      model=MODEL_NAME,
                       config=types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT)
                      
                     )
                st.session_state.messages = []
                st.session_state.onboarded = True                                                          
                st.rerun()
        st.stop()

 #Create a chat interface

header_col, button_col= st.columns([5,2], vertical_alignment="center")
with header_col:
    st.title("  Foodsnap🍛       ")


with button_col:
   
   send_disabled= len(st.session_state.messages)<=1
   if st.button("Send details to WhatsApp📱",disabled=send_disabled,use_container_width=True):
        with st.spinner("Summarizing your day..."):
          summary = ask_gemini([SUMMARY_REQUEST_PROMPT])
        success,info= send_whatsapp(st.session_state.whatsapp_number, st.session_state.name, summary)
        if success:
             st.success("sent! check your whatsapp📱")
        else:
          st.error(f"Couldn't send that: {info}")


st.caption(f"Logged in as {st.session_state.username}- updates go to {st.session_state.whatsapp_number}")             
if not st.session_state.messages:
    add_message("assistant", "text", WELCOME_MESSAGE_TEMPLATE.format(username=st.session_state.username))
else:
    for message in st.session_state.messages:
        render_message(message)  


user_input = st.chat_input(" Ask a question , or Snap a photo or describe your meal here...",
   accept_file=True, file_type=["png", "jpg", "jpeg"],                       
)

if user_input:
    photo = user_input.files[0] if user_input.files else None
    text = user_input.text
    parts=[]
    if photo is not None:
        photo_bytes =photo.getvalue()
        add_message("user", "image", photo_bytes)
        parts.append(types.Part.from_bytes(data=photo_bytes, mime_type=photo.type))
    if text:
        add_message("user", "text", text)
        parts.append(text)  
    elif photo is not None:
        parts.append("What is this meal? Give me the calories and macros.")    

    with st.spinner("cruching the numbers..."):
        answer = ask_gemini(parts)
    add_message("assistant", "text", answer)         




