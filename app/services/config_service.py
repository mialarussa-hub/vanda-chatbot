"""
Configuration Service - Gestisce configurazioni dinamiche da Supabase
"""
from typing import Optional, Dict, Any
from supabase import create_client, Client
from loguru import logger
import json
from datetime import datetime, timedelta
import os


class ConfigService:
    """
    Servizio per gestire configurazioni dinamiche del chatbot.
    Legge da Supabase table 'chatbot_config' con caching.
    """

    def __init__(self):
        """Inizializza il servizio di configurazione"""
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")

        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL e SUPABASE_KEY devono essere configurati")

        self.client: Client = create_client(self.supabase_url, self.supabase_key)

        # Cache per configurazioni
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._cache_timestamp: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(seconds=300)  # 5 minuti default

        logger.info("ConfigService inizializzato")

    def get_config(self, config_key: str, use_cache: bool = True) -> Optional[Dict[str, Any]]:
        """
        Recupera una configurazione dal database.

        Args:
            config_key: Chiave della configurazione
            use_cache: Se True usa la cache (default: True)

        Returns:
            Dict con la configurazione o None se non trovata
        """
        # Controlla cache
        if use_cache and config_key in self._cache:
            cache_age = datetime.now() - self._cache_timestamp.get(config_key, datetime.min)
            if cache_age < self._cache_ttl:
                logger.debug(f"Config '{config_key}' recuperata da cache")
                return self._cache[config_key]

        try:
            # Query Supabase
            response = self.client.table("chatbot_config").select("*").eq("config_key", config_key).execute()

            if response.data and len(response.data) > 0:
                config_value = response.data[0].get("config_value", {})

                # Aggiorna cache
                self._cache[config_key] = config_value
                self._cache_timestamp[config_key] = datetime.now()

                logger.info(f"Config '{config_key}' recuperata da DB")
                return config_value
            else:
                logger.warning(f"Config '{config_key}' non trovata nel DB")
                return None

        except Exception as e:
            logger.error(f"Errore recupero config '{config_key}': {e}")
            return None

    def update_config(self, config_key: str, config_value: Dict[str, Any], updated_by: str = "admin") -> bool:
        """
        Aggiorna una configurazione nel database.

        Args:
            config_key: Chiave della configurazione
            config_value: Nuovo valore (dict)
            updated_by: Chi ha fatto l'update

        Returns:
            True se aggiornato con successo
        """
        try:
            # Update su Supabase
            response = self.client.table("chatbot_config").update({
                "config_value": config_value,
                "updated_at": datetime.now().isoformat(),
                "updated_by": updated_by
            }).eq("config_key", config_key).execute()

            if response.data:
                # Invalida cache
                if config_key in self._cache:
                    del self._cache[config_key]

                logger.info(f"Config '{config_key}' aggiornata da {updated_by}")
                return True
            else:
                logger.error(f"Errore update config '{config_key}'")
                return False

        except Exception as e:
            logger.error(f"Errore update config '{config_key}': {e}")
            return False

    def get_system_prompt(self) -> str:
        """Recupera il system prompt corrente"""
        config = self.get_config("system_prompt")
        if config:
            return config.get("prompt", "")
        return ""

    def get_rag_parameters(self) -> Dict[str, Any]:
        """Recupera i parametri RAG correnti"""
        config = self.get_config("rag_parameters")
        if config:
            return config
        # Fallback a valori default
        return {
            "match_count": 3,
            "match_threshold": 0.60,
            "max_context_length": 8000,
            "enable_metadata_filters": True
        }

    def get_llm_parameters(self) -> Dict[str, Any]:
        """Recupera i parametri LLM correnti"""
        config = self.get_config("llm_parameters")
        if config:
            return config
        # Fallback a valori default
        return {
            "model": "gpt-4o-mini",
            "temperature": 0.5,
            "max_tokens": 500,
            "stream_enabled": True
        }

    def get_advanced_settings(self) -> Dict[str, Any]:
        """Recupera le impostazioni avanzate"""
        config = self.get_config("advanced_settings")
        if config:
            return config
        # Fallback a valori default
        return {
            "cache_ttl_seconds": 300,
            "enable_conversation_memory": True,
            "max_history_messages": 10
        }

    def clear_cache(self):
        """Svuota tutta la cache delle configurazioni"""
        self._cache.clear()
        self._cache_timestamp.clear()
        logger.info("Cache configurazioni svuotata")

    def get_all_configs(self) -> Dict[str, Dict[str, Any]]:
        """
        Recupera tutte le configurazioni.

        Returns:
            Dict con tutte le configurazioni
        """
        try:
            response = self.client.table("chatbot_config").select("*").execute()

            configs = {}
            if response.data:
                for row in response.data:
                    configs[row["config_key"]] = {
                        "value": row["config_value"],
                        "description": row.get("description", ""),
                        "updated_at": row.get("updated_at", ""),
                        "updated_by": row.get("updated_by", "")
                    }

            return configs

        except Exception as e:
            logger.error(f"Errore recupero tutte le config: {e}")
            return {}


# Istanza globale singleton
_config_service: Optional[ConfigService] = None


def get_config_service() -> ConfigService:
    """
    Restituisce l'istanza singleton del ConfigService.

    Returns:
        ConfigService instance
    """
    global _config_service
    if _config_service is None:
        _config_service = ConfigService()
    return _config_service
