import os
import json
import uuid
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

# Inicjalizacja bazy konwersacji
conversations = load_data()

# Zarządzanie aktywnym czatem w sesji
if "current_chat_id" not in st.session_state:
    if conversations:
        # Domyślnie wybierz pierwszą z dostępnych
        st.session_state.current_chat_id = list(conversations.keys())[0]
    else:
        # Utwórz nową, jeśli brak
        new_id = str(uuid.uuid4())[:8]
        conversations[new_id] = {"title": "Nowa konwersacja", "messages": []}
        save_data(conversations)
        st.session_state.current_chat_id = new_id

# --- PANEL BOCZNY (HISTORIA CZATÓW JAK W GEMINI) ---
with st.sidebar:
    st.header("💬 Twoje Konwersacje")
    
    if st.button("➕ Nowy czat", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        conversations[new_id] = {"title": "Nowa konwersacja", "messages": []}
        save_data(conversations)
        st.session_state.current_chat_id = new_id
        st.rerun()

    st.divider()

    # Wyświetlanie listy wszystkich konwersacji
    # Sortujemy od najnowszych (klucze lub po prostu iteracja)
    for chat_id, chat_data in list(conversations.items()):
        title = chat_data.get("title", "Konwersacja")
        # Podświetlenie aktywnego czatu
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

# Główny interfejs czatu
current_id = st.session_state.current_chat_id
if current_id not in conversations:
    # Zabezpieczenie, gdyby aktualny ID został usunięty
    current_id = list(conversations.keys())[0]
    st.session_state.current_chat_id = current_id

current_chat = conversations[current_id]

st.title("🤖 Personalny Agent AI")
st.markdown(f"Aktualny czat: **{current_chat.get('title', 'Konwersacja')}**")

# Wyświetlanie wiadomości z aktywnego czatu
for message in current_chat["messages"]:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Obsługa wpisywania wiadomości
if prompt := st.chat_input("Napisz coś do swojego agenta..."):
    # Jeśli to pierwsza wiadomość, ustaw tytuł czatu na podstawie treści promptu
    if len(current_chat["messages"]) == 0:
        current_chat["title"] = prompt[:30] + ("..." if len(prompt) > 30 else "")

    current_chat["messages"].append({"role": "user", "content": prompt})
    save_data(conversations)

    with st.chat_message("user"):
        st.markdown(prompt)

    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    messages_payload = [{"role": m["role"], "content": m["content"]} for m in current_chat["messages"]]

    with st.chat_message("assistant"):
        with st.spinner("Agent myśli..."):
            try:
                response = client.messages.create(
                    model="claude-sonnet-5-5",
                    max_tokens=1000,
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
