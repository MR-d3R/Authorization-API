from fastapi import FastAPI
from pathlib import Path
from utils import load_and_validate_config

CONFIG_PATH = Path("config.json")
config = load_and_validate_config(CONFIG_PATH)
app = FastAPI(title = config.service_name ,debug = config.debug)

@app.get("/ping")
def ping():
    """
    Эндпоинт для проверки работы сервиса.
    Возвращает "pong" в ответ на "ping".
    """
    return {"message": "pong"}
