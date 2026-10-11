import os
import streamlit as st
import anthropic
from mem0 import Memory

st.set_page_config(page_title="Personalny Agent AI", page_icon="🤖")

st.title("🤖 Personalny Agent AI")
st.markdown("Model: Claude 3.5 Sonnet | Pamięć: Mem0 (Lokalna)")

# Inicjalizacja Mem0 z ChromaDB i stabilnym modelem Claude
@st.cache_resource
def init_agent():
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    
    config = {
        "llm": {
            "provider": "anthropic",
            "config": {
                "model": "claude-3-5-sonnet-20241022",
                "api_key": api_key
            }
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": "sentence-transformers/all-MiniLM-L6-v2"
            }
        },
        "vector_store": {
            "provider": "chroma",
            "config": {
                "collection_name": "memories",
                "path": "/tmp/chroma_db"
            }
        }
    }
    
    return Memory.from_config(config)

try:
    memory = init_agent()
except Exception as e:
    st.error(f"Błąd inicjalizacji pamięci: {e}")
    st.stop()

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

    user_id = "default_user"
    
    # Przeszukiwanie pamięci Mem0
    try:
        related_memories = memory.search(query=prompt, user_id=user_id)
        if isinstance(related_memories, dict) and "results" in related_memories:
            mem_list = related_memories["results"]
        else:
            mem_list = related_memories if isinstance(related_memories, list) else []
        context_str = "\n".join([m['memory'] for m in mem_list if isinstance(m, dict) and 'memory' in m]) if mem_list else "Brak wcześniejszych wspomnień."
    except Exception:
        context_str = "Brak wcześniejszych wspomnień."

    # Klient Anthropic
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = f"""Jesteś pomocnym, spersonalizowanym agentem AI. 
    Oto fakty z pamięci długoterminowej o użytkowniku:
    {context_str}
    """

    messages_payload = [{"role": m["role"], "content": m["content"]} for m in st.session_state.messages]

    with st.chat_message("assistant"):
        with st.spinner("Agent myśli..."):
            try:
                response = client.messages.create(
                    model="claude-3-5-sonnet-20241022",
                    max_tokens=1000,
                    system=system_prompt,
                    messages=messages_payload
                )
                assistant_reply = response.content[0].text
                st.markdown(assistant_reply)
                
                # Zapis do pamięci
                memory.add(messages=[{"role": "user", "content": prompt}, {"role": "assistant", "content": assistant_reply}], user_id=user_id)
                
                st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
            except Exception as e:
                st.error(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
