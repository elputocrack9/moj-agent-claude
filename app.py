import os
import streamlit as st
import anthropic
from mem0 import Memory

st.set_page_config(page_title="Personalny Agent AI", page_icon="🤖")

st.title("🤖 Personalny Agent AI")
st.markdown("Model: Claude Sonnet 5.5 | Pamięć: Mem0 (Trwała z Debugiem)")

# Inicjalizacja Mem0 ze stałą ścieżką bazy ChromaDB w folderze projektu
@st.cache_resource
def init_agent():
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    db_path = os.path.join(os.path.dirname(__file__), "chroma_db")
    
    config = {
        "llm": {
            "provider": "anthropic",
            "config": {
                "model": "claude-sonnet-5-5",
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
                "path": db_path
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
    
    # Pobieranie WSZYSTKICH wspomnień dla użytkownika (eliminuje problem niedopasowania query w search)
    context_str = "Brak wcześniejszych wspomnień."
    try:
        all_memories = memory.get_all(user_id=user_id)
        # mem0 get_all zwraca zwykle listę słowników lub obiekt z kluczem
        mem_list = []
        if isinstance(all_memories, dict):
            mem_list = all_memories.get("results", []) or all_memories.get("memories", [])
        elif isinstance(all_memories, list):
            mem_list = all_memories
            
        facts = []
        for m in mem_list:
            if isinstance(m, dict) and 'memory' in m:
                facts.append(m['memory'])
            elif hasattr(m, 'memory'):
                facts.append(m.memory)
                
        if facts:
            context_str = "\n".join([f"- {f}" for f in facts])
    except Exception as err:
        # Fallback do standardowego search
        try:
            related = memory.search(query=prompt, user_id=user_id)
            mem_list = related.get("results", []) if isinstance(related, dict) else related
            facts = [m.get('memory', '') for m in mem_list if isinstance(m, dict) and 'memory' in m]
            if facts:
                context_str = "\n".join([f"- {f}" for f in facts])
        except Exception:
            pass

    # Klient Anthropic
    api_key = st.secrets.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_API_KEY")
    client = anthropic.Anthropic(api_key=api_key)

    system_prompt = f"""Jesteś pomocnym, spersonalizowanym agentem AI. 
    Wykorzystaj poniższe fakty z pamięci długoterminowej o użytkowniku, aby odpowiadać spersonalizowanie:
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
                
                # Zapis do pamięci trwałej
                memory.add(messages=[{"role": "user", "content": prompt}, {"role": "assistant", "content": assistant_reply}], user_id=user_id)
                
                st.session_state.messages.append({"role": "assistant", "content": assistant_reply})
            except Exception as e:
                st.error(f"Wystąpił błąd podczas generowania odpowiedzi: {e}")
