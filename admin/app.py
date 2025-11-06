"""
VANDA Chatbot - Admin Panel
Streamlit app per gestire configurazioni del chatbot
"""
import streamlit as st
import sys
import os
from datetime import datetime
import json

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.config_service import get_config_service

# Page config
st.set_page_config(
    page_title="Vanda Chatbot Admin",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        margin-bottom: 1rem;
    }
    .section-header {
        font-size: 1.5rem;
        font-weight: bold;
        color: #2c3e50;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-bottom: 2px solid #1f77b4;
        padding-bottom: 0.5rem;
    }
    .success-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d4edda;
        border: 1px solid #c3e6cb;
        color: #155724;
        margin: 1rem 0;
    }
    .error-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #f8d7da;
        border: 1px solid #f5c6cb;
        color: #721c24;
        margin: 1rem 0;
    }
    .info-box {
        padding: 1rem;
        border-radius: 0.5rem;
        background-color: #d1ecf1;
        border: 1px solid #bee5eb;
        color: #0c5460;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)


def initialize_session_state():
    """Inizializza lo stato della sessione"""
    if 'config_service' not in st.session_state:
        try:
            st.session_state.config_service = get_config_service()
            st.session_state.initialized = True
        except Exception as e:
            st.error(f"❌ Errore inizializzazione: {e}")
            st.session_state.initialized = False


def load_configs():
    """Carica tutte le configurazioni dal DB"""
    try:
        config_service = st.session_state.config_service
        return config_service.get_all_configs()
    except Exception as e:
        st.error(f"❌ Errore caricamento configurazioni: {e}")
        return {}


def main():
    """Main app function"""

    # Header
    st.markdown('<div class="main-header">🤖 Vanda Chatbot Admin Panel</div>', unsafe_allow_html=True)
    st.markdown("**Gestisci configurazioni, prompt e parametri del chatbot**")
    st.markdown("---")

    # Initialize
    initialize_session_state()

    if not st.session_state.get('initialized', False):
        st.error("❌ Impossibile connettersi al database. Verifica le variabili d'ambiente.")
        return

    # Sidebar
    with st.sidebar:
        st.title("📋 Menu")
        page = st.radio(
            "Seleziona sezione:",
            ["🏠 Dashboard", "📝 System Prompt", "🎛️ Parametri RAG", "🤖 Parametri LLM", "⚙️ Impostazioni Avanzate"],
            index=0
        )

        st.markdown("---")

        # Refresh button
        if st.button("🔄 Ricarica Configurazioni", use_container_width=True):
            st.session_state.config_service.clear_cache()
            st.rerun()

        st.markdown("---")
        st.caption(f"Ultimo aggiornamento: {datetime.now().strftime('%H:%M:%S')}")

    # Load configs
    configs = load_configs()

    # Page routing
    if page == "🏠 Dashboard":
        show_dashboard(configs)
    elif page == "📝 System Prompt":
        show_system_prompt(configs)
    elif page == "🎛️ Parametri RAG":
        show_rag_parameters(configs)
    elif page == "🤖 Parametri LLM":
        show_llm_parameters(configs)
    elif page == "⚙️ Impostazioni Avanzate":
        show_advanced_settings(configs)


def show_dashboard(configs):
    """Dashboard con overview delle configurazioni"""
    st.markdown('<div class="section-header">📊 Dashboard</div>', unsafe_allow_html=True)

    # Metrics
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Configurazioni Totali", len(configs))

    with col2:
        system_prompt = configs.get("system_prompt", {}).get("value", {})
        prompt_length = len(system_prompt.get("prompt", ""))
        st.metric("Lunghezza Prompt", f"{prompt_length} char")

    with col3:
        rag_params = configs.get("rag_parameters", {}).get("value", {})
        match_count = rag_params.get("match_count", 0)
        st.metric("RAG Match Count", match_count)

    with col4:
        llm_params = configs.get("llm_parameters", {}).get("value", {})
        model = llm_params.get("model", "N/A")
        st.metric("Modello LLM", model)

    st.markdown("---")

    # Configurazioni dettagliate
    st.subheader("📋 Configurazioni Correnti")

    for config_key, config_data in configs.items():
        with st.expander(f"**{config_key}**"):
            st.write(f"**Descrizione:** {config_data.get('description', 'N/A')}")
            st.write(f"**Ultimo aggiornamento:** {config_data.get('updated_at', 'N/A')}")
            st.write(f"**Aggiornato da:** {config_data.get('updated_by', 'N/A')}")
            st.json(config_data.get('value', {}))


def show_system_prompt(configs):
    """Editor per system prompt"""
    st.markdown('<div class="section-header">📝 System Prompt</div>', unsafe_allow_html=True)

    current_config = configs.get("system_prompt", {}).get("value", {})
    current_prompt = current_config.get("prompt", "")

    st.markdown('<div class="info-box">💡 Il system prompt definisce il comportamento e il tono del chatbot.</div>', unsafe_allow_html=True)

    # Editor
    new_prompt = st.text_area(
        "System Prompt:",
        value=current_prompt,
        height=300,
        help="Definisci come il chatbot deve comportarsi e rispondere agli utenti"
    )

    # Character count
    st.caption(f"Lunghezza: {len(new_prompt)} caratteri")

    # Preview
    with st.expander("👁️ Anteprima"):
        st.info(new_prompt)

    # Save button
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("💾 Salva", use_container_width=True):
            new_config = {"prompt": new_prompt}
            if st.session_state.config_service.update_config("system_prompt", new_config):
                st.markdown('<div class="success-box">✅ System prompt aggiornato con successo!</div>', unsafe_allow_html=True)
                st.session_state.config_service.clear_cache()
                st.rerun()
            else:
                st.markdown('<div class="error-box">❌ Errore durante il salvataggio</div>', unsafe_allow_html=True)

    with col2:
        if st.button("🔄 Reset a Default", use_container_width=True):
            default_prompt = "Sei un assistente AI per Vanda Designers, uno studio di architettura e interior design in Spagna. Rispondi in modo professionale, conciso e utile. Usa le informazioni fornite dal database per dare risposte accurate sui progetti, servizi e competenze dello studio."
            new_config = {"prompt": default_prompt}
            if st.session_state.config_service.update_config("system_prompt", new_config):
                st.markdown('<div class="success-box">✅ Reset completato!</div>', unsafe_allow_html=True)
                st.session_state.config_service.clear_cache()
                st.rerun()


def show_rag_parameters(configs):
    """Editor per parametri RAG"""
    st.markdown('<div class="section-header">🎛️ Parametri RAG</div>', unsafe_allow_html=True)

    current_config = configs.get("rag_parameters", {}).get("value", {})

    st.markdown('<div class="info-box">💡 Questi parametri controllano come il chatbot cerca e recupera informazioni dal database vettoriale.</div>', unsafe_allow_html=True)

    # Form
    with st.form("rag_form"):
        col1, col2 = st.columns(2)

        with col1:
            match_count = st.number_input(
                "Match Count",
                min_value=1,
                max_value=10,
                value=current_config.get("match_count", 3),
                help="Numero di documenti da recuperare dalla ricerca vettoriale"
            )

            match_threshold = st.slider(
                "Similarity Threshold",
                min_value=0.0,
                max_value=1.0,
                value=float(current_config.get("match_threshold", 0.60)),
                step=0.05,
                help="Soglia minima di similarità (0.60-0.75 consigliato)"
            )

        with col2:
            max_context_length = st.number_input(
                "Max Context Length",
                min_value=1000,
                max_value=16000,
                value=current_config.get("max_context_length", 8000),
                step=1000,
                help="Lunghezza massima del contesto inviato al LLM"
            )

            enable_metadata_filters = st.checkbox(
                "Abilita Filtri Metadata",
                value=current_config.get("enable_metadata_filters", True),
                help="Permette filtraggio per categoria, tipo progetto, etc."
            )

        # Submit
        submitted = st.form_submit_button("💾 Salva Configurazione", use_container_width=True)

        if submitted:
            new_config = {
                "match_count": match_count,
                "match_threshold": match_threshold,
                "max_context_length": max_context_length,
                "enable_metadata_filters": enable_metadata_filters
            }

            if st.session_state.config_service.update_config("rag_parameters", new_config):
                st.markdown('<div class="success-box">✅ Parametri RAG aggiornati!</div>', unsafe_allow_html=True)
                st.session_state.config_service.clear_cache()
                st.rerun()
            else:
                st.markdown('<div class="error-box">❌ Errore durante il salvataggio</div>', unsafe_allow_html=True)


def show_llm_parameters(configs):
    """Editor per parametri LLM"""
    st.markdown('<div class="section-header">🤖 Parametri LLM</div>', unsafe_allow_html=True)

    current_config = configs.get("llm_parameters", {}).get("value", {})

    st.markdown('<div class="info-box">💡 Questi parametri controllano il modello OpenAI e come genera le risposte.</div>', unsafe_allow_html=True)

    # Form
    with st.form("llm_form"):
        col1, col2 = st.columns(2)

        with col1:
            model = st.selectbox(
                "Modello OpenAI",
                options=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
                index=["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"].index(current_config.get("model", "gpt-4o-mini")),
                help="Modello da utilizzare per generare risposte"
            )

            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=2.0,
                value=float(current_config.get("temperature", 0.5)),
                step=0.1,
                help="Creatività delle risposte (0.0 = deterministico, 2.0 = molto creativo)"
            )

        with col2:
            max_tokens = st.number_input(
                "Max Tokens",
                min_value=100,
                max_value=4000,
                value=current_config.get("max_tokens", 500),
                step=100,
                help="Lunghezza massima della risposta"
            )

            stream_enabled = st.checkbox(
                "Streaming Abilitato",
                value=current_config.get("stream_enabled", True),
                help="Abilita streaming SSE per risposte in tempo reale"
            )

        # Submit
        submitted = st.form_submit_button("💾 Salva Configurazione", use_container_width=True)

        if submitted:
            new_config = {
                "model": model,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stream_enabled": stream_enabled
            }

            if st.session_state.config_service.update_config("llm_parameters", new_config):
                st.markdown('<div class="success-box">✅ Parametri LLM aggiornati!</div>', unsafe_allow_html=True)
                st.session_state.config_service.clear_cache()
                st.rerun()
            else:
                st.markdown('<div class="error-box">❌ Errore durante il salvataggio</div>', unsafe_allow_html=True)


def show_advanced_settings(configs):
    """Editor per impostazioni avanzate"""
    st.markdown('<div class="section-header">⚙️ Impostazioni Avanzate</div>', unsafe_allow_html=True)

    current_config = configs.get("advanced_settings", {}).get("value", {})

    st.markdown('<div class="info-box">💡 Configurazioni avanzate per performance e funzionalità del chatbot.</div>', unsafe_allow_html=True)

    # Form
    with st.form("advanced_form"):
        cache_ttl = st.number_input(
            "Cache TTL (secondi)",
            min_value=60,
            max_value=3600,
            value=current_config.get("cache_ttl_seconds", 300),
            step=60,
            help="Durata della cache per le configurazioni"
        )

        enable_memory = st.checkbox(
            "Abilita Conversation Memory",
            value=current_config.get("enable_conversation_memory", True),
            help="Salva e recupera la cronologia delle conversazioni"
        )

        max_history = st.number_input(
            "Max History Messages",
            min_value=5,
            max_value=50,
            value=current_config.get("max_history_messages", 10),
            help="Numero massimo di messaggi da mantenere in memoria"
        )

        # Submit
        submitted = st.form_submit_button("💾 Salva Configurazione", use_container_width=True)

        if submitted:
            new_config = {
                "cache_ttl_seconds": cache_ttl,
                "enable_conversation_memory": enable_memory,
                "max_history_messages": max_history
            }

            if st.session_state.config_service.update_config("advanced_settings", new_config):
                st.markdown('<div class="success-box">✅ Impostazioni avanzate aggiornate!</div>', unsafe_allow_html=True)
                st.session_state.config_service.clear_cache()
                st.rerun()
            else:
                st.markdown('<div class="error-box">❌ Errore durante il salvataggio</div>', unsafe_allow_html=True)


if __name__ == "__main__":
    main()
