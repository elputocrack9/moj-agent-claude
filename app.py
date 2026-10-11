import os
import json
import uuid
import base64
import streamlit as st
import anthropic

st.set_page_config(page_title="Personalny Agent AI", page_icon="🤖", layout="wide")

DB_FILE = os.path.join(os.path.dirname(__file__), "conversations.json")

def load_data():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def save_data(data):
    try:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        st.error(f"Błąd zapisu danych: {e}")

conversations = load_data()

if "current_chat_id" not in st.session_state:
    if conversations:
        st.session_state.current_chat_id = list(conversations.keys())[0]
    else:
        new_id = str(uuid.uuid4())[:8]
        conversations[new_id] = {"title": "Nowa konwersacja", "messages": []}
        save_data(conversations)
        st.session_state.current_chat_id = new_id

# --- PANEL BOCZNY ---
with st.sidebar:
    st.header("💬 Twoje Konwersacje")
    
    if st.button("➕ Nowy czat", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        conversations[new_id] = {"title": "Nowa konwersacja", "messages": []}
        save_data(conversations)
        st.session_state.current_chat_id = new_id
        st.rerun()

    st.divider()

    for chat_id, chat_data in list(conversations.items()):
        title = chat_data.get("title", "Konwersacja")
        is_active = (chat_id == st.session_state.current_chat_id)
        
        col1, col2 = st.columns([0.8, 0.2])
        with col1:
            if st.button(title, key=f"chat_{chat_id}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.current_chat_id = chat_id
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{chat_id}"):
                if chat_id in conversations:
                    del conversations[chat_id]
                    save_data(conversations)
                    if conversations:
                        st.session_state.current_chat_id = list(conversations.keys())[0]
                    else:
                        new_id = str(uuid.uuid4())[:8]
                        conversations[new_id] = {"title": "Nowa konwersacja", "messages": []}
                        save_data(conversations)
                        st.session_state.current_chat_id = new_id
                    st.rerun()

current_id = st.session_state.current_chat_id
if current_id not in conversations:
    current_id = list(conversations.keys())[0]
    st.session_state.current_chat_id = current_id

current_chat = conversations[current_id]

st.title("🤖 Personalny Agent AI")
st.markdown(f"Aktualny czat: **{current_chat.get('title', 'Konwersacja')}**")

# Wyświetlanie wiadomości z bieżącego czatu
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        content = message["content"]
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        st.markdown(part["text"])
                    elif part.get("type") == "image":
                        source = part.get("source", {})
                        data_b64 = source.get("data", "")
                        media_type = source.get("media_type", "image/png")
                        st.image(f"data:{media_type};base64,{data_b64}", width=300)
        else:
            st.markdown(str(content))

# --- SEKCJA INPUTU I ZAŁĄCZNIKÓW ---
uploaded_file = st.file_uploader("Załącz obraz lub plik (opcjonalnie):", type=["png", "jpg", "jpeg", "webp", "pdf", "txt"])
prompt = st.chat_input("Napisz coś do swojego agenta...")

if prompt or uploaded_file:
    user_content_blocks = []
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        encoded_file = base64.b64encode(file_bytes).decode("utf-8")
        file_type = uploaded_file.type
        
        if file_type.startswith("image/"):
            user_content_blocks.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": file_type,
                    "data": encoded_file,
                }
            })
        elif file_type == "application/pdf":
            user_content_blocks.append({
                "type": "document",
                "source": {
                    "type": "base64",
                    "media_type": "application/pdf",
                    "data": encoded_file
                }
            })

    if prompt:
        user_content_blocks.append({
            "type": "text",
            "text": prompt
        })
    else:
        user_content_blocks.append({
            "type": "text",
            "text": "[Użytkownik załączył plik]"
        })

    if len(current_chat["messages"]) == 0:
        title_text = prompt if prompt else "Załącznik"
        current_chat["title"] = title_text[:30] + ("..." if len(title_text) > 30 else "")

    current_chat["messages"].append({"role": "user", "content": user_content_blocks})
    save_data(conversations)

    with st.chat_message("user"):
        if prompt:
            st.markdown(prompt)
        if uploaded_file is not None and uploaded_file.type.startswith("image/"):
            st.image(uploaded_file, width=300)

    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    # --- KLUCZOWA ZMIANA: ZBIERANIE HISTORI ZE WSZYSTKICH CZATÓW JAKO KONTEKST ---
    global_history_summary = "Oto podsumowanie/historia wcześniejszych rozmów z użytkownikiem we wszystkich wątkach:\n"
    for cid, cdata in conversations.items():
        if cid != current_id and cdata.get("messages"):
            global_history_summary += f"\n--- Wątek: {cdata.get('title', 'Czat')} ---\n"
            for msg in cdata["messages"]:
                role = msg["role"]
                content = msg["content"]
                # Wyciągamy sam tekst do pamięci długoterminowej między wątkami
                text_snippet = ""
                if isinstance(content, list):
                    for part in content:
                        if isinstance(part, dict) and part.get("type") == "text":
                            text_snippet += part.get("text", "") + " "
                else:
                    text_snippet = str(content)
                global_history_summary += f"{role}: {text_snippet.strip()}\n"

    system_prompt = f"""Jesteś pomocnym, inteligentnym agentem AI. Masz pełną pamięć o użytkowniku z jego poprzednich konwersacji w innych wątkach. Wykorzystuj te informacje naturalnie w odpowiedziach:
    
    {global_history_summary}
    """

    # Payload bieżącego czatu
    messages_payload = [{"role": m["role"], "content": m["content"]} for m in current_chat["messages"]]

    with st.chat_message("assistant"):
        with st.spinner("Agent analizuje..."):
            try:
                response = client.messages.create(
                    model="claude-sonnet-5-5",
                    max_tokens=1500,
                    system=system_prompt,
                    messages=messages_payload
                )
                
                assistant_reply = ""
                for content_block in response.content:
                    if hasattr(content_block, "text"):
                        assistant_reply += content_block.text
                
                if not assistant_reply:
                    assistant_reply = str(response.content)

                st.markdown(assistant_reply)
                
                current_chat["messages"].append({"role": "assistant", "content": assistant_reply})
                save_data(conversations)
                
            except Exception as e:
                st.error(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
