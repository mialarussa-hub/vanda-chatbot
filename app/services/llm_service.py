"""
LLM Service per VANDA chatbot.

Gestisce:
- Generazione risposte usando OpenAI GPT-4
- Streaming responses con Server-Sent Events (SSE)
- Gestione conversation history (ultimi 10 messaggi)
- Token counting e usage tracking
- Error handling robusto per OpenAI API
- Integration con RAG context
"""

from openai import OpenAI, APIError, APITimeoutError, RateLimitError
from app.config import settings
from app.models.schemas import Message, MessageRole, DocumentChunk
from app.services.config_service import get_config_service
from typing import List, Optional, Dict, Any, Generator
from loguru import logger
import tiktoken
import time


class LLMService:
    """
    Servizio per generazione risposte LLM usando OpenAI.

    Gestisce sia risposte standard che streaming con SSE per un'esperienza
    utente fluida e real-time.
    """

    # System prompt ottimizzato per Vanda Designers chatbot
    SYSTEM_PROMPT = """Sei l'assistente virtuale di Vanda Designers, uno studio specializzato in architettura e interior design con sede in Spagna.

Il tuo compito è aiutare i visitatori del sito web a:
- Scoprire i progetti dello studio (residenziali, commerciali, hospitality, retail)
- Rispondere a domande su servizi, approccio progettuale e portfolio
- Guidare gli utenti verso il contatto con lo studio per preventivi o collaborazioni

## Tono e Stile
- Usa un tono amichevole, professionale ma accessibile
- Sii entusiasta quando parli dei progetti (senza esagerare)
- Evita un linguaggio troppo tecnico, rendilo comprensibile a tutti
- Mantieni le risposte concise ma complete (2-4 paragrafi)
- Usa emoji solo se appropriato al contesto (max 1-2 per messaggio)

## Conoscenze e Comportamento
- Hai accesso a informazioni reali sui progetti Vanda attraverso documenti recuperati dal database
- Quando rispondi, UTILIZZA SEMPRE le informazioni fornite nel [CONTEXT] sotto
- Se le informazioni richieste NON sono nel context, dillo onestamente: "Non ho informazioni specifiche su questo, ma ti consiglio di contattare direttamente lo studio"
- NON inventare progetti, clienti, o dettagli che non sono nel context
- Puoi fare riferimenti generali su tendenze di design o architettura, ma sempre in relazione a Vanda

## Quando Rispondere
- Rispondi in ITALIANO (la maggior parte degli utenti parla italiano)
- Se l'utente scrive in un'altra lingua, rispondi nella stessa lingua
- Mantieni la coerenza con la conversazione precedente

## Quando Escalare
- Se l'utente chiede un preventivo dettagliato o vuole iniziare un progetto: suggerisci di contattare lo studio via email/form
- Se l'utente chiede informazioni tecniche molto specifiche (materiali, costi esatti, tempistiche): invita al contatto diretto

## Gestione Sources
- Quando menzioni un progetto specifico, fai riferimento naturale al nome del progetto se disponibile
- Non dire esplicitamente "secondo il documento X" ma integra le informazioni in modo fluido

Ricorda: sei un ambassador dello studio, trasmetti la passione e l'expertise di Vanda Designers!"""

    def __init__(self):
        """
        Inizializza client OpenAI e configurazioni LLM.

        Raises:
            Exception: Se la connessione a OpenAI fallisce
        """
        try:
            self.client = OpenAI(api_key=settings.OPENAI_API_KEY)

            # Carica configurazioni dinamiche da DB (con fallback a settings)
            self._load_dynamic_config()

            # Inizializza tokenizer per conteggio token
            try:
                self.tokenizer = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # Fallback per modelli non supportati da tiktoken
                logger.warning(f"Model {self.model} not in tiktoken, using cl100k_base")
                self.tokenizer = tiktoken.get_encoding("cl100k_base")

            logger.info(
                f"LLM Service initialized - Model: {self.model}, "
                f"Temp: {self.temperature}, Max tokens: {self.max_tokens}"
            )

        except Exception as e:
            logger.error(f"Failed to initialize LLM Service: {e}")
            raise

    def _load_dynamic_config(self):
        """Carica configurazioni dinamiche da DB con fallback a settings"""
        try:
            config_service = get_config_service()

            # Carica system prompt
            self.system_prompt = config_service.get_system_prompt()
            if not self.system_prompt:
                # Fallback al SYSTEM_PROMPT hardcoded
                self.system_prompt = self.SYSTEM_PROMPT
                logger.warning("Using hardcoded SYSTEM_PROMPT as fallback")

            # Carica parametri LLM
            llm_params = config_service.get_llm_parameters()
            self.model = llm_params.get("model", settings.LLM_DEFAULT_MODEL)
            self.temperature = llm_params.get("temperature", settings.LLM_DEFAULT_TEMPERATURE)
            self.max_tokens = llm_params.get("max_tokens", settings.LLM_MAX_TOKENS)
            self.stream_enabled = llm_params.get("stream_enabled", settings.LLM_STREAM_ENABLED)

            # Carica impostazioni avanzate
            advanced = config_service.get_advanced_settings()
            self.max_history_messages = advanced.get("max_history_messages", 10)
            self.max_context_tokens = 6000  # Fisso per ora

            logger.info("Dynamic configuration loaded from DB")

        except Exception as e:
            logger.warning(f"Failed to load dynamic config, using settings fallback: {e}")
            # Fallback completo a settings
            self.system_prompt = self.SYSTEM_PROMPT
            self.model = settings.LLM_DEFAULT_MODEL
            self.temperature = settings.LLM_DEFAULT_TEMPERATURE
            self.max_tokens = settings.LLM_MAX_TOKENS
            self.stream_enabled = settings.LLM_STREAM_ENABLED
            self.max_history_messages = 10
            self.max_context_tokens = 6000

    def generate_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Message]] = None,
        rag_context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Genera risposta LLM standard (non-streaming).

        Questo metodo:
        1. Costruisce la lista messaggi con system prompt, history e context RAG
        2. Chiama OpenAI Chat Completions API
        3. Ritorna risposta + metadata (tokens, timing)

        Args:
            user_message: Messaggio utente corrente
            conversation_history: Storia conversazione (ultimi N messaggi)
            rag_context: Context RAG formattato con documenti rilevanti
            temperature: Override temperature (default: da settings)
            max_tokens: Override max tokens (default: da settings)

        Returns:
            Dictionary con:
            - response: str (risposta generata)
            - tokens_used: int (token consumati)
            - model: str (modello usato)
            - processing_time_ms: float (tempo elaborazione)

        Raises:
            Exception: Se la generazione fallisce
        """
        try:
            start_time = time.time()

            # Usa valori di default se non specificati
            temp = temperature if temperature is not None else self.temperature
            max_tok = max_tokens if max_tokens is not None else self.max_tokens

            # Costruisci lista messaggi
            messages = self._build_messages(
                user_message=user_message,
                conversation_history=conversation_history,
                rag_context=rag_context
            )

            # Log token count per debug
            total_tokens = self._count_messages_tokens(messages)
            logger.debug(f"Total input tokens: {total_tokens}")

            logger.info(
                f"Generating response - Model: {self.model}, "
                f"Temp: {temp}, Max tokens: {max_tok}"
            )

            # Chiama OpenAI API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
                stream=False
            )

            # Estrai risposta e metadata
            assistant_message = response.choices[0].message.content
            tokens_used = response.usage.total_tokens if response.usage else None

            processing_time = (time.time() - start_time) * 1000  # Convert to ms

            logger.info(
                f"Response generated - Tokens: {tokens_used}, "
                f"Time: {processing_time:.2f}ms"
            )

            return {
                "response": assistant_message,
                "tokens_used": tokens_used,
                "model": self.model,
                "processing_time_ms": round(processing_time, 2)
            }

        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded: {e}")
            raise Exception("Troppe richieste in corso. Riprova tra qualche secondo.")

        except APITimeoutError as e:
            logger.error(f"OpenAI API timeout: {e}")
            raise Exception("Il servizio sta impiegando troppo tempo. Riprova.")

        except APIError as e:
            logger.error(f"OpenAI API error: {e}")
            raise Exception(f"Errore del servizio AI: {str(e)}")

        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def generate_streaming_response(
        self,
        user_message: str,
        conversation_history: Optional[List[Message]] = None,
        rag_context: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None
    ) -> Generator[str, None, None]:
        """
        Genera risposta LLM in streaming (Server-Sent Events).

        Questo metodo usa un generator Python per yielddare token incrementali
        man mano che arrivano da OpenAI. Ideale per UI real-time.

        Il generator yielda stringhe in formato SSE:
        - "data: {token}\n\n" per ogni token
        - "data: [DONE]\n\n" a completamento

        Args:
            user_message: Messaggio utente corrente
            conversation_history: Storia conversazione (ultimi N messaggi)
            rag_context: Context RAG formattato con documenti rilevanti
            temperature: Override temperature (default: da settings)
            max_tokens: Override max tokens (default: da settings)

        Yields:
            str: Token SSE formattati ("data: {content}\n\n")

        Raises:
            Exception: Se la generazione fallisce
        """
        try:
            start_time = time.time()

            # Usa valori di default se non specificati
            temp = temperature if temperature is not None else self.temperature
            max_tok = max_tokens if max_tokens is not None else self.max_tokens

            # Costruisci lista messaggi
            messages = self._build_messages(
                user_message=user_message,
                conversation_history=conversation_history,
                rag_context=rag_context
            )

            # Log token count
            total_tokens = self._count_messages_tokens(messages)
            logger.debug(f"Total input tokens: {total_tokens}")

            logger.info(
                f"Starting streaming response - Model: {self.model}, "
                f"Temp: {temp}, Max tokens: {max_tok}"
            )

            # Chiama OpenAI API con streaming
            stream = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temp,
                max_tokens=max_tok,
                stream=True  # Enable streaming
            )

            # Track tokens per logging
            token_count = 0
            full_response = ""

            # Itera sui chunks dello stream
            for chunk in stream:
                # Estrai content delta
                delta = chunk.choices[0].delta

                if hasattr(delta, 'content') and delta.content:
                    content = delta.content
                    full_response += content
                    token_count += 1

                    # IMPORTANTE: Yielda token in formato SSE preservando esattamente
                    # il contenuto (inclusi spazi, punteggiatura, newlines)
                    # NON facciamo strip() o modifiche al content
                    yield f"data: {content}\n\n"

                # Check se stream finito
                if chunk.choices[0].finish_reason:
                    logger.debug(f"Stream finished: {chunk.choices[0].finish_reason}")

            # Yielda segnale completamento
            yield "data: [DONE]\n\n"

            processing_time = (time.time() - start_time) * 1000

            logger.info(
                f"Streaming completed - Chunks: {token_count}, "
                f"Time: {processing_time:.2f}ms, "
                f"Chars: {len(full_response)}"
            )

        except RateLimitError as e:
            logger.error(f"OpenAI rate limit exceeded during streaming: {e}")
            error_msg = "Troppe richieste in corso. Riprova tra qualche secondo."
            yield f"data: [ERROR] {error_msg}\n\n"

        except APITimeoutError as e:
            logger.error(f"OpenAI API timeout during streaming: {e}")
            error_msg = "Il servizio sta impiegando troppo tempo. Riprova."
            yield f"data: [ERROR] {error_msg}\n\n"

        except APIError as e:
            logger.error(f"OpenAI API error during streaming: {e}")
            yield f"data: [ERROR] Errore del servizio AI: {str(e)}\n\n"

        except Exception as e:
            logger.error(f"Error in streaming response: {e}")
            yield f"data: [ERROR] Errore interno: {str(e)}\n\n"

    def _build_messages(
        self,
        user_message: str,
        conversation_history: Optional[List[Message]] = None,
        rag_context: Optional[str] = None
    ) -> List[Dict[str, str]]:
        """
        Costruisce la lista di messaggi per OpenAI API.

        Ordine messaggi:
        1. System prompt (sempre presente)
        2. RAG context (se fornito) come messaggio system
        3. Conversation history (ultimi N messaggi)
        4. User message corrente

        Args:
            user_message: Messaggio utente corrente
            conversation_history: Storia conversazione
            rag_context: Context RAG formattato

        Returns:
            Lista di dict pronti per OpenAI API format
        """
        messages = []

        # 1. System prompt principale (dinamico da DB)
        messages.append({
            "role": "system",
            "content": self.system_prompt
        })

        # 2. RAG context (se presente)
        if rag_context:
            context_message = f"[CONTEXT - Documenti rilevanti dal database]\n\n{rag_context}"
            messages.append({
                "role": "system",
                "content": context_message
            })
            logger.debug(f"Added RAG context: {len(rag_context)} chars")

        # 3. Conversation history (limitata agli ultimi N messaggi)
        if conversation_history:
            # Prendi ultimi N messaggi
            recent_history = conversation_history[-self.max_history_messages:]

            for msg in recent_history:
                messages.append({
                    "role": msg.role.value if hasattr(msg.role, 'value') else msg.role,
                    "content": msg.content
                })

            logger.debug(f"Added {len(recent_history)} history messages")

        # 4. User message corrente
        messages.append({
            "role": "user",
            "content": user_message
        })

        logger.debug(f"Built {len(messages)} total messages for LLM")

        return messages

    def _count_messages_tokens(self, messages: List[Dict[str, str]]) -> int:
        """
        Conta i token totali in una lista di messaggi.

        Usa tiktoken per conteggio accurato. Utile per:
        - Verificare che non si superi il context limit
        - Logging e debugging
        - Ottimizzare la lunghezza history

        Args:
            messages: Lista messaggi formato OpenAI

        Returns:
            Numero totale di token
        """
        try:
            num_tokens = 0

            for message in messages:
                # Ogni messaggio ha overhead di ~4 token per formattazione
                num_tokens += 4

                # Conta token del content
                if "content" in message:
                    num_tokens += len(self.tokenizer.encode(message["content"]))

                # Role ha ~1 token
                if "role" in message:
                    num_tokens += 1

            # Overhead complessivo
            num_tokens += 2

            return num_tokens

        except Exception as e:
            logger.warning(f"Error counting tokens: {e}")
            # Fallback: stima approssimativa (1 token ~= 4 chars)
            total_chars = sum(len(m.get("content", "")) for m in messages)
            return total_chars // 4

    def count_tokens(self, text: str) -> int:
        """
        Conta token in un testo singolo.

        Utile per validazione input o calcoli esterni.

        Args:
            text: Testo da analizzare

        Returns:
            Numero di token
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            logger.warning(f"Error counting tokens for text: {e}")
            # Fallback
            return len(text) // 4

    def trim_conversation_history(
        self,
        history: List[Message],
        max_tokens: Optional[int] = None
    ) -> List[Message]:
        """
        Tronca conversation history per rispettare limit token.

        Mantiene i messaggi più recenti, rimuove i più vecchi fino a rientrare
        nel budget di token.

        Args:
            history: Lista completa messaggi
            max_tokens: Max token consentiti (default: self.max_context_tokens)

        Returns:
            Lista messaggi troncata
        """
        if not history:
            return []

        max_tok = max_tokens if max_tokens is not None else self.max_context_tokens

        # Converti in formato per counting
        messages_dicts = [
            {"role": m.role.value if hasattr(m.role, 'value') else m.role, "content": m.content}
            for m in history
        ]

        # Conta token totali
        total_tokens = self._count_messages_tokens(messages_dicts)

        # Se già sotto il limit, return tutto
        if total_tokens <= max_tok:
            logger.debug(f"History within token limit: {total_tokens}/{max_tok}")
            return history

        # Altrimenti, rimuovi messaggi vecchi
        logger.info(f"Trimming history: {total_tokens} -> {max_tok} tokens")

        trimmed = []
        current_tokens = 0

        # Itera dalla fine (più recenti)
        for msg in reversed(history):
            msg_dict = {
                "role": msg.role.value if hasattr(msg.role, 'value') else msg.role,
                "content": msg.content
            }
            msg_tokens = self._count_messages_tokens([msg_dict])

            if current_tokens + msg_tokens <= max_tok:
                trimmed.insert(0, msg)  # Inserisci all'inizio per mantenere ordine
                current_tokens += msg_tokens
            else:
                break

        logger.info(f"History trimmed: {len(history)} -> {len(trimmed)} messages")

        return trimmed

    def validate_input(self, text: str, max_length: int = 2000) -> bool:
        """
        Valida input utente prima di inviare a LLM.

        Checks:
        - Non vuoto
        - Non troppo lungo
        - Caratteri validi

        Args:
            text: Testo da validare
            max_length: Lunghezza massima caratteri

        Returns:
            True se valido, False altrimenti

        Raises:
            ValueError: Con messaggio specifico se non valido
        """
        if not text or not text.strip():
            raise ValueError("Il messaggio non può essere vuoto")

        if len(text) > max_length:
            raise ValueError(
                f"Il messaggio è troppo lungo (max {max_length} caratteri)"
            )

        # Check caratteri strani (opzionale)
        # Puoi aggiungere regex per bloccare input sospetti

        return True


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Crea istanza singleton del servizio LLM
# In questo modo viene inizializzato una volta sola all'avvio dell'app
try:
    llm_service = LLMService()
    logger.info("Global LLM service instance created")
except Exception as e:
    logger.error(f"Failed to create global LLM service: {e}")
    llm_service = None
