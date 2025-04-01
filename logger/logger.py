import logging
from datetime import datetime
from termcolor import colored
import inspect
import traceback
import requests  

class ColorfulLogger:
    """
    Логгер с красивыми цветными сообщениями и алертами в Telegram.
    
    Атрибуты:
    service_name (str): Название микросервиса.
    tg_api_alert (str): Токен Telegram-бота.
    tg_chat_id_alert (str): Идентификатор чата для отправки алертов.
    log_file (str): Путь к файлу для записи логов.
    custom_format (str): Формат сообщений в логах.
    
    Методы:
    log(level, message, *args): Записывает лог с заданным уровнем и сообщением.
    info(message, *args): Логирует информационные сообщения.
    debug(message, *args): Логирует отладочные сообщения.
    warning(message, *args): Логирует предупреждения.
    error(message, *args): Логирует ошибки и отправляет алерты в Telegram.
    critical(message, *args): Логирует критические ошибки и отправляет алерты в Telegram.
    exception(message, *args): Логирует исключения и отправляет алерты с трассировкой в Telegram.
    """

    def __init__(self, log_file="logs.log", custom_format=None, config=None):
        """
        Инициализация логгера.
        
        :param log_file: Путь к файлу логов (по умолчанию "logs.log").
        :param custom_format: Формат логов (по умолчанию None).
        :param config: Конфигурация с параметрами service_name, tg_bot и tg_id_alert.
        """
        self.config = config
        self.service_name = self.config.service_name
        self.tg_api_alert = self.config.tg_bot
        self.tg_chat_id_alert = self.config.tg_id_alert
        self.log_file = log_file
        self.custom_format = custom_format
        self._setup_logger()

    def _setup_logger(self):
        """Настройка логгера и файлового обработчика."""
        self.logger = logging.getLogger("ColorfulLogger")
        self.logger.setLevel(logging.DEBUG)

        file_handler = logging.FileHandler(self.log_file, mode="a", encoding="utf-8")
        file_handler.setLevel(logging.DEBUG)
        
        log_format = self.custom_format or "%(asctime)s [%(levelname)s] %(message)s"
        file_formatter = logging.Formatter(log_format, datefmt="%Y-%m-%d %H:%M:%S")
        file_handler.setFormatter(file_formatter)

        if self.logger.handlers:
            self.logger.handlers.clear()
        self.logger.addHandler(file_handler)

    def _send_telegram_alert(self, message: str):
        """
        Отправляет алерт в Telegram.
        
        :param message: Сообщение, которое нужно отправить в чат.
        """
        if not self.tg_api_alert or not self.tg_chat_id_alert:
            return  

        url = f"https://api.telegram.org/bot{self.tg_api_alert}/sendMessage"
        payload = {
            "chat_id": self.tg_chat_id_alert,
            "text": message
        }
        try:
            response = requests.post(url, data=payload)
            if not response.ok:
                self.logger.error("Не удалось отправить алерт в Telegram.")
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка при отправке алерта в Telegram: {e}")

    def log(self, level: str, message: str, *args):
        """
        Логирует сообщение с заданным уровнем и форматирует его.

        :param level: Уровень логирования (например, INFO, DEBUG).
        :param message: Сообщение для логирования.
        :param args: Дополнительные параметры для форматирования сообщения.
        """
        color_map = {
            "INFO": "green",
            "DEBUG": "blue",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "magenta",
        }

        if level not in color_map:
            raise ValueError(f"Unsupported log level: {level}")

        time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        frame = inspect.currentframe().f_back
        filename = frame.f_code.co_filename
        lineno = frame.f_lineno
        func_name = frame.f_code.co_name

        formatted_message = message % args if args else message
        colored_message = f"{time_str} [{level}] {formatted_message} (Service: {self.service_name}, File: {filename}, Line: {lineno}, Function: {func_name})"
        
        print(colored(colored_message, color_map[level]))


        if level == "INFO":
            self.logger.info(formatted_message)
        elif level == "DEBUG":
            self.logger.debug(formatted_message)
        elif level == "WARNING":
            self.logger.warning(formatted_message)
        elif level == "ERROR":
            self.logger.error(formatted_message)
            if self.tg_api_alert:  
                self._send_telegram_alert(f"🚨 Ошибка в сервисе {self.service_name}: {formatted_message}")
        elif level == "CRITICAL":
            self.logger.critical(formatted_message)
            if self.tg_api_alert:  
                self._send_telegram_alert(f"🔥 Критическая ошибка в сервисе {self.service_name}: {formatted_message}")

    def info(self, message: str, *args):
        """Логирует информационное сообщение."""
        self.log("INFO", message, *args)

    def debug(self, message: str, *args):
        """Логирует отладочное сообщение."""
        self.log("DEBUG", message, *args)

    def warning(self, message: str, *args):
        """Логирует предупреждающее сообщение."""
        self.log("WARNING", message, *args)

    def error(self, message: str, *args):
        """Логирует ошибку и отправляет алерт в Telegram."""
        self.log("ERROR", message, *args)

    def critical(self, message: str, *args):
        """Логирует критическую ошибку и отправляет алерт в Telegram."""
        self.log("CRITICAL", message, *args)

    def exception(self, message: str, *args):
        """
        Логирует исключение с трассировкой и отправляет алерт в Telegram.
        
        :param message: Сообщение, описывающее исключение.
        :param args: Дополнительные параметры для форматирования сообщения.
        """
        error_message = message % args if args else message
        tb = traceback.format_exc()
        full_message = f"{error_message}\n{tb}"
        self.error(full_message)
        if self.tg_api_alert:  
            self._send_telegram_alert(f"⚠️ Исключение в сервисе {self.service_name}:\n{full_message}")

if __name__ == "__main__":
    config = {
        "service_name": "MyService",  
        "tg_bot": "6566841078:AAEBN9f2rDsHModMAmmtykWXbki3th9qajI",   #@ext_test_bot
        "tg_id_alert": "635571791" #Тока попробуйте мне в личку алертить !! СВОЛОЧИ ! 
    }

    logger = ColorfulLogger(custom_format="%(asctime)s [%(levelname)s] %(message)s [%(filename)s:%(lineno)d]", config=config)
    

    logger.info("Это информационное сообщение.")
    logger.debug("Это сообщение для отладки.")
    logger.warning("Это предупреждающее сообщение.")
    logger.error("Ошибка с параметрами: %s", "value")
    
    try:
        1 / 0
    except ZeroDivisionError:
        logger.exception("Произошло исключение!")
