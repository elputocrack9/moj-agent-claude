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

# --- PANEL BOCZNY: ZARZĄDZANIE, USTAWIENIA I EKSPORT ---
with st.sidebar:
    st.header("💬 Twoje Konwersacje")
    
    if st.button("➕ Nowy czat", use_container_width=True):
        new_id = str(uuid.uuid4())[:8]
        conversations[new_id] = {"title": "Nowa konwersacja", "messages": []}
        save_data(conversations)
        st.session_state.current_chat_id = new_id
        st.rerun()

    st.divider()

    # Lista konwersacji z opcją zmiany nazwy i usuwania
    for chat_id, chat_data in list(conversations.items()):
        title = chat_data.get("title", "Konwersacja")
        is_active = (chat_id == st.session_state.current_chat_id)
        
        col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
        with col1:
            if st.button(title[:16] + ("..." if len(title) > 16 else ""), key=f"chat_{chat_id}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.current_chat_id = chat_id
                st.rerun()
        with col2:
            # Przycisk edycji nazwy
            if st.button("✏️", key=f"rename_{chat_id}", help="Zmień tytuł"):
                st.session_state[f"editing_{chat_id}"] = not st.session_state.get(f"editing_{chat_id}", False)
                st.rerun()
        with col3:
            if st.button("🗑️", key=f"del_{chat_id}", help="Usuń czat"):
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

        # Input do zmiany tytułu, jeśli włączony
        if st.session_state.get(f"editing_{chat_id}", False):
            new_title_input = st.text_input("Nowy tytuł:", value=title, key=f"input_title_{chat_id}")
            if st.button("Zapisz tytuł", key=f"save_title_{chat_id}"):
                conversations[chat_id]["title"] = new_title_input
                save_data(conversations)
                st.session_state[f"editing_{chat_id}"] = False
                st.rerun()

    st.divider()
    st.header("⚙️ Ustawienia modelu")
    
    # Wybór Persony / Roli systemowej
    persona_options = {
        "Standardowy Asystent": "Jesteś pomocnym, inteligentnym agentem AI. Masz pełną pamięć o użytkowniku, w tym dostęp do wszystkich wcześniej przesłanych obrazów, dokumentów oraz treści z jego poprzednich konwersacji we wszystkich wątkach.",
        "Programista Python / Ekspert": "Jesteś doświadczonym Inżynorem Oprogramowania i ekspertem Pythona. Pisz czysty, wydajny kod, tłumacz zagadnienia techniczne wprost i pamiętaj o kontekście użytkownika z poprzednich sesji.",
        "Kreatywny Copywriter": "Jesteś utalentowanym copywriterem i ekspertem od marketingu. Twoje wypowiedzi są angażujące, perswazyjne i doskonale sformatowane.",
        "Analityk Danych": "Jesteś precyzyjnym analitykiem danych. Skup się na logice, liczbach, strukturze oraz merytorycznym podejściu do problemów użytkownika."
    }
    selected_persona = st.selectbox("Rola / Tryb agenta:", list(persona_options.keys()))
    system_prompt_base = persona_options[selected_persona]

    # Suwak temperatury (kreatywność)
    temperature = st.slider("Temperatura (Kreatywność):", min_value=0.0, max_value=1.0, value=0.7, step=0.1)

    st.divider()
    
    # Przycisk eksportu bieżącego czatu
    current_id = st.session_state.current_chat_id
    if current_id in conversations:
        current_chat_export = conversations[current_id]
        export_text = f"# Czat: {current_chat_export.get('title', 'Konwersacja')}\n\n"
        for m in current_chat_export.get("messages", []):
            role = "Użytkownik" if m["role"] == "user" else "Asystent"
            content = m["content"]
            txt = ""
            if isinstance(content, list):
                for p in content:
                    if isinstance(p, dict) and p.get("type") == "text":
                        txt += p.get("text", "") + " "
            else:
                txt = str(content)
            export_text += f"**{role}:** {txt.strip()}\n\n"
            
        st.download_button(
            label="📥 Eksportuj czat (Markdown)",
            data=export_text,
            file_name=f"chat_{current_id}.md",
            mime="text/markdown",
            use_container_width=True
        )

# Walidacja aktywnego ID
current_id = st.session_state.current_chat_id
if current_id not in conversations:
    current_id = list(conversations.keys())[0]
    st.session_state.current_chat_id = current_id

current_chat = conversations[current_id]

st.title("🤖 Personalny Agent AI")
st.markdown(f"Aktualny czat: **{current_chat.get('title', 'Konwersacja')}** | Tryb: *{selected_persona}*")

# --- WYŚWIETLANIE WIADOMOŚCI Z OPCJĄ EDYCJI / USUNIĘCIA ---
for idx, message in enumerate(current_chat["messages"]):
    role = message["role"]
    content = message["content"]
    
    with st.chat_message(role):
        # Renderowanie zawartości
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
                    elif part.get("type") == "document":
                        st.info("📄 [Załączony dokument PDF]")
        else:
            st.markdown(str(content))

        # Przyciski zarządzania pojedynczą wiadomością (Edycja / Usunięcie)
        col_e1, col_e2, col_e3 = st.columns([0.1, 0.1, 0.8])
        with col_e1:
            if st.button("🗑️", key=f"del_msg_{current_id}_{idx}", help="Usuń tę wiadomość"):
                current_chat["messages"].pop(idx)
                save_data(conversations)
                st.rerun()
        with col_e2:
            if role == "user" and st.button("✏️", key=f"edit_msg_{current_id}_{idx}", help="Edytuj tę wiadomość"):
                st.session_state[f"editing_msg_{current_id}_{idx}"] = True

        # Formularz edycji treści wiadomości użytkownika
        if st.session_state.get(f"editing_msg_{current_id}_{idx}", False):
            edit_text = st.text_area("Edytuj treść:", value=str(content[0].get("text") if isinstance(content, list) else content), key=f"edit_input_{current_id}_{idx}")
            if st.button("Zaktualizuj i wyślij ponownie", key=f"submit_edit_{current_id}_{idx}"):
                # Obcinamy historię od tego momentu i nadpisujemy prompt
                if isinstance(content, list):
                    content[0]["text"] = edit_text
                else:
                    current_chat["messages"][idx]["content"] = edit_text
                
                # Usuwamy wszystko po tej wiadomości, aby wygenerować nową odpowiedź
                current_chat["messages"] = current_chat["messages"][:idx+1]
                save_data(conversations)
                st.session_state[f"editing_msg_{current_id}_{idx}"] = False
                st.rerun()

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

    # Budowanie pełnego payloadu ze wszystkich wątków (multimodalna pamięć globalna)
    full_history_payload = []
    for cid, cdata in conversations.items():
        for msg in cdata.get("messages", []):
            full_history_payload.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    with st.chat_message("assistant"):
        with st.spinner("Agent analizuje..."):
            try:
                response = client.messages.create(
                    model="claude-sonnet-5-5",
                    max_tokens=1500,
                    temperature=temperature,
                    system=system_prompt_base,
                    messages=full_history_payload
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
