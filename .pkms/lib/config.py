"""
pkms/lib/config.py - Configuration Management

Loads and provides access to PKMS configuration from .pkms/config.toml.

Usage:
    from lib.config import get_config, get_path

    # Get entire config
    config = get_config()
    print(config["paths"]["vault"])

    # Get specific path (resolved to absolute Path)
    vault_path = get_path("vault")
    inbox_path = get_path("inbox")
    metadata_path = get_path("metadata")

Design:
- Paths are resolved relative to project root
- Config is cached (loaded once per process)
- Thread-safe singleton pattern
- Raises helpful errors if config missing
"""
import tomllib
from pathlib import Path
from typing import Any, Dict
from functools import lru_cache


@lru_cache(maxsize=1)
def _find_project_root() -> Path:
	"""
	Find project root by looking for .pkms/ directory.

	Searches upward from current working directory.

	Returns:
		Path: Absolute path to project root

	Raises:
		FileNotFoundError: If .pkms/ not found in any parent directory
	"""
	current = Path.cwd().resolve()

	# Check current directory first
	if (current / ".pkms").is_dir():
		return current

	# Search parent directories
	for parent in current.parents:
		if (parent / ".pkms").is_dir():
			return parent

	raise FileNotFoundError(
		"Could not find .pkms/ directory. "
		"Make sure you're running from within the PKMS project."
	)


@lru_cache(maxsize=1)
def get_config() -> Dict[str, Any]:
	"""
	Load configuration from .pkms/config.toml.

	Returns:
		Dict: Configuration dictionary

	Raises:
		FileNotFoundError: If config.toml not found
		tomllib.TOMLDecodeError: If config.toml is invalid

	Example:
		>>> config = get_config()
		>>> config["paths"]["vault"]
		'vault'
		>>> config["vault"]["organize_by_date"]
		True
	"""
	root = _find_project_root()
	config_path = root / ".pkms" / "config.toml"

	if not config_path.exists():
		raise FileNotFoundError(f"Config file not found: {config_path}")

	with open(config_path, "rb") as f:
		return tomllib.load(f)


def get_path(key: str) -> Path:
	"""
	Get absolute path from config.

	Args:
		key: Path key from [paths] section (e.g., "vault", "inbox", "metadata")

	Returns:
		Path: Absolute path resolved from project root

	Raises:
		KeyError: If path key not found in config

	Example:
		>>> vault_path = get_path("vault")
		>>> print(vault_path)
		/home/user/pkms/vault

		>>> metadata_path = get_path("metadata")
		>>> print(metadata_path)
		/home/user/pkms/data/metadata
	"""
	config = get_config()
	root = _find_project_root()

	if key not in config["paths"]:
		raise KeyError(f"Path '{key}' not found in config.toml [paths] section")

	rel_path = config["paths"][key]
	return (root / rel_path).resolve()


def get_vault_config() -> Dict[str, Any]:
	"""
	Get vault-specific configuration.

	Returns:
		Dict: Vault configuration

	Example:
		>>> vault_config = get_vault_config()
		>>> vault_config["organize_by_date"]
		True
		>>> vault_config["date_format"]
		'%Y-%m'
	"""
	config = get_config()
	return config.get("vault", {})


def get_embeddings_config() -> Dict[str, Any]:
	"""
	Get embeddings-specific configuration.

	Returns:
		Dict: Embeddings configuration

	Example:
		>>> emb_config = get_embeddings_config()
		>>> emb_config["model"]
		'nomic-embed-text'
		>>> emb_config["ollama_url"]
		'http://localhost:11434'
	"""
	config = get_config()
	return config.get("embeddings", {})


def get_search_config() -> Dict[str, Any]:
	"""
	Get search-specific configuration.

	Returns:
		Dict: Search configuration

	Example:
		>>> search_config = get_search_config()
		>>> search_config["bm25_weight"]
		0.5
		>>> search_config["semantic_weight"]
		0.5
	"""
	config = get_config()
	return config.get("search", {})


def get_relevance_config() -> Dict[str, Any]:
	"""
	Get relevance scoring configuration.

	Returns:
		Dict: Relevance configuration

	Example:
		>>> rel_config = get_relevance_config()
		>>> rel_config["weight_recency"]
		0.4
		>>> rel_config["recency_half_life_days"]
		90.0
	"""
	config = get_config()
	return config.get("relevance", {})


def get_chunking_config() -> Dict[str, Any]:
	"""
	Get chunking configuration.

	Returns:
		Dict: Chunking configuration

	Example:
		>>> chunk_config = get_chunking_config()
		>>> chunk_config["strategy"]
		'fixed'
		>>> chunk_config["chunk_size"]
		512
	"""
	config = get_config()
	return config.get("chunking", {})


def get_git_config() -> Dict[str, Any]:
	"""
	Get git configuration.

	Returns:
		Dict: Git configuration

	Example:
		>>> git_config = get_git_config()
		>>> git_config["auto_commit"]
		False
		>>> git_config["auto_push"]
		False
	"""
	config = get_config()
	return config.get("git", {})


def get_config_value(section: str, key: str, env_var: str | None = None, default: Any = None) -> Any:
	"""
	Get configuration value with fallback chain: config.toml > ENV > default.

	Args:
		section: Config section (e.g., "embeddings", "paths")
		key: Config key within section (e.g., "model", "vault")
		env_var: Optional environment variable name to check as override
		default: Default value if not found in config or ENV

	Returns:
		Configuration value from first available source

	Example:
		>>> # Reads from config.toml [embeddings] model,
		>>> # or PKMS_EMBED_MODEL env var,
		>>> # or defaults to "nomic-embed-text"
		>>> model = get_config_value("embeddings", "model", "PKMS_EMBED_MODEL", "nomic-embed-text")
	"""
	import os

	# 1. Try environment variable (highest priority - allows runtime override)
	if env_var:
		env_value = os.getenv(env_var)
		if env_value is not None:
			return env_value

	# 2. Try config file
	try:
		config = get_config()
		if section in config and key in config[section]:
			return config[section][key]
	except (FileNotFoundError, KeyError):
		pass

	# 3. Use default
	return default


def get_records_dir() -> str:
	"""
	Get metadata/records directory path.

	Convenience function with fallback chain.

	Returns:
		str: Path to metadata directory
	"""
	try:
		return str(get_path("metadata"))
	except (FileNotFoundError, KeyError):
		import os
		return os.getenv("PKMS_RECORDS_DIR", "data/metadata")


def get_chunks_dir() -> str:
	"""
	Get chunks directory path.

	Convenience function with fallback chain.

	Returns:
		str: Path to chunks directory
	"""
	try:
		return str(get_path("chunks"))
	except (FileNotFoundError, KeyError):
		import os
		return os.getenv("PKMS_CHUNKS_DIR", "data/chunks")
