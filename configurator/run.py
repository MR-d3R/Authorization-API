from argparse import ArgumentParser
from pathlib import Path
from .utils import load_and_validate_config, create_default_config
import uvicorn

CONFIG_PATH = Path("config.json")

def runner():
    """
    Запуск валидатора конфигурации и FastAPI микросервиса.

    Этот скрипт выполняет следующие функции:
    1. Создание файла конфигурации по умолчанию, если указан аргумент `--cfg`.
    2. Загрузка и валидация файла конфигурации.
    3. Запуск FastAPI приложения с использованием Uvicorn.

    Конфигурация:
    - Располагается в файле config.json.
    - Должна содержать следующие параметры:
        - service_name: Название сервиса (str).
        - host: Хост для запуска приложения (str).
        - port: Порт для запуска приложения (int).
        - debug: Режим отладки (bool).

    Пример использования:
        python main.py --cfg    # Создать файл конфигурации по умолчанию.
        python main.py          # Запустить приложение с указанной конфигурацией.

    Если параметр `debug` в конфигурации установлен в `True`,
    сервер будет запущен с поддержкой автоматической перезагрузки.
    """
    parser = ArgumentParser(description="Config validator and FastAPI microservice launcher.")
    parser.add_argument("--cfg", 
                        action="store_true", 
                        help="Create a default configuration file."
                        )
    args = parser.parse_args()

    if args.cfg:
        create_default_config(CONFIG_PATH)
    else:
        try:
            config = load_and_validate_config(CONFIG_PATH)
            print("Configuration is valid:", config)
            uvicorn.run("app:app", 
                        host=config.host, 
                        port=config.port, 
                        reload=config.debug
                        )
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    runner()
