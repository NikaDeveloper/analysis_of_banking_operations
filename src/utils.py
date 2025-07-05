import json
import logging
import os
from datetime import datetime
from typing import Any, Dict, List, Union

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)


def load_transactions_from_excel(file_path: str) -> pd.DataFrame:
    """
    Загружает данные транзакций из Excel-файла в DataFrame pandas,
    выполняя предобработку колонок.

    Args:
        file_path: Путь к Excel-файлу.

    Returns:
        DataFrame с данными транзакций.
    """
    try:
        df = pd.read_excel(file_path)
        logger.info(f"Транзакции успешно загружены из {file_path}")

        df["Дата операции"] = pd.to_datetime(df["Дата операции"], format="mixed", dayfirst=True, errors="coerce")
        df["Дата платежа"] = pd.to_datetime(df["Дата платежа"], format="mixed", dayfirst=True, errors="coerce")

        # Преобразование числовых колонок, учитывая запятые
        numeric_cols = [
            "Сумма операции",
            "Сумма платежа",
            "Кешбэк",
            "Бонусы (включая кэшбэк)",
            "Округление на инвесткопилку",
            "Сумма операции с округлением",
        ]

        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
                df[col] = df[col].astype(float)
        if "Кешбэк" in df.columns:
            df["Кешбэк"] = df["Кешбэк"].fillna(0.0)

        # Фильтруем строки, где "Дата операции" не удалось спарсить
        df.dropna(subset=["Дата операции"], inplace=True)

        return df
    except FileNotFoundError:
        logger.error(f"Файл не найден: {file_path}")
        raise
    except Exception as e:
        logger.error(f"Ошибка при загрузке и предобработке Excel-файла: {e}")
        raise


def get_greeting(time_str: str) -> str:
    """
    Возвращает приветствие в зависимости от времени.

    Args:
        time_str: Строка с датой и временем в формате YYYY-MM-DD HH:MM:SS.

    Returns:
        Приветствие ("Доброе утро", "Добрый день", "Добрый вечер", "Доброй ночи").
    """
    try:
        dt_object = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        hour = dt_object.hour
        if 5 <= hour < 12:
            return "Доброе утро"
        elif 12 <= hour < 18:
            return "Добрый день"
        elif 18 <= hour < 23:
            return "Добрый вечер"
        else:
            return "Доброй ночи"
    except ValueError as e:
        logger.error(f"Некорректный формат времени: {time_str}. Ошибка: {e}")
        raise


def get_currency_rates(currencies: List[str]) -> List[Dict[str, Union[str, float]]]:
    """
    Получает текущие курсы валют с помощью API.

    Args:
        currencies: Список кодов валют (например, ["USD", "EUR"]).

    Returns:
        Список словарей с названием валюты и ее курсом.
    """
    api_key = os.getenv("EXCHANGE_RATE_API_KEY")
    if not api_key:
        logger.error("API ключ для курсов валют не найден в .env")
        return []

    url = "https://api.apilayer.com/exchangerates_data/latest"
    headers = {"apikey": api_key}
    params = {"symbols": ",".join(currencies), "base": "RUB"}

    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        response.raise_for_status()  # Вызовет исключение для ошибок HTTP
        data = response.json()
        rates = []
        for currency in currencies:
            if currency == "RUB":
                continue  # Игнорируем RUB, так как это базовая валюта
            if currency in data["rates"]:
                rates.append(
                    {"currency": currency, "rate": round(1 / data["rates"][currency], 2)}
                )  # Пересчет из "base" в "symbol"
            else:
                logger.warning(f"Курс для валюты {currency} не найден в ответе API.")
        logger.info(f"Курсы валют успешно получены: {rates}")
        return rates
    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка при запросе курсов валют: {e}")
        return []
    except Exception as e:
        logger.error(f"Неизвестная ошибка при получении курсов валют: {e}")
        return []


def get_stock_prices(stocks: List[str]) -> List[Dict[str, Union[str, float]]]:
    """
    Получает текущие цены акций S&P500 с помощью API Finnhub.io.

    Args:
        stocks: Список тикеров акций (например, ["AAPL", "AMZN"]).

    Returns:
        Список словарей с названием акции и ее ценой.
    """
    api_key = os.getenv("FINNHUB_API_KEY")
    if not api_key:
        logger.error("API ключ для Finnhub.io не найден в .env")
        return []

    stock_prices_data = []
    for stock_symbol in stocks:
        url = f"https://finnhub.io/api/v1/quote?symbol={stock_symbol}&token={api_key}"
        try:
            response = requests.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            if data and data.get("c"):
                stock_prices_data.append({"stock": stock_symbol, "price": round(data["c"], 2)})
            else:
                logger.warning(f"Не удалось получить цену для акции {stock_symbol}.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка при запросе цены акции {stock_symbol}: {e}")
        except Exception as e:
            logger.error(f"Неизвестная ошибка при получении цены акции {stock_symbol}: {e}")
    logger.info(f"Цены акций успешно получены: {stock_prices_data}")
    return stock_prices_data


def load_user_settings(file_path: str = "src/user_settings.json") -> Dict[str, Any]:
    """
    Загружает пользовательские настройки из JSON-файла.

    Args:
        file_path: Путь к файлу user_settings.json.

    Returns:
        Словарь с пользовательскими настройками.
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            settings = json.load(f)
        logger.info(f"Пользовательские настройки загружены из {file_path}")
        return settings
    except FileNotFoundError:
        logger.error(f"Файл пользовательских настроек не найден: {file_path}")
        return {}
    except json.JSONDecodeError as e:
        logger.error(f"Ошибка декодирования JSON в файле настроек: {file_path}. Ошибка: {e}")
        return {}
    except Exception as e:
        logger.error(f"Неизвестная ошибка при загрузке пользовательских настроек: {e}")
        return {}
