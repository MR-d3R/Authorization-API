import json
from pathlib import Path
from pydantic import BaseModel, ValidationError

class ConfigSchema(BaseModel):
    service_name: str
    host: str
    port: int
    debug: bool

    class Config:
        extra = 'allow'  

def load_and_validate_config(config_path: Path):
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file '{config_path}' not found.")

    with config_path.open("r") as file:
        try:
            config_data = json.load(file)
            return ConfigSchema(**config_data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in configuration file: {e}")
        except ValidationError as e:
            raise ValueError(f"Configuration validation error: {e}")

def create_default_config(config_path: Path):
    default_config = {
        "service_name": "fastapi_microservice",
        "host": "127.0.0.1",
        "port": 8000,
        "debug": True
    }

    with config_path.open("w") as file:
        json.dump(default_config, file, indent=4)
    print(f"Default configuration created at '{config_path}'.")
