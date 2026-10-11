import os
import json
import streamlit as st
import anthropic

st.set_page_config(page_title="Personalny Agent AI", page_icon="🤖")

st.title("🤖 Personalny Agent AI")
st.markdown("Model: Claude Sonnet 5.5 | Pamięć: Trwała (JSON)")

# Ścieżka do pliku z pamięcią trwałą
MEMORY_FILE = os.path.join(os.path.dirname(__file__), "user_memory.json")

def load_memories():
    if os.path.exists(MEMORY_FILE):
        try:
            with open(MEMORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def save_memory(fact):
    memories = load_memories()
    if fact not in memories:
        memories.append(fact)
        try:
            with open(MEMORY_FILE, "w", encoding="utf-8") as f:
                json.dump(memories, f, ensure_ascii=False, indent=2)
        except Exception as e:
            st.error(f"Błąd zapisu pamięci: {e}")

# Historia czatu w sesji Streamlita
if "messages" not in st.session_state:
    st.session_state.messages = []

# Wyświetlanie historii
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Obsługa wiadomości
if prompt := st.chat_input("Napisz coś do swojego agenta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Automatyczne wyciąganie prostych faktów lub zapisywanie wypowiedzi użytkownika do pamięci
    # Jeśli użytkownik podaje informację (np. "Mam na imię...", "Moja narzeczona..."), zapisujemy ją
    lower_prompt = prompt.lower()
    if any(keyword in lower_prompt for keyword in ["mam na imię", "nazywam się", "narzeczona", "dziewczyna", "żona", "mieszkam", "lat", "urodziła", "pracuję", "lubię"]):
        save_memory(prompt)

    # Pobieramy całą zgromadzoną pamięć trwale zapisaną w pliku
    saved_facts = load_memories()
    context_str = "\n".join([f"- {fact}" for fact in saved_facts]) if saved_facts else "Brak zapisanych faktów."

    # Klient Anthropic
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = f"""Jesteś pomocnym, spersonalizowanym agentem AI. 
    Oto fakty z pamięci długoterminowej o użytkowniku, które musisz bezwzględnie pamiętać i wykorzystywać:
    {context_str}
    """

    messages_payload = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

    with st.chat_message("assistant"):
        with st.spinner("Agent myśli..."):
            try:
                response = client.messages.create(
                    model="claude-sonnet-5-5",
                    max_tokens=1000,
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
                st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
                
            except Exception as e:
                st.error(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
