import json
import logging
import pandas as pd
from datetime import datetime
from functools import wraps
from typing import Optional, Callable, Any
import os

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


# Декоратор для записи отчетов в файл
def save_report_to_file(filepath: Optional[str] = None) -> Callable:
    """Декоратор для функций, генерирующих отчеты. Записывает возвращаемый результат функции в файл."""

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs) # Выполняем оригинальную функцию

            # Определяем имя файла
            final_filepath = filepath
            if final_filepath is None:
                # Генерируем имя файла по умолчанию: report_func_name_timestamp.json
                current_time_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                default_filename = f"report_{func.__name__}_{current_time_str}.json"
                # Сохраняем в папку 'reports' в корне проекта
                reports_dir = os.path.join(os.path.dirname(__file__), '..', 'reports')
                os.makedirs(reports_dir, exist_ok=True) # Создаем папку, если ее нет
                final_filepath = os.path.join(reports_dir, default_filename)

            # Если результат - DataFrame, преобразуем его в список словарей для JSON
            if isinstance(result, pd.DataFrame):
                data_to_save = result.copy()
                for col in data_to_save.select_dtypes(include=['datetime64[ns]']).columns:
                    data_to_save[col] = data_to_save[col].dt.strftime('%Y-%m-%d %H:%M:%S')
                data_to_save = data_to_save.to_dict(orient='records')
            else:
                data_to_save = result

            try:
                with open(final_filepath, 'w', encoding='utf-8') as f:
                    json.dump(data_to_save, f, ensure_ascii=False, indent=2)
                logging.info(f"Отчет успешно сохранен в файл: {final_filepath}")
            except IOError as e:
                logging.error(f"Ошибка при сохранении отчета в файл {final_filepath}: {e}")
            except Exception as e:
                logging.critical(f"Непредвиденная ошибка при обработке отчета для сохранения: {e}", exc_info=True)

            return result  # Возвращаем оригинальный результат функции
        return wrapper
    return decorator


@save_report_to_file()
def spending_by_category(transactions: pd.DataFrame,
                         category: str,
                         date: Optional[str] = None) -> pd.DataFrame:
    """Возвращает траты по заданной категории за последние три месяца от переданной даты или текущей даты."""
    logging.info(f"Начат расчет трат по категории '{category}'")

    if transactions.empty:
        logging.warning("Пустой DataFrame транзакций передан в spending_by_category.")
        return pd.DataFrame()

    # Определяем конечную дату периода
    end_date: datetime
    if date:
        try:
            end_date = datetime.strptime(date, "%Y-%m-%d %H:%M:%S")
        except ValueError:
            logging.error(f"Некорректный формат входной даты: {date}. Используется текущая дата.")
            end_date = datetime.now()
    else:
        end_date = datetime.now()

    start_date = end_date - pd.DateOffset(months=3)


    if 'Дата операции' not in transactions.columns or not pd.api.types.is_datetime64_any_dtype(transactions['Дата операции']):
        logging.error("Колонка 'Дата операции' отсутствует или не имеет корректного типа datetime. Невозможно отфильтровать по дате.")
        return pd.DataFrame()

    # Фильтруем по дате
    filtered_by_date_df = transactions[
        (transactions['Дата операции'] >= start_date) &
        (transactions['Дата операции'] <= end_date)
    ].copy()

    if filtered_by_date_df.empty:
        logging.info(f"Нет транзакций в диапазоне {start_date.strftime('%Y-%m-%d')} - {end_date.strftime('%Y-%m-%d')}.")
        return pd.DataFrame()

    # Фильтруем по категории
    if 'Категория' not in filtered_by_date_df.columns:
        logging.warning("Колонка 'Категория' отсутствует. Невозможно отфильтровать по категории.")
        return pd.DataFrame()

    filtered_by_category_df = filtered_by_date_df[
        filtered_by_date_df['Категория'].astype(str).str.lower() == category.lower()
    ].copy()

    if filtered_by_category_df.empty:
        logging.info(f"Не найдено трат по категории '{category}' в указанном диапазоне дат.")
        return pd.DataFrame()

    # Оставляем только расходные операции
    if 'Сумма операции' in filtered_by_category_df.columns:
        filtered_by_category_df['Сумма операции'] = pd.to_numeric(filtered_by_category_df['Сумма операции'],
                                                                  errors='coerce')
        filtered_by_category_df.dropna(subset=['Сумма операции'], inplace=True)
        expenses_df = filtered_by_category_df[filtered_by_category_df['Сумма операции'] < 0].copy()
    else:
        logging.warning("Колонка 'Сумма операции' отсутствует. Невозможно отфильтровать расходы.")
        return pd.DataFrame()

    if expenses_df.empty:
        logging.info(f"Нет расходных операций по категории '{category}' в указанном диапазоне дат.")
        return pd.DataFrame()

    logging.info(f"Расчет трат по категории '{category}' завершен. Найдено {len(expenses_df)} расходных операций.")
    return expenses_df[['Дата операции', 'Сумма операции', 'Категория', 'Описание', 'MCC']]


# Декоратор с параметром (указываем имя файла)
@save_report_to_file(filepath=os.path.join(os.path.dirname(__file__), '..', 'reports', 'supermarket_expenses_report.json'))
def get_supermarket_expenses_report(transactions: pd.DataFrame, date: Optional[str] = None) -> pd.DataFrame:
    """Пример использования декоратора с параметром для конкретного отчета."""
    logging.info("Генерация отчета по тратам в супермаркетах.")
    return spending_by_category(transactions, "Супермаркеты", date)
