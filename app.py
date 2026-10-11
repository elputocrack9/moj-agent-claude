import os
import json
import uuid
import base64
import re
import io
import streamlit as st
import anthropic
import pandas as pd
import openpyxl

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

    for chat_id, chat_data in list(conversations.items()):
        title = chat_data.get("title", "Konwersacja")
        is_active = (chat_id == st.session_state.current_chat_id)
        
        col1, col2, col3 = st.columns([0.6, 0.2, 0.2])
        with col1:
            if st.button(title[:16] + ("..." if len(title) > 16 else ""), key=f"chat_{chat_id}", use_container_width=True, type="primary" if is_active else "secondary"):
                st.session_state.current_chat_id = chat_id
                st.rerun()
        with col2:
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

        if st.session_state.get(f"editing_{chat_id}", False):
            new_title_input = st.text_input("Nowy tytuł:", value=title, key=f"input_title_{chat_id}")
            if st.button("Zapisz tytuł", key=f"save_title_{chat_id}"):
                conversations[chat_id]["title"] = new_title_input
                save_data(conversations)
                st.session_state[f"editing_{chat_id}"] = False
                st.rerun()

    st.divider()
    st.header("⚙️ Ustawienia modelu")
    
    persona_options = {
        "Standardowy Asystent": "Jesteś pomocnym, inteligentnym agentem AI. Masz pełną pamięć o użytkowniku, w tym dostęp do wszystkich wcześniej przesłanych obrazów, dokumentów oraz treści z jego poprzednich konwersacji. Jeżeli użytkownik prosi o plik Excela, wygeneruj poprawny kod Python tworzący ten plik za pomocą openpyxl/pandas w bloku ```python.",
        "Programista Python / Excel Ekspert": "Jesteś ekspertem Pythona i analitykiem danych w Excelu. Piszesz zaawansowane skrypty, czytelny kod i tworzysz profesjonalne pliki Excela z automatycznymi formułami i formatowaniem w blokach kodu ```python.",
        "Kreatywny Copywriter": "Jesteś utalentowanym copywriterem i ekspertem od marketingu. Twoje wypowiedzi są angażujące i perswazyjne.",
        "Analityk Danych": "Jesteś precyzyjnym analitykiem danych. Skup się na logice, liczbach, strukturze oraz merytorycznym podejściu."
    }
    selected_persona = st.selectbox("Rola / Tryb agenta:", list(persona_options.keys()))
    system_prompt_base = persona_options[selected_persona]

    st.divider()
    
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

def execute_excel_code(code_str):
    try:
        local_scope = {"pd": pd, "openpyxl": openpyxl}
        exec(code_str, globals(), local_scope)
        excel_files = [f for f in os.listdir(".") if f.endswith(".xlsx")]
        if excel_files:
            latest_file = max(excel_files, key=os.path.getmtime)
            with open(latest_file, "rb") as f:
                bytes_data = f.read()
            return latest_file, bytes_data
    except Exception as e:
        st.error(f"Błąd podczas generowania pliku Excel: {e}")
    return None, None

for idx, message in enumerate(current_chat["messages"]):
    role = message["role"]
    content = message["content"]
    
    with st.chat_message(role):
        text_content = ""
        if isinstance(content, list):
            for part in content:
                if isinstance(part, dict):
                    if part.get("type") == "text":
                        text_content += part["text"] + "\n"
                        st.markdown(part["text"])
                    elif part.get("type") == "image":
                        source = part.get("source", {})
                        data_b64 = source.get("data", "")
                        media_type = source.get("media_type", "image/png")
                        st.image(f"data:{media_type};base64,{data_b64}", width=300)
                    elif part.get("type") == "document":
                        st.info("📄 [Załączony dokument PDF]")
        else:
            text_content = str(content)
            st.markdown(text_content)

        if role == "assistant" and "```python" in text_content and "xlsx" in text_content:
            code_blocks = re.findall(r"```python(.*?)```", text_content, re.DOTALL)
            for code in code_blocks:
                if ".to_excel" in code or "Workbook(" in code or "save(" in code:
                    filename, excel_bytes = execute_excel_code(code)
                    if excel_bytes:
                        st.download_button(
                            label=f"📊 Pobierz wygenerowany plik Excel ({filename})",
                            data=excel_bytes,
                            file_name=filename,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key=f"dl_excel_{current_id}_{idx}"
                        )

        col_e1, col_e2, _ = st.columns([0.1, 0.1, 0.8])
        with col_e1:
            if st.button("🗑️", key=f"del_msg_{current_id}_{idx}", help="Usuń wiadomość"):
                current_chat["messages"].pop(idx)
                save_data(conversations)
                st.rerun()
        with col_e2:
            if role == "user" and st.button("✏️", key=f"edit_msg_{current_id}_{idx}", help="Edytuj wiadomość"):
                st.session_state[f"editing_msg_{current_id}_{idx}"] = True

        if st.session_state.get(f"editing_msg_{current_id}_{idx}", False):
            edit_text = st.text_area("Edytuj treść:", value=str(content[0].get("text") if isinstance(content, list) else content), key=f"edit_input_{current_id}_{idx}")
            if st.button("Zaktualizuj i wyślij ponownie", key=f"submit_edit_{current_id}_{idx}"):
                if isinstance(content, list):
                    content[0]["text"] = edit_text
                else:
                    current_chat["messages"][idx]["content"] = edit_text
                current_chat["messages"] = current_chat["messages"][:idx+1]
                save_data(conversations)
                st.session_state[f"editing_msg_{current_id}_{idx}"] = False
                st.rerun()

uploaded_file = st.file_uploader("Załącz obraz lub plik (opcjonalnie):", type=["png", "jpg", "jpeg", "webp", "pdf", "txt", "xlsx", "csv"])
prompt = st.chat_input("Napisz coś do swojego agenta (np. 'Stwórz budżet domowy w Excelu')...")

if prompt or uploaded_file:
    user_content_blocks = []
    
    if uploaded_file is not None:
        file_bytes = uploaded_file.read()
        encoded_file = base64.b64encode(file_bytes).decode("utf-8")
        file_type = uploaded_file.type
        
        if file_type.startswith("image/"):
            user_content_blocks.append({
                "type": "image",
                "source": {"type": "base64", "media_type": file_type, "data": encoded_file}
            })
        elif file_type == "application/pdf":
            user_content_blocks.append({
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": encoded_file}
            })
        elif file_type in ["application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "text/csv"]:
            try:
                if file_type == "text/csv":
                    df = pd.read_csv(io.BytesIO(file_bytes))
                else:
                    df = pd.read_excel(io.BytesIO(file_bytes))
                csv_preview = df.head(20).to_csv(index=False)
                user_content_blocks.append({
                    "type": "text",
                    "text": f"[Użytkownik załączył plik danych '{uploaded_file.name}'. Oto pierwsze wiersze danych w formacie CSV]:\n{csv_preview}"
                })
            except Exception as ex:
                st.error(f"Nie udało się odczytać arkusza: {ex}")

    if prompt:
        user_content_blocks.append({"type": "text", "text": prompt})
    else:
        if not user_content_blocks:
            user_content_blocks.append({"type": "text", "text": "[Użytkownik załączył plik]"})

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

    full_history_payload = []
    for cid, cdata in conversations.items():
        for msg in cdata.get("messages", []):
            full_history_payload.append({
                "role": msg["role"],
                "content": msg["content"]
            })

    with st.chat_message("assistant"):
        with st.spinner("Agent analizuje i przetwarza..."):
            try:
                response = client.messages.create(
                    model="claude-3-5-sonnet-latest",
                    max_tokens=2500,
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
                st.rerun()
                
            except Exception as e:
                st.error(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
