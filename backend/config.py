"""Typed configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass(frozen=True)
class Settings:
    """Application settings — all sourced from .env / environment."""

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "cuedrop_dev"

    # VirtualDJ
    vdj_host: str = "http://127.0.0.1:80"
    vdj_auth_token: str = ""

    # Anthropic (Claude)
    anthropic_api_key: str = ""

    # Spotify
    spotify_client_id: str = ""
    spotify_client_secret: str = ""

    # Local library
    local_library_path: str = ""

    # ACRCloud
    acrcloud_access_key: str = ""
    acrcloud_access_secret: str = ""
    acrcloud_host: str = ""

    # Essentia microservice
    essentia_url: str | None = None

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] | None = None

    def __post_init__(self) -> None:
        if self.cors_origins is None:
            object.__setattr__(self, "cors_origins", ["*"])


def load_settings(env_path: str = "backend/.env") -> Settings:
    """Load settings from .env file and environment variables."""
    load_dotenv(dotenv_path=env_path)

    return Settings(
        neo4j_uri=os.getenv("NEO4J_URI", Settings.neo4j_uri),
        neo4j_user=os.getenv("NEO4J_USER", Settings.neo4j_user),
        neo4j_password=os.getenv("NEO4J_PASSWORD", Settings.neo4j_password),
        vdj_host=os.getenv("VDJ_HOST", Settings.vdj_host),
        vdj_auth_token=os.getenv("VDJ_AUTH_TOKEN", Settings.vdj_auth_token),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", Settings.anthropic_api_key),
        acrcloud_access_key=os.getenv("ACRCLOUD_ACCESS_KEY", Settings.acrcloud_access_key),
        acrcloud_access_secret=os.getenv("ACRCLOUD_ACCESS_SECRET", Settings.acrcloud_access_secret),
        acrcloud_host=os.getenv("ACRCLOUD_HOST", Settings.acrcloud_host),
        spotify_client_id=os.getenv("SPOTIFY_CLIENT_ID", Settings.spotify_client_id),
        spotify_client_secret=os.getenv("SPOTIFY_CLIENT_SECRET", Settings.spotify_client_secret),
        local_library_path=os.getenv("LOCAL_LIBRARY_PATH", Settings.local_library_path),
        essentia_url=os.getenv("ESSENTIA_URL") or None,
        host=os.getenv("HOST", Settings.host),
        port=int(os.getenv("PORT", str(Settings.port))),
    )
