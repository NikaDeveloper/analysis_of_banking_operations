import logging
from datetime import datetime, timedelta
from typing import Optional

import pandas as pd

from src.decorators import log_report_to_file

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)


@log_report_to_file()  # Декоратор без параметра (файл по умолчанию)
def spending_by_category(transactions: pd.DataFrame, category: str, date: Optional[str] = None) -> pd.DataFrame:
    """
    Возвращает траты по заданной категории за последние три месяца
    от переданной даты (или текущей даты, если не передана).

    Args:
        transactions: DataFrame с транзакциями.
        category: Название категории.
        date: Опциональная дата в формате YYYY-MM-DD. Если None, используется текущая дата.

    Returns:
        DataFrame с отфильтрованными транзакциями по категории за последние три месяца.
    """
    try:
        if date:
            start_date = datetime.strptime(date, "%Y-%m-%d")
        else:
            start_date = datetime.now()

        three_months_ago = start_date - timedelta(days=90)

        # Фильтруем транзакции по категории, дате, статусу "OK" и только по расходам (Сумма платежа < 0)
        filtered_df = transactions[
            (transactions["Категория"] == category)
            & (transactions["Дата операции"] >= three_months_ago)
            & (transactions["Дата операции"] <= start_date)
            & (transactions["Статус"] == "OK")
            & (transactions["Сумма платежа"] < 0)  # Только расходы (отрицательные значения)
        ].copy()

        logger.info(
            f"Отчет 'Траты по категории' для '{category}' за период "
            f"с {three_months_ago.strftime('%Y-%m-%d')} по {start_date.strftime('%Y-%m-%d')} успешно сгенерирован."
        )
        return filtered_df
    except Exception as e:
        logger.error(f"Ошибка при формировании отчета 'Траты по категории': {e}")
        return pd.DataFrame()
