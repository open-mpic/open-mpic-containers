import os
import sys
import yaml
from typing import Dict, Any


def load_config(config_path: str) -> Dict[str, Any]:
    """Load uvicorn configuration from YAML file."""
    if not os.path.exists(config_path):
        print(f"Config file not found at {config_path}", file=sys.stderr)
        sys.exit(1)

    with open(config_path, 'r') as f:
        return yaml.safe_load(f)


def main():
    # Default config path, can be overridden by environment variable
    config_path = os.getenv('UVICORN_CONFIG_PATH', '/app/config/uvicorn_config.yaml')
    config = load_config(config_path)

    import uvicorn

    # Ensure required config values have defaults
    config.setdefault('host', '0.0.0.0')
    config.setdefault('port', 80)
    config.setdefault('proxy_headers', True)
    config.setdefault('log_config', '/app/config/log_config.yaml')
    config.setdefault('timeout_keep_alive', 60)

    # Get a default number of workers based on cpu count
    workers = (os.cpu_count() * 2 + 1) if os.cpu_count() else 1
    config.setdefault('workers', workers)

    # set OS env variable for FastAPI app to access to output runtime configuration
    os.environ['uvicorn_server_timeout_keep_alive'] = config['timeout_keep_alive']

    # Start uvicorn with the configured parameters
    uvicorn.run(
        "main:app",
        host=config['host'],
        port=config['port'],
        proxy_headers=config['proxy_headers'],
        log_config=config['log_config'],
        timeout_keep_alive=config['timeout_keep_alive'],
        workers=config['workers'],
        reload=config.get('reload', False)
    )


if __name__ == "__main__":
    main()
