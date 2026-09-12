"""Configuração por variáveis de ambiente (ou .env na raiz do repo)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = "postgresql+psycopg://enter:enter@localhost:5432/enter"
    secret_key: str = "dev-nao-usar-em-producao"
    demo_token: str = "demo"
    domain: str = ":8080"  # site do Caddy; ":8080" = local sem TLS
    data_dir: Path = Path("data")
    model_impl: str = "app.modelo_enteros:ModeloEnteros"
    extractor_impl: str = "extractor.pipeline:Extrator"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    sessao_horas: int = 12
    api_url: str = "http://localhost:8000"  # usado pelo CLI para avisar a API após cargas

    @property
    def cookie_secure(self) -> bool:
        return not (self.domain.startswith(":") or "localhost" in self.domain)

    @property
    def exemplos_dir(self) -> Path:
        return self.data_dir / "exemplos"

    @property
    def derived_dir(self) -> Path:
        return self.data_dir / "derived"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
