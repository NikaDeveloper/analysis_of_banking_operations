import json
import logging
from datetime import datetime

import pandas as pd

from src.reports import spending_by_category
from src.services import simple_search
from src.utils import load_transactions_from_excel
from src.views import process_transactions_for_main_page

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)


def main() -> None:
    """
    Основная функция для запуска приложения.
    """
    transactions_file = "operations.xlsx"

    try:
        # Загрузка и предобработка транзакций
        transactions_df = load_transactions_from_excel(transactions_file)
        logger.info("Транзакции успешно загружены для дальнейшей обработки.")

        # Определяем самую позднюю дату в данных для симуляции "текущей" даты
        if not transactions_df.empty and "Дата операции" in transactions_df.columns:
            latest_transaction_date = transactions_df["Дата операции"].max()
            current_datetime_for_app = latest_transaction_date  # Используем последнюю дату транзакции

            # Для main_page_json нам нужна строка с временем
            current_datetime_str_for_main_page = latest_transaction_date.strftime("%Y-%m-%d %H:%M:%S")
            # Для report_date_str нам нужна только дата
            report_date_str_for_report = latest_transaction_date.strftime("%Y-%m-%d")
        else:
            logger.warning(
                "DataFrame с транзакциями пуст или отсутствует колонка 'Дата операции'. "
                "Используем текущую системную дату для отчетов."
            )
            current_datetime_for_app = datetime.now()
            current_datetime_str_for_main_page = current_datetime_for_app.strftime("%Y-%m-%d %H:%M:%S")
            report_date_str_for_report = current_datetime_for_app.strftime("%Y-%m-%d")

        # --- 1. Генерация JSON для главной страницы ---
        logger.info(
            f"\n--- Генерируем JSON-ответ для главной страницы на дату: {current_datetime_str_for_main_page} ---"
        )
        main_page_json = process_transactions_for_main_page(current_datetime_str_for_main_page, transactions_file)
        print(f"JSON для главной страницы:\n{main_page_json}")
        print("-" * 50)

        # --- 2. Выполнение простого поиска ---
        search_query = "лента"
        logger.info(f"\n--- Выполняем простой поиск по запросу: '{search_query}' ---")
        search_results = simple_search(transactions_df, search_query)

        if search_results:
            logger.info(f"Поиск завершен. Найдено {len(search_results)} транзакций по запросу '{search_query}'.")
            print(
                f"Результаты поиска по '{search_query}':\n{json.dumps(search_results, ensure_ascii=False, indent=2)}"
            )
        else:
            logger.info(f"Поиск завершен. Транзакций по запросу '{search_query}' не найдено.")
            print(f"Результаты поиска по '{search_query}': []")
        print("-" * 50)

        # --- 3. Генерация отчета "Траты по категории" ---
        category_for_report = "Супермаркеты"
        # Передаем дату последней транзакции для отчета
        logger.info(
            f"\n--- Генерируем отчет 'Траты по категории' для '{category_for_report}'"
            f" на дату: {report_date_str_for_report} ---"
        )

        spending_report_df = spending_by_category(transactions_df, category_for_report, report_date_str_for_report)

        if not spending_report_df.empty:
            report_data_for_json = spending_report_df.to_dict(orient="records")

            for row in report_data_for_json:
                for key, value in row.items():
                    if isinstance(value, pd.Timestamp):
                        row[key] = value.strftime("%d.%m.%Y %H:%M:%S")
                    elif pd.isna(value):
                        row[key] = None

            print(
                f"Отчет по тратам в категории '{category_for_report}' "
                f"за последние 3 месяца (JSON):\n{json.dumps(report_data_for_json, ensure_ascii=False, indent=2)}"
            )
        else:
            print(f"Отчет по тратам в категории '{category_for_report}' за последние 3 месяца: Нет данных.")
        print("-" * 50)

    except FileNotFoundError as e:
        logger.critical(f"Критическая ошибка в работе приложения: {e}")
    except Exception as e:
        logger.critical(f"Критическая ошибка в работе приложения: {e}")


if __name__ == "__main__":
    main()
