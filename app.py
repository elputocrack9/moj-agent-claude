import os
import streamlit as st
from anthropic import Anthropic
from mem0 import Memory

# 1. Ustawienia wyglądu aplikacji mobilnej
st.set_page_config(page_title="Mój Agent Claude", page_icon="🤖", layout="centered")
st.title("🤖 Personalny Agent AI")
st.caption("Model: Claude Sonnet | Pamięć: Mem0")

# 2. Pobranie klucza API ze zmiennych środowiskowych
api_key = os.environ.get("ANTHROPIC_API_KEY")

if not api_key:
    st.error("⚠️ Brak klucza ANTHROPIC_API_KEY! Dodaj go w panelu Streamlit Cloud.")
    st.stop()

# 3. Inicjalizacja połączenia z API i Pamięcią
@st.cache_resource
def init_agent():
    client = Anthropic(api_key=api_key)
    mem = Memory()
    return client, mem

anthropic_client, memory = init_agent()
USER_ID = "glowny_uzytkownik"

# 4. Historia rozmowy w bieżącej sesji
if "messages" not in st.session_state:
    st.session_state.messages = []

# Wyświetlanie czatu na ekranie
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 5. Reakcja na wpisanie wiadomości przez użytkownika
if prompt := st.chat_input("Napisz do agenta..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # A. Przeszukiwanie pamięci długoterminowej
    with st.spinner("Szukam w pamięci..."):
        relevant_memories = memory.search(query=prompt, user_id=USER_ID)
        kontekst_pamieci = ""
        if relevant_memories and "results" in relevant_memories:
            fakty = [m["memory"] for m in relevant_memories["results"]]
            if fakty:
                kontekst_pamieci = "\n".join(f"- {f}" for f in fakty)

    # B. Instrukcja główna (Prompt Systemowy)
    system_prompt = (
        "Jesteś prywatnym, inteligentnym asystentem osobistym.\n"
        "Pomagasz użytkownikowi w codziennych zadaniach, researchu i analizach.\n"
        "Masz dostęp do pamięci długoterminowej z Waszych poprzednich rozmów.\n\n"
        f"FAKTY Z PAMIĘCI DŁUGOTERMINOWEJ O UŻYTKOWNIKU:\n{kontekst_pamieci if kontekst_pamieci else 'Brak zapisanych wcześniejszych faktów.'}\n\n"
        "Wykorzystuj tę wiedzę w sposób naturalny i pomocny."
    )

    # C. Wywołanie najnowszego modelu Sonnet z API
    with st.chat_message("assistant"):
        with st.spinner("Claude odpowiada..."):
            response = anthropic_client.messages.create(
                model="claude-3-5-sonnet-latest",  # Wskazuje zawsze na najnowszy stablilny Sonnet
                max_tokens=2000,
                system=system_prompt,
                messages=[{"role": "user", "content": prompt}]
            )
            answer = response.content[0].text
            st.markdown(answer)

    # D. Zapis do bieżącej sesji i nowej pamięci Mem0
    st.session_state.messages.append({"role": "assistant", "content": answer})
    
    memory.add(
        messages=[
            {"role": "user", "content": prompt},
            {"role": "assistant", "content": answer}
        ],
        user_id=USER_ID
    )