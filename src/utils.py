import json
import logging
import os
from datetime import datetime
import pandas as pd


def get_greeting(dt: datetime) -> str:
    """Возвращает приветствие в зависимости от времени суток"""
    hour = dt.hour
    if 5 <= hour < 12:
        return "Доброе утро!"
    elif 12 <= hour < 17:
        return "Добрый день!"
    elif 17 <= hour < 23:
        return "Добрый вечер!"
    else:
        return "Доброй ночи!"


def load_user_settings(filepath: str = None) -> dict:
    """Загружает пользовательские настройки из json файла"""
    if filepath is None:
        current_dir = os.path.dirname(__file__)
        filepath = os.path.join(current_dir, '..', 'data', 'user_settings.json')
        logging.info(f"Используемый путь к user_settings.json: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            settings = json.load(f)
            logging.info(f"Настройки пользователя успешно загружены из {filepath}")
            return settings
    except FileNotFoundError:
        logging.error(f"Файл настроек не найден: {filepath}. Возвращены пустые настройки по умолчанию.")
        return {"user_currencies": [], "user_stocks": []}
    except json.JSONDecodeError:
        logging.error(f"Ошибка декодирования json в файле: {filepath}. Возвращены пустые настройки по умолчанию.")
        return {"user_currencies": [], "user_stocks": []}


def read_excel_data(file_path: str) -> pd.DataFrame:
    """Считывает транзакции из Excel"""
    try:
        df = pd.read_excel(file_path)
        return df
    except FileNotFoundError:
        print(f"Ошибка: Файл '{file_path}' не найден.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Произошла ошибка при чтении Excel файла: {e}")
        return pd.DataFrame()
