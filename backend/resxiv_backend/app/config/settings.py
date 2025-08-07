"""
Application Settings Configuration

This module handles all configuration management using Pydantic settings
for type validation and environment variable parsing.
"""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic_settings import BaseSettings
from pydantic import Field, field_validator
import os
from pathlib import Path


class DatabaseSettings(BaseSettings):
    """Database configuration settings"""
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    # PostgreSQL
    postgres_host: str = Field(default="localhost", env="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, env="POSTGRES_PORT")
    postgres_db: str = Field(default="resxiv", env="POSTGRES_DB")
    postgres_user: str = Field(default="postgres", env="POSTGRES_USER")
    postgres_password: str = Field(default="postgres", env="POSTGRES_PASSWORD")
    postgres_echo: bool = Field(default=False, env="POSTGRES_ECHO")
    postgres_pool_size: int = Field(default=10, env="POSTGRES_POOL_SIZE")
    postgres_max_overflow: int = Field(default=20, env="POSTGRES_MAX_OVERFLOW")
    
    # MongoDB
    mongodb_host: str = Field(default="localhost", env="MONGODB_HOST")
    mongodb_port: int = Field(default=27017, env="MONGODB_PORT")
    mongodb_db: str = Field(default="resxiv_chat", env="MONGODB_DB")
    mongodb_user: Optional[str] = Field(default=None, env="MONGODB_USER")
    mongodb_password: Optional[str] = Field(default=None, env="MONGODB_PASSWORD")
    mongodb_replica_set: Optional[str] = Field(default=None, env="MONGODB_REPLICA_SET")
    
    # Redis
    redis_host: str = Field(default="localhost", env="REDIS_HOST")
    redis_port: int = Field(default=6379, env="REDIS_PORT")
    redis_db: int = Field(default=0, env="REDIS_DB")
    redis_password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    redis_socket_timeout: int = Field(default=30, env="REDIS_SOCKET_TIMEOUT")
    redis_connection_pool_size: int = Field(default=10, env="REDIS_CONNECTION_POOL_SIZE")
    
    @property
    def postgres_url(self) -> str:
        """Generate PostgreSQL connection URL"""
        return (
            f"postgresql+asyncpg://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )
    
    @property
    def mongodb_url(self) -> str:
        """Generate MongoDB connection URL"""
        if self.mongodb_user and self.mongodb_password:
            auth = f"{self.mongodb_user}:{self.mongodb_password}@"
        else:
            auth = ""
        
        url = f"mongodb://{auth}{self.mongodb_host}:{self.mongodb_port}/{self.mongodb_db}"
        
        if self.mongodb_replica_set:
            url += f"?replicaSet={self.mongodb_replica_set}"
        
        return url
    
    @property
    def redis_url(self) -> str:
        """Generate Redis connection URL"""
        if self.redis_password:
            auth = f":{self.redis_password}@"
        else:
            auth = ""
        
        return f"redis://{auth}{self.redis_host}:{self.redis_port}/{self.redis_db}"


class JWTSettings(BaseSettings):
    """JWT authentication settings"""
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    secret_key: str = Field(..., env="JWT_SECRET_KEY")
    algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    access_token_expire_minutes: int = Field(default=300, env="JWT_ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, env="JWT_REFRESH_TOKEN_EXPIRE_DAYS")
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("JWT secret key must be at least 32 characters long")
        return v


class SecuritySettings(BaseSettings):
    """Security configuration settings"""
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    bcrypt_rounds: int = Field(default=12, env="BCRYPT_ROUNDS")
    password_min_length: int = Field(default=8, env="PASSWORD_MIN_LENGTH")
    max_login_attempts: int = Field(default=5, env="MAX_LOGIN_ATTEMPTS")
    lockout_duration_minutes: int = Field(default=15, env="LOCKOUT_DURATION_MINUTES")
    
    @field_validator("bcrypt_rounds")
    @classmethod
    def validate_bcrypt_rounds(cls, v):
        if v < 10 or v > 15:
            raise ValueError("Bcrypt rounds should be between 10 and 15")
        return v


class CORSSettings(BaseSettings):
    """CORS configuration settings"""
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    origins: Union[str, List[str]] = Field(
        default=["http://35.154.171.72:3000"], 
        env="CORS_ORIGINS"
    )
    credentials: bool = Field(default=True, env="CORS_CREDENTIALS")
    methods: Union[str, List[str]] = Field(
        default=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
        env="CORS_METHODS"
    )
    headers: Union[str, List[str]] = Field(default=["*"], env="CORS_HEADERS")
    
    @field_validator("origins", mode='before')
    @classmethod
    def parse_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("methods", mode='before')
    @classmethod
    def parse_methods(cls, v):
        if isinstance(v, str):
            return [method.strip() for method in v.split(",")]
        return v
    
    @field_validator("headers", mode='before')
    @classmethod
    def parse_headers(cls, v):
        if isinstance(v, str):
            return [header.strip() for header in v.split(",")]
        return v


class FileSettings(BaseSettings):
    """File upload and storage settings"""
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    max_file_size: int = Field(default=50, env="MAX_FILE_SIZE")  # MB
    allowed_file_types: Union[str, List[str]] = Field(
        default=["pdf", "doc", "docx", "tex", "txt", "png", "jpg", "jpeg", "svg"],
        env="ALLOWED_FILE_TYPES"
    )
    upload_dir: Path = Field(default=Path("./uploads"), env="UPLOAD_DIR")
    static_dir: Path = Field(default=Path("./static"), env="STATIC_DIR")
    papers_dir: Path = Field(default=Path("../../papers"), env="PAPERS_DIR")
    
    @field_validator("allowed_file_types", mode='before')
    @classmethod
    def parse_file_types(cls, v):
        if isinstance(v, str):
            return [file_type.strip() for file_type in v.split(",")]
        return v
    
    @field_validator("upload_dir", "static_dir", "papers_dir", mode='before')
    @classmethod
    def parse_paths(cls, v):
        return Path(v)
    
    @property
    def max_file_size_bytes(self) -> int:
        """Convert MB to bytes"""
        return self.max_file_size * 1024 * 1024


class EmailSettings(BaseSettings):
    """Email configuration settings"""
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    smtp_host: str = Field(default="smtp.gmail.com", env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_username: str = Field(default="", env="SMTP_USERNAME")
    smtp_password: str = Field(default="", env="SMTP_PASSWORD")
    smtp_tls: bool = Field(default=True, env="SMTP_TLS")
    from_email: str = Field(default="noreply@resxiv.com", env="FROM_EMAIL")
    
    @field_validator("smtp_port")
    @classmethod
    def validate_smtp_port(cls, v):
        if v not in [25, 465, 587, 2525]:
            raise ValueError("SMTP port must be one of: 25, 465, 587, 2525")
        return v


class AgenticSettings(BaseSettings):
    """Agentic system configuration settings"""
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }
    
    # OpenAI Configuration
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    
    # Agentic Model Configuration
    agentic_model: str = Field(default="gpt-4o-mini", env="AGENTIC_MODEL")
    agentic_max_tool_calls: int = Field(default=25, env="AGENTIC_MAX_TOOL_CALLS")
    agentic_session_timeout_hours: int = Field(default=24, env="AGENTIC_SESSION_TIMEOUT_HOURS")
    
    # Agent Configuration
    enable_research_agent: bool = Field(default=True, env="ENABLE_RESEARCH_AGENT")
    enable_project_agent: bool = Field(default=True, env="ENABLE_PROJECT_AGENT")
    enable_paper_agent: bool = Field(default=True, env="ENABLE_PAPER_AGENT")
    enable_conversation_agent: bool = Field(default=True, env="ENABLE_CONVERSATION_AGENT")
    
    # Tool Configuration
    enable_research_tools: bool = Field(default=True, env="ENABLE_RESEARCH_TOOLS")
    enable_project_tools: bool = Field(default=True, env="ENABLE_PROJECT_TOOLS")
    enable_paper_tools: bool = Field(default=True, env="ENABLE_PAPER_TOOLS")
    
    # PDF Chat Configuration
    max_pdf_upload_size_mb: int = Field(default=50, env="MAX_PDF_UPLOAD_SIZE_MB")
    
    @field_validator("agentic_model")
    @classmethod
    def validate_model(cls, v):
        allowed_models = [
            "gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-4", 
            "gpt-3.5-turbo", "gpt-3.5-turbo-16k"
        ]
        if v not in allowed_models:
            raise ValueError(f"Model must be one of: {', '.join(allowed_models)}")
        return v
    
    @field_validator("agentic_max_tool_calls")
    @classmethod
    def validate_max_tool_calls(cls, v):
        if v < 1 or v > 100:
            raise ValueError("Max tool calls must be between 1 and 100")
        return v


class Settings(BaseSettings):
    """Main application settings"""
    
    # Application
    app_name: str = Field(default="ResXiv", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    app_description: str = Field(
        default="Unified Research Collaboration Platform",
        env="APP_DESCRIPTION"
    )
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=True, env="DEBUG")
    secret_key: str = Field(..., env="SECRET_KEY")
    
    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=1, env="WORKERS")
    reload: bool = Field(default=True, env="RELOAD")

    # Frontend URL (used in e-mails for links)
    frontend_url: str = Field(default="cbeta.resxiv.com", env="FRONTEND_URL")
    
    # Sub-settings
    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    security: SecuritySettings = Field(default_factory=SecuritySettings)
    cors: CORSSettings = Field(default_factory=CORSSettings)
    files: FileSettings = Field(default_factory=FileSettings)
    email: EmailSettings = Field(default_factory=EmailSettings)
    agentic: AgenticSettings = Field(default_factory=AgenticSettings)
    
    # Feature flags
    enable_registration: bool = Field(default=True, env="ENABLE_REGISTRATION")
    enable_file_upload: bool = Field(default=True, env="ENABLE_FILE_UPLOAD")
    enable_ai_features: bool = Field(default=True, env="ENABLE_AI_FEATURES")
    enable_real_time_collaboration: bool = Field(default=True, env="ENABLE_REAL_TIME_COLLABORATION")
    enable_analytics: bool = Field(default=True, env="ENABLE_ANALYTICS")
    enable_external_apis: bool = Field(default=True, env="ENABLE_EXTERNAL_APIS")
    
    @field_validator("secret_key")
    @classmethod
    def validate_secret_key(cls, v):
        if len(v) < 32:
            raise ValueError("Secret key must be at least 32 characters long")
        return v
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        if v not in ["development", "testing", "staging", "production"]:
            raise ValueError("Environment must be one of: development, testing, staging, production")
        return v
    
    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """Get application settings (cached)"""
    return Settings() 