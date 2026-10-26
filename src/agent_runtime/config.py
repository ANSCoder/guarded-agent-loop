"""Settings, read from AGENT_* environment variables or .env. Defaults are here."""

from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All settings. Each one can be set as AGENT_<NAME> in the environment or in .env."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="AGENT_", extra="ignore")

    # anthropic: the paid Claude API. openai: any OpenAI-style server (Ollama, Hugging Face, ...).
    provider: Literal["anthropic", "openai"] = "anthropic"
    base_url: str = ""  # openai provider only, e.g. http://localhost:11434/v1 for Ollama
    # Keys are read from the environment or .env and never printed or put in a trace.
    anthropic_api_key: SecretStr | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    api_key: SecretStr | None = None  # openai provider only; leave unset for Ollama
    reasoning_effort: str = ""  # openai provider only; "none" skips a thinking model's reasoning
    model: str = "claude-sonnet-5-5"
    max_steps: int = Field(default=12, ge=1)
    max_tokens: int = 4096
    timeout_s: float = 120.0
    tool_timeout_s: float = 10.0
    tool_output_cap: int = 4000
    trace_dir: str = "traces"
    checkpoint_dir: str = "checkpoints"
    policy_path: str = "config/policy.toml"
    mcp_path: str = "config/mcp.toml"
