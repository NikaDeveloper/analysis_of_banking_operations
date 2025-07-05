import pandas as pd
import requests
import json
import logging
import os
from dotenv import load_dotenv

load_dotenv()

API_KEY_EXCHANGE = os.getenv("API_KEY_EXCHANGE")
API_KEY_STOCK = os.getenv("API_KEY_STOCK")

API_EXCHANGE_URL = r"https://api.apilayer.com/exchangerates_data/latest" # Изменил на latest, так как convert - это другая функция.
API_TWELVEDATA_QUOTE_URL = r"https://api.twelvedata.com/quote"
API_TWELVEDATA_TIME_SERIES_URL = r"https://api.twelvedata.com/time_series"


def get_exchange_rates(currencies: list, base_currency: str = "RUB") -> list:
    """
    Получает текущие курсы обмена для заданных валют относительно базовой валюты.
    """
    if not API_KEY_EXCHANGE:
        logging.error("API_KEY_EXCHANGE не установлен. Невозможно получить курсы валют.")
        return []

    symbols = ",".join(currencies)
    params = {"base": base_currency, "symbols": symbols}
    headers = {"apikey": API_KEY_EXCHANGE}

    logging.info(f"Отправка запроса на: {API_EXCHANGE_URL} с параметрами: {params}")
    try:
        response = requests.get(API_EXCHANGE_URL, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Полученные сырые курсы: {data.get('rates')}")

        if data.get("success"):
            rates_list = []
            for currency, rate in data["rates"].items():
                rates_list.append({
                    "base": base_currency,
                    "target": currency,
                    "rate": rate
                })
            return rates_list
        else:
            logging.warning(f"Ошибка при получении курсов валют: {data.get('error', 'Неизвестная ошибка API')}")
            return []

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса к API курсов валют: {e}")
        return []
    except Exception as e:
        logging.critical(f"Непредвиденная ошибка при обработке курсов валют: {e}", exc_info=True)
        return []

def get_stock_prices(stocks: list) -> list:
    """
    Получает текущие цены для заданных акций.
    """
    if not API_KEY_STOCK:
        logging.error("API_KEY_STOCK не установлен. Невозможно получить цены акций.")
        return []

    symbols = ",".join(stocks)
    params = {"symbol": symbols, "apikey": API_KEY_STOCK}

    logging.info(f"Отправка запроса на Twelve Data Quote API: {API_TWELVEDATA_QUOTE_URL} с параметрами: {params}")
    try:
        response = requests.get(API_TWELVEDATA_QUOTE_URL, params=params)
        response.raise_for_status()
        data = response.json()
        logging.info(f"Полученные сырые данные по акциям: {data}")

        prices = []
        if isinstance(data, dict):
            # Если вернулся один объект или словарь ошибок
            if "code" in data and data["code"] != 200: # Проверяем, есть ли код ошибки, который не 200 (успех)
                logging.warning(f"Ошибка при получении данных по акции {data.get('symbol', 'unknown')}: {data.get('message', 'Неизвестная ошибка')}")
                # Если это ошибка для конкретной акции, но не для всего запроса, продолжаем
            elif "symbol" in data: # Одиночный результат
                if data.get("close"):
                    prices.append({
                        "stock": data["symbol"],
                        "price": float(data["close"])
                    })
                else:
                    logging.warning(f"Данные для акции {data['symbol']} не найдены или имеют некорректный формат в ответе API.")
            else:
                for symbol, stock_data in data.items():
                    if isinstance(stock_data, dict) and stock_data.get("close"):
                        prices.append({
                            "stock": symbol,
                            "price": float(stock_data["close"])
                        })
                    else:
                        logging.warning(f"Данные для акции {symbol} не найдены или имеют некорректный формат в ответе API.")
        else:
            logging.warning(f"Неожиданный формат ответа от API акций: {data}")
            return []

        return prices
    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка запроса к API цен на акции: {e}")
        return []
    except Exception as e:
        logging.critical(f"Непредвиденная ошибка при обработке цен на акции: {e}", exc_info=True)
        return []


def simple_search_transactions(transactions: list[dict], search_query: str) -> str:
    """
    Осуществляет поиск транзакций по описанию или категории.
    Принимает список словарей транзакций и строку для поиска.
    Возвращает JSON-ответ со всеми транзакциями, содержащими запрос.
    """
    logging.info(f"Начат поиск по запросу: '{search_query}'")
    found_transactions = []
    lower_search_query = search_query.lower()

    for transaction in transactions:
        description = str(transaction.get('Описание', '')).lower()
        category = str(transaction.get('Категория', '')).lower()

        if lower_search_query in description or lower_search_query in category:
            date_val = transaction.get('Дата операции')
            date_formatted = date_val.strftime("%d.%m.%Y") if pd.notna(date_val) else None

            amount_val = transaction.get('Сумма операции')
            amount_formatted = round(amount_val, 2) if pd.notna(amount_val) else None

            category_val = transaction.get('Категория')
            mcc_val = transaction.get('MCC')

            category_display = f"{category_val} ({mcc_val})" if pd.notna(category_val) and pd.notna(mcc_val) else \
                (category_val if pd.notna(category_val) else
                 (mcc_val if pd.notna(mcc_val) else "Неизвестно"))

            description_display = transaction.get('Описание', 'Нет описания')

            found_transactions.append({
                "date": date_formatted,
                "amount": amount_formatted,
                "category": category_display,
                "description": description_display
            })

    logging.info(f"Завершён поиск. Найдено {len(found_transactions)} транзакций по запросу: '{search_query}'")
    return json.dumps(found_transactions, ensure_ascii=False, indent=2)
