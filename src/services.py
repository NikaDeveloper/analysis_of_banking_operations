import logging
import re
from typing import Any, Dict, List

import pandas as pd

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)


def simple_search(transactions: pd.DataFrame, query: str) -> List[Dict[str, Any]]:
    """
    Выполняет поиск по описанию транзакций.

    Args:
        transactions: DataFrame с транзакциями.
        query: Строка запроса для поиска.

    Returns:
        Список словарей с найденными транзакциями, где даты преобразованы в строки.
    """
    logger.info(f"Начинаем поиск по запросу: '{query}'")

    if transactions.empty:
        logger.info("DataFrame с транзакциями пуст.")
        return []
    if not query:
        logger.info("Запрос пустой")
        return []

    # Преобразование запроса для регистронезависимого поиска
    query_lower = query.lower()

    filtered_transactions = transactions[
        transactions["Описание"].astype(str).str.lower().str.contains(query_lower, na=False)
    ].copy()  # Важно сделать копию, чтобы избежать SettingWithCopyWarning

    results = filtered_transactions.to_dict(orient="records")

    # Преобразуем Timestamp объекты в строки для JSON сериализации
    for row in results:
        for key, value in row.items():
            if isinstance(value, pd.Timestamp):
                row[key] = value.strftime("%d.%m.%Y %H:%M:%S")  # Используем тот же формат, что и в файле
            elif pd.isna(value):  # Обработка NaN (Not a Number) для JSON
                row[key] = ""  # JSON не имеет NaN, обычно преобразуется в null

    logger.info(f"Поиск завершен. Найдено {len(results)} транзакций по запросу '{query}'.")
    return results
