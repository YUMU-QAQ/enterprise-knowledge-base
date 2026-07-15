"""全局配置 — 从环境变量 / .env 加载"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # ── 应用 ──
    APP_NAME: str = "企业知识库"
    APP_ENV: str = "development"
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # ── 数据库 ──
    DATABASE_URL: str = "postgresql+asyncpg://kb_user:changeme@localhost:5432/knowledge_base"
    DATABASE_URL_SYNC: str = "postgresql://kb_user:changeme@localhost:5432/knowledge_base"

    # ── Redis ──
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Elasticsearch ──
    ES_HOST: str = "http://localhost:9200"
    ES_USER: Optional[str] = None
    ES_PASSWORD: Optional[str] = None

    # ── MinIO ──
    MINIO_ENDPOINT: str = "localhost:9000"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "changeme"
    MINIO_BUCKET: str = "knowledge-base"
    MINIO_SECURE: bool = False

    # ── JWT ──
    SECRET_KEY: str = "change-me-to-a-random-string-at-least-32-chars"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24h
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── 飞书 ──
    FEISHU_ENABLED: bool = False
    FEISHU_APP_ID: Optional[str] = None
    FEISHU_APP_SECRET: Optional[str] = None
    FEISHU_VERIFICATION_TOKEN: Optional[str] = None
    FEISHU_ENCRYPT_KEY: Optional[str] = None

    # ── 钉钉 ──
    DINGTALK_ENABLED: bool = False
    DINGTALK_APP_KEY: Optional[str] = None
    DINGTALK_APP_SECRET: Optional[str] = None
    DINGTALK_CORP_ID: Optional[str] = None
    DINGTALK_AES_KEY: Optional[str] = None
    DINGTALK_TOKEN: Optional[str] = None

    # ── LLM ──
    LLM_PROVIDER: str = "openai_compatible"
    LLM_BASE_URL: str = "http://localhost:11434/v1"
    LLM_API_KEY: str = "ollama"
    LLM_MODEL: str = "qwen3:14b"
    LLM_MAX_TOKENS: int = 2048
    LLM_TEMPERATURE: float = 0.3

    # ── Embedding ──
    EMBEDDING_MODEL: str = "BAAI/bge-m3"
    EMBEDDING_DEVICE: str = "cpu"
    EMBEDDING_DIM: int = 768
    EMBEDDING_BATCH_SIZE: int = 32

    # ── Reranker ──
    RERANKER_MODEL: str = "BAAI/bge-reranker-v2-m3"
    RERANKER_TOP_K: int = 5
    RERANKER_DEVICE: str = "cpu"

    # ── 分块 ──
    CHUNK_SIZE: int = 512
    CHUNK_OVERLAP: int = 50

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",")]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
