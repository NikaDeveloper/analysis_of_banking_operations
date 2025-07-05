import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Union

import pandas as pd

from src.utils import (
    get_currency_rates,
    get_greeting,
    get_stock_prices,
    load_transactions_from_excel,
    load_user_settings,
)

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)


def process_transactions_for_main_page(date_str: str, file_path: str = "operations.xlsx") -> str:
    """
    Обрабатывает транзакции для главной страницы, генерируя JSON-ответ.

    Args:
        date_str: Строка с датой и временем в формате YYYY-MM-DD HH:MM:SS.
        file_path: Путь к Excel-файлу с транзакциями.

    Returns:
        JSON-строка с данными для главной страницы.
    """
    try:
        all_transactions = load_transactions_from_excel(file_path)
        settings = load_user_settings()

        input_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        start_of_month = input_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Фильтрация транзакций за текущий месяц до входной даты
        filtered_transactions = all_transactions[
            (all_transactions["Дата операции"] >= start_of_month)
            & (all_transactions["Дата операции"] <= input_date)
            & (all_transactions["Статус"] == "OK")  # Учитываем только успешные транзакции
        ].copy()  # Делаем копию, чтобы избежать SettingWithCopyWarning

        greeting = get_greeting(date_str)

        # Данные по картам
        cards_data: List[Dict[str, Union[str, float]]] = []

        unique_cards = filtered_transactions["Номер карты"].unique()
        for card_number in unique_cards:
            card_transactions = filtered_transactions[filtered_transactions["Номер карты"] == card_number]

            total_spent = (
                card_transactions[card_transactions["Сумма платежа"] < 0]["Сумма платежа"].fillna(0).abs().sum()
            )

            cashback_series = card_transactions["Кэшбэк"]
            # Преобразуем NaN в 0 перед суммированием, чтобы гарантировать числовой результат
            cashback = cashback_series.fillna(0).sum()
            # Убедимся, что кэшбэк положительный, если он был рассчитан
            if cashback < 0:
                cashback = abs(cashback)

            cards_data.append(
                {
                    "last_digits": str(card_number).replace("*", ""),  # Удаляем '*' из номера карты
                    "total_spent": round(float(total_spent), 2),
                    "cashback": round(float(cashback), 2),
                }
            )

        # Топ-5 транзакций
        # Исключаем транзакции с положительными суммами (зачисления)
        # и используем абсолютное значение для сортировки по "расходам".
        top_transactions_df = filtered_transactions[
            filtered_transactions["Сумма платежа"] < 0
        ].copy()  # Создаем копию для изменения

        # Создаем новую колонку для сортировки по абсолютному значению
        top_transactions_df["Abs Sum"] = top_transactions_df["Сумма платежа"].abs()
        top_transactions_df = top_transactions_df.sort_values(by="Abs Sum", ascending=False)

        top_5_transactions = []
        for _, row in top_transactions_df.head(5).iterrows():
            top_5_transactions.append(
                {
                    "date": row["Дата операции"].strftime("%d.%m.%Y"),
                    "amount": round(float(row["Сумма платежа"].abs()), 2),  # Берем абсолютное значение
                    "category": row["Категория"],
                    "description": row["Описание"],
                }
            )

        # Курсы валют
        user_currencies = settings.get("user_currencies", [])
        currency_rates = get_currency_rates(user_currencies)

        # Цены акций
        user_stocks = settings.get("user_stocks", [])
        stock_prices = get_stock_prices(user_stocks)

        response_data = {
            "greeting": greeting,
            "cards": cards_data,
            "top_transactions": top_5_transactions,
            "currency_rates": currency_rates,
            "stock_prices": stock_prices,
        }

        logger.info("JSON-ответ для главной страницы успешно сгенерирован.")
        return json.dumps(response_data, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Ошибка при обработке транзакций для главной страницы: {e}")
        return json.dumps({"error": str(e)}, ensure_ascii=False, indent=2)
