import json
import logging
import pandas as pd
from datetime import datetime
import os
from src.utils import get_greeting, load_user_settings
from src.services import get_exchange_rates, get_stock_prices, simple_search_transactions
from src.reports import spending_by_category, get_supermarket_expenses_report


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


CURRENT_DIR = os.path.dirname(__file__)
OPERATIONS_FILEPATH = os.path.join(CURRENT_DIR, '..', 'data', 'operations.xlsx')


def load_operations_data(filepath: str) -> pd.DataFrame:
    """Загружает данные операций из Excel-файла."""
    try:
        df = pd.read_excel(filepath, sheet_name=None)

        combined_df = pd.DataFrame()
        for sheet_name, sheet_df in df.items():
            combined_df = pd.concat([combined_df, sheet_df], ignore_index=True)

        logging.info(f"Данные операций успешно загружены из {filepath}")

        date_col_name = None
        for col in ['Дата операции', 'Дата', 'Date']:
            if col in combined_df.columns:
                date_col_name = col
                break

        if date_col_name:
            combined_df[date_col_name] = pd.to_datetime(combined_df[date_col_name], format='%d.%m.%Y %H:%M:%S', errors='coerce')
            combined_df.dropna(subset=[date_col_name], inplace=True)
        else:
            logging.warning("Колонка с датой не найдена в файле операций. Проверьте названия колонок.")
            return pd.DataFrame()

        logging.info(f"Колонки, загруженные из Excel: {combined_df.columns.tolist()}")

        return combined_df

    except FileNotFoundError:
        logging.error(f"Файл операций не найден: {filepath}")
        return pd.DataFrame()
    except Exception as e:
        logging.critical(f"Ошибка при загрузке данных операций из Excel: {e}", exc_info=True)
        return pd.DataFrame()


def filter_operations_by_month(df: pd.DataFrame, end_date_str: str) -> pd.DataFrame:
    """
    Фильтрует DataFrame операций, оставляя данные с начала месяца,
    на который выпадает end_date_str, по саму end_date_str.
    """
    try:
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")
        start_of_month = end_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        if 'Дата операции' not in df.columns or not pd.api.types.is_datetime64_any_dtype(df['Дата операции']):
            logging.error("Колонка 'Дата операции' отсутствует или не имеет корректного типа datetime.")
            return pd.DataFrame()

        filtered_df = df[(df['Дата операции'] >= start_of_month) & (df['Дата операции'] <= end_date)].copy()
        logging.info(
            f"Отфильтрованы операции с {start_of_month.strftime('%Y-%m-%d')} по {end_date.strftime('%Y-%m-%d')}.")
        return filtered_df
    except ValueError:
        logging.error(f"Некорректный формат входной даты: {end_date_str}. Ожидается YYYY-MM-DD HH:MM:SS.")
        return pd.DataFrame()
    except Exception as e:
        logging.critical(f"Ошибка при фильтрации данных операций: {e}", exc_info=True)
        return pd.DataFrame()


def analyze_card_data(df: pd.DataFrame) -> list:
    """
    Анализирует данные по картам: последние 4 цифры, общая сумма расходов, кешбэк.
    """
    card_data = []
    if 'Номер карты' not in df.columns or 'Сумма операции' not in df.columns:
        logging.warning("Отсутствуют необходимые колонки ('Номер карты' или 'Сумма операции') для анализа карт.")
        return []

    df_copy = df.copy()
    df_copy['Сумма операции'] = pd.to_numeric(df_copy['Сумма операции'], errors='coerce')
    df_copy.dropna(subset=['Сумма операции'], inplace=True)

    df_filtered_expenses = df_copy[df_copy['Сумма операции'] < 0].copy()

    if df_filtered_expenses.empty:
        logging.info("Нет расходных операций для анализа по картам в отфильтрованном диапазоне.")
        return []

    grouped_by_card = df_filtered_expenses.groupby('Номер карты')

    for card_num, group in grouped_by_card:
        last_digits = str(card_num)[-4:] if pd.notna(card_num) else "Неизвестно"
        total_spent = abs(group['Сумма операции'].sum())
        cashback = round(total_spent / 100, 2)  # 1 рубль на каждые 100 рублей

        card_data.append({
            "last_digits": last_digits,
            "total_spent": round(total_spent, 2),
            "cashback": cashback
        })

    logging.info(f"Проанализированы данные по {len(card_data)} картам.")
    return card_data


def get_top_transactions(df: pd.DataFrame, top_n: int = 5) -> list:
    """Возвращает топ-N транзакций по сумме платежа."""
    required_cols = [
        'Дата операции',
        'Дата платежа',
        'Номер карты',
        'Статус',
        'Сумма операции',
        'Валюта операции',
        'Сумма платежа',
        'Валюта платежа',
        'Кэшбэк',
        'Категория',
        'MCC',
        'Описание',
        'Бонусы (включая кэшбэк)',
        'Округление на инвесткопилку',
        'Сумма операции с округлением']

    if not all(col in df.columns for col in required_cols):
        missing_cols = [col for col in required_cols if col not in df.columns]
        logging.warning(f"Отсутствуют необходимые колонки ({', '.join(missing_cols)}) для топ-транзакций.")
        return []

    df_copy = df.copy()

    df_copy['Сумма операции'] = pd.to_numeric(df_copy['Сумма операции'], errors='coerce')
    df_copy.dropna(subset=['Сумма операции'], inplace=True)

    df_copy['abs_amount'] = df_copy['Сумма операции'].abs()

    top_transactions_df = df_copy.sort_values(by='abs_amount', ascending=False).head(top_n)

    top_transactions_list = []
    for _, row in top_transactions_df.iterrows():
        category_val = f"{row['Категория']} ({row['MCC']})" if pd.notna(row['Категория']) and pd.notna(row['MCC']) else \
            (row['Категория'] if pd.notna(row['Категория']) else
             (row['MCC'] if pd.notna(row['MCC']) else "Неизвестно"))

        description_val = row['Описание'] if pd.notna(row['Описание']) else "Нет описания"

        top_transactions_list.append({
            "date": row['Дата операции'].strftime("%d.%m.%Y") if pd.notna(row['Дата операции']) else None,
            "amount": round(row['Сумма операции'], 2),
            "category": category_val,
            "description": description_val
        })

    logging.info(f"Сформирован топ-{top_n} транзакций.")
    return top_transactions_list


def generate_main_page_json(date_str: str) -> str:
    """Главная функция для генерации JSON-ответа для главной страницы."""
    response_data = {}

    try:
        dt_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
        response_data["greeting"] = get_greeting(dt_obj)
    except ValueError:
        logging.error(f"Некорректный формат входной даты: {date_str}. Приветствие не сгенерировано.")
        response_data["greeting"] = "Привет!"  # Fallback
    except Exception as e:
        logging.critical(f"Ошибка при генерации приветствия: {e}", exc_info=True)
        response_data["greeting"] = "Привет!"

    all_operations_df = load_operations_data(OPERATIONS_FILEPATH)
    if all_operations_df.empty:
        logging.error("Не удалось загрузить данные операций. Разделы карт и транзакций будут пусты.")
        response_data["cards"] = []
        response_data["top_transactions"] = []
    else:
        filtered_operations_df = filter_operations_by_month(all_operations_df, date_str)
        if filtered_operations_df.empty:
            logging.warning("В указанном диапазоне дат не найдено операций.")
            response_data["cards"] = []
            response_data["top_transactions"] = []
        else:
            response_data["cards"] = analyze_card_data(filtered_operations_df)

            response_data["top_transactions"] = get_top_transactions(filtered_operations_df, top_n=5)

    user_settings = load_user_settings()
    user_currencies = user_settings.get("user_currencies", [])
    user_stocks = user_settings.get("user_stocks", [])

    if user_currencies:
        response_data["currency_rates"] = get_exchange_rates(user_currencies)
    else:
        logging.warning("Не указаны валюты для отслеживания в user_settings.json.")
        response_data["currency_rates"] = []

    if user_stocks:
        response_data["stock_prices"] = get_stock_prices(user_stocks)
    else:
        logging.warning("Не указаны акции для отслеживания в user_settings.json.")
        response_data["stock_prices"] = []

    return json.dumps(response_data, ensure_ascii=False, indent=2)


def generate_search_json(search_query: str, date_str: str) -> str:
    """
    Генерирует JSON-ответ для страницы поиска.
    Принимает строку для поиска и строку с датой (для фильтрации операций).
    """
    all_operations_df = load_operations_data(OPERATIONS_FILEPATH)
    if all_operations_df.empty:
        logging.error("Не удалось загрузить данные операций для поиска.")
        return json.dumps({"search_results": []}, ensure_ascii=False, indent=2)


    filtered_operations_df = filter_operations_by_month(all_operations_df, date_str)
    if filtered_operations_df.empty:
        logging.warning("В указанном диапазоне дат не найдено операций для поиска.")
        return json.dumps({"search_results": []}, ensure_ascii=False, indent=2)

    transactions_list = filtered_operations_df.to_dict('records')

    search_results_json = simple_search_transactions(transactions_list, search_query)

    # Так как simple_search_transactions уже возвращает JSON,
    # мы просто возвращаем его, возможно, обернув в корневой объект,
    # если вы хотите добавить другие метаданные поиска.
    # Для простоты пока вернем как есть, но это можно изменить.
    # Если simple_search_transactions возвращает просто список, то нужно:
    # return json.dumps({"search_results": search_results_list}, ensure_ascii=False, indent=2)

    return search_results_json


if __name__ == "__main__":
    test_date = "2021-12-31 23:59:59" # Например, конец дня 31 декабря 2021

    print(f"\nГенерация JSON для даты: {test_date}")
    main_page_json = generate_main_page_json(test_date)
    print("\nСформированный JSON-ответ для главной страницы:")
    print(main_page_json)

    print(f"\n--- Тестирование простого поиска ---")
    search_query_example = "супермаркеты" # Пример поискового запроса
    search_date_example = "2021-12-31 23:59:59" # Дата, для которой фильтруются операции перед поиском

    print(f"\nВыполнение поиска для запроса: '{search_query_example}' на дату: {search_date_example}")
    search_json_response = generate_search_json(search_query_example, search_date_example)
    print("\nСформированный JSON-ответ для поиска:")
    print(search_json_response)

    search_query_example_2 = "перевод"
    print(f"\nВыполнение поиска для запроса: '{search_query_example_2}' на дату: {search_date_example}")
    search_json_response_2 = generate_search_json(search_query_example_2, search_date_example)
    print("\nСформированный JSON-ответ для поиска:")
    print(search_json_response_2)

    # --- ДОБАВЬТЕ ЭТОТ БЛОК ДЛЯ ТЕСТИРОВАНИЯ ОТЧЕТОВ ---
    print(f"\n--- Тестирование отчетов ---")
    all_operations_df_for_reports = load_operations_data(OPERATIONS_FILEPATH)

    if not all_operations_df_for_reports.empty:
        print(f"\nГенерация отчета 'Траты по категории' (Без файла):")
        # Вызов функции с декоратором без параметра
        report_df_default = spending_by_category(
            all_operations_df_for_reports,
            "Супермаркеты",
            "2021-12-31 23:59:59"
        )
        print(f"Результат функции (DataFrame): {len(report_df_default)} строк.")
        # Декоратор уже записал этот результат в файл.

        print(f"\nГенерация отчета 'Траты по категории' (С указанием файла):")
        # Вызов функции с декоратором, который имеет жестко заданный путь к файлу
        report_df_supermarkets = get_supermarket_expenses_report(
            all_operations_df_for_reports,
            "2021-12-31 23:59:59"
        )
        print(f"Результат функции (DataFrame): {len(report_df_supermarkets)} строк.")
        # Декоратор уже записал этот результат в файл.

        print(f"\nГенерация отчета для категории 'ЖКХ' (Без файла):")
        report_df_housing = spending_by_category(
            all_operations_df_for_reports,
            "ЖКХ", # Проверьте, есть ли такая категория в ваших данных
            "2021-12-31 23:59:59"
        )
        print(f"Результат функции (DataFrame): {len(report_df_housing)} строк.")
    else:
        print("Не удалось загрузить данные операций для тестирования отчетов.")
