"""
Memory Manager per VANDA chatbot.

Gestisce:
- Salvataggio conversazioni su Supabase (tabella chat_messages)
- Recupero history per session_id
- Cleanup sessioni vecchie
- Statistiche e analytics
- Thread-safe per accessi concorrenti
"""

from supabase import create_client, Client
from app.config import settings
from app.models.schemas import Message, MessageRole
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from loguru import logger
import uuid
import threading


class MemoryManager:
    """
    Servizio per gestione memoria conversazioni su Supabase.

    Salva tutti i messaggi (user/assistant/system) nella tabella chat_messages
    permettendo recupero, analisi e cleanup delle conversazioni.
    """

    def __init__(self):
        """
        Inizializza connessione Supabase per memory storage.

        Raises:
            Exception: Se la connessione fallisce
        """
        try:
            # Connessione Supabase
            self.client: Client = create_client(
                settings.SUPABASE_URL,
                settings.SUPABASE_KEY
            )
            self.table_name = "chat_messages"

            # Thread lock per operazioni thread-safe
            self._lock = threading.Lock()

            # Configurazioni
            self.max_history_messages = 50  # Max messaggi da recuperare per sessione
            self.session_timeout_hours = 24  # Timeout sessione inattiva (24h)

            logger.info(f"Memory Manager initialized - Table: {self.table_name}")

        except Exception as e:
            logger.error(f"Failed to initialize Memory Manager: {e}")
            raise

    def add_message(
        self,
        session_id: str,
        role: MessageRole,
        content: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[int]:
        """
        Aggiunge un messaggio alla conversazione.

        Salva il messaggio su Supabase in modo thread-safe.

        Args:
            session_id: UUID sessione (può essere string UUID o UUID object)
            role: Ruolo messaggio (user, assistant, system)
            content: Contenuto testuale messaggio
            metadata: Dati extra (tokens_used, model, rag_documents, etc)

        Returns:
            ID del messaggio salvato, None se errore

        Example:
            >>> memory_manager.add_message(
            ...     session_id="550e8400-e29b-41d4-a716-446655440000",
            ...     role=MessageRole.USER,
            ...     content="Ciao!",
            ...     metadata={}
            ... )
            1
        """
        try:
            with self._lock:
                # Prepara dati
                role_str = role.value if hasattr(role, 'value') else str(role)

                message_data = {
                    "session_id": str(session_id),  # Converti UUID a string
                    "role": role_str,
                    "content": content,
                    "metadata": metadata or {}
                }

                # Inserisci su Supabase
                response = self.client.table(self.table_name).insert(message_data).execute()

                if response.data:
                    message_id = response.data[0]["id"]
                    logger.debug(
                        f"Message saved - session: {session_id}, "
                        f"role: {role_str}, id: {message_id}"
                    )
                    return message_id
                else:
                    logger.warning(f"No data returned after insert for session {session_id}")
                    return None

        except Exception as e:
            logger.error(f"Error saving message for session {session_id}: {e}")
            return None

    def get_history(
        self,
        session_id: str,
        limit: Optional[int] = None,
        include_system: bool = False
    ) -> List[Message]:
        """
        Recupera la history di una conversazione.

        Args:
            session_id: UUID sessione
            limit: Max numero messaggi (default: self.max_history_messages)
            include_system: Se includere messaggi system (default: False)

        Returns:
            Lista di Message objects ordinati cronologicamente

        Example:
            >>> history = memory_manager.get_history("550e8400-...")
            >>> for msg in history:
            ...     print(f"{msg.role}: {msg.content}")
        """
        try:
            max_messages = limit if limit is not None else self.max_history_messages

            # Query Supabase
            query = self.client.table(self.table_name)\
                .select("*")\
                .eq("session_id", str(session_id))\
                .order("created_at", desc=False)\
                .limit(max_messages)

            response = query.execute()

            if not response.data:
                logger.debug(f"No messages found for session {session_id}")
                return []

            # Converti in Message objects
            messages = []
            for row in response.data:
                role_str = row["role"]

                # Filtra system messages se richiesto
                if not include_system and role_str == "system":
                    continue

                # Converti role string in MessageRole enum
                try:
                    role = MessageRole(role_str)
                except ValueError:
                    logger.warning(f"Unknown role: {role_str}, skipping message")
                    continue

                # Crea Message object
                message = Message(
                    role=role,
                    content=row["content"],
                    timestamp=datetime.fromisoformat(row["created_at"].replace('Z', '+00:00'))
                )

                messages.append(message)

            logger.info(
                f"Retrieved {len(messages)} messages for session {session_id}"
            )

            return messages

        except Exception as e:
            logger.error(f"Error retrieving history for session {session_id}: {e}")
            return []

    def get_sessions(
        self,
        active_only: bool = True,
        hours_threshold: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Recupera lista di tutte le sessioni.

        Args:
            active_only: Se True, solo sessioni attive (default: True)
            hours_threshold: Considera attive solo sessioni con activity < N ore fa
                           (default: self.session_timeout_hours)

        Returns:
            Lista di dict con info sessioni: {session_id, message_count, last_activity}

        Example:
            >>> sessions = memory_manager.get_sessions()
            >>> for session in sessions:
            ...     print(f"{session['session_id']}: {session['message_count']} messages")
        """
        try:
            hours = hours_threshold if hours_threshold is not None else self.session_timeout_hours

            # Query tutti i messaggi raggruppati per session_id
            response = self.client.table(self.table_name)\
                .select("session_id, created_at")\
                .execute()

            if not response.data:
                logger.debug("No sessions found")
                return []

            # Raggruppa per session_id
            sessions_map = {}
            for row in response.data:
                session_id = row["session_id"]
                created_at = datetime.fromisoformat(row["created_at"].replace('Z', '+00:00'))

                if session_id not in sessions_map:
                    sessions_map[session_id] = {
                        "session_id": session_id,
                        "message_count": 0,
                        "last_activity": created_at
                    }

                sessions_map[session_id]["message_count"] += 1

                # Aggiorna last_activity se più recente
                if created_at > sessions_map[session_id]["last_activity"]:
                    sessions_map[session_id]["last_activity"] = created_at

            sessions = list(sessions_map.values())

            # Filtra sessioni attive se richiesto
            if active_only:
                threshold_time = datetime.now(datetime.timezone.utc) - timedelta(hours=hours)
                sessions = [
                    s for s in sessions
                    if s["last_activity"] > threshold_time
                ]

            logger.info(f"Found {len(sessions)} sessions (active_only={active_only})")

            return sessions

        except Exception as e:
            logger.error(f"Error retrieving sessions: {e}")
            return []

    def delete_session(self, session_id: str) -> bool:
        """
        Elimina tutti i messaggi di una sessione.

        Args:
            session_id: UUID sessione da eliminare

        Returns:
            True se eliminata con successo, False altrimenti

        Example:
            >>> memory_manager.delete_session("550e8400-...")
            True
        """
        try:
            with self._lock:
                response = self.client.table(self.table_name)\
                    .delete()\
                    .eq("session_id", str(session_id))\
                    .execute()

                # Supabase delete ritorna i record eliminati
                deleted_count = len(response.data) if response.data else 0

                if deleted_count > 0:
                    logger.info(f"Session {session_id} deleted ({deleted_count} messages)")
                    return True
                else:
                    logger.warning(f"Session {session_id} not found or already deleted")
                    return False

        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")
            return False

    def cleanup_old_sessions(self, hours_threshold: Optional[int] = None) -> int:
        """
        Elimina sessioni vecchie inattive.

        Rimuove tutte le sessioni con ultima attività > N ore fa.

        Args:
            hours_threshold: Ore di inattività (default: self.session_timeout_hours)

        Returns:
            Numero di sessioni eliminate

        Example:
            >>> count = memory_manager.cleanup_old_sessions(hours_threshold=48)
            >>> print(f"Deleted {count} old sessions")
        """
        try:
            hours = hours_threshold if hours_threshold is not None else self.session_timeout_hours
            threshold_time = datetime.utcnow() - timedelta(hours=hours)

            logger.info(f"Starting cleanup of sessions older than {hours}h")

            # Trova sessioni vecchie
            response = self.client.table(self.table_name)\
                .select("session_id, created_at")\
                .lt("created_at", threshold_time.isoformat())\
                .execute()

            if not response.data:
                logger.info("No old sessions to cleanup")
                return 0

            # Trova session_id unici delle sessioni vecchie
            old_sessions = set(row["session_id"] for row in response.data)

            # Elimina messaggi vecchi
            deleted_count = 0
            for session_id in old_sessions:
                if self.delete_session(session_id):
                    deleted_count += 1

            logger.info(f"Cleanup completed: {deleted_count} sessions deleted")

            return deleted_count

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return 0

    def get_session_stats(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Recupera statistiche di una sessione.

        Args:
            session_id: UUID sessione

        Returns:
            Dict con stats: {
                message_count, user_count, assistant_count,
                first_message, last_message, duration_minutes
            }
            None se sessione non trovata

        Example:
            >>> stats = memory_manager.get_session_stats("550e8400-...")
            >>> print(f"Durata: {stats['duration_minutes']} minuti")
        """
        try:
            response = self.client.table(self.table_name)\
                .select("role, created_at")\
                .eq("session_id", str(session_id))\
                .order("created_at", desc=False)\
                .execute()

            if not response.data:
                logger.debug(f"No stats available for session {session_id}")
                return None

            messages = response.data

            # Conta messaggi per ruolo
            user_count = sum(1 for m in messages if m["role"] == "user")
            assistant_count = sum(1 for m in messages if m["role"] == "assistant")

            # Timestamp primo e ultimo messaggio
            first_message = datetime.fromisoformat(messages[0]["created_at"].replace('Z', '+00:00'))
            last_message = datetime.fromisoformat(messages[-1]["created_at"].replace('Z', '+00:00'))

            # Durata conversazione
            duration = last_message - first_message
            duration_minutes = duration.total_seconds() / 60

            stats = {
                "session_id": session_id,
                "message_count": len(messages),
                "user_count": user_count,
                "assistant_count": assistant_count,
                "first_message": first_message,
                "last_message": last_message,
                "duration_minutes": round(duration_minutes, 2)
            }

            logger.debug(f"Stats for session {session_id}: {stats}")

            return stats

        except Exception as e:
            logger.error(f"Error getting stats for session {session_id}: {e}")
            return None

    def generate_session_id(self) -> str:
        """
        Genera un nuovo UUID per sessione.

        Returns:
            String UUID v4

        Example:
            >>> session_id = memory_manager.generate_session_id()
            >>> print(session_id)
            '550e8400-e29b-41d4-a716-446655440000'
        """
        return str(uuid.uuid4())


# ============================================================================
# SINGLETON INSTANCE
# ============================================================================

# Crea istanza singleton del Memory Manager
try:
    memory_manager = MemoryManager()
    logger.info("Global Memory Manager instance created")
except Exception as e:
    logger.error(f"Failed to create global Memory Manager: {e}")
    memory_manager = None
