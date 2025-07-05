import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.views import process_transactions_for_main_page


@pytest.fixture
def mock_transactions_df():
    """
    Фикстура для DataFrame с тестовыми транзакциями, имитирующими operations.xls.
    В 'Сумма платежа' используем отрицательные значения для расходов.
    """
    data = {
        "Дата операции": [
            "01.07.2024 10:00:00",
            "02.07.2024 11:00:00",
            "03.07.2024 12:00:00",
            "04.07.2024 13:00:00",
            "05.07.2024 14:00:00",
            "05.07.2024 15:00:00",
            "05.07.2024 16:00:00",
            "05.07.2024 17:00:00",
            "05.07.2024 18:00:00",
            "06.07.2024 09:00:00",  # Новая транзакция для проверки граничных условий
        ],
        "Дата платежа": [
            "01.07.2024",
            "02.07.2024",
            "03.07.2024",
            "04.07.2024",
            "05.07.2024",
            "05.07.2024",
            "05.07.2024",
            "05.07.2024",
            "05.07.2024",
            "06.07.2024",
        ],
        "Номер карты": [
            "*1111",
            "*2222",
            "*1111",
            "*3333",
            "*1111",
            "*2222",
            "*1111",
            "*3333",
            "*1111",
            "*1111",
        ],
        "Статус": ["OK", "OK", "OK", "OK", "OK", "OK", "FAILED", "OK", "OK", "OK"],
        "Сумма операции": [
            -100.00,
            -200.00,
            -150.00,
            -50.00,
            -300.00,
            -1000.00,
            -500.00,
            -400.00,
            -700.00,
            5000.00,  # Положительная сумма, как зачисление
        ],
        "Валюта операции": ["RUB", "RUB", "RUB", "RUB", "RUB", "RUB", "RUB", "RUB", "RUB", "RUB"],
        "Сумма платежа": [
            -100.00,
            -200.00,
            -150.00,
            -50.00,
            -300.00,
            -1000.00,
            -500.00,  # Эта сумма должна быть проигнорирована т.к. FAILED статус
            -400.00,
            -700.00,
            5000.00,  # Зачисление, не расход
        ],
        "Валюта платежа": ["RUB", "RUB", "RUB", "RUB", "RUB", "RUB", "RUB", "RUB", "RUB", "RUB"],
        "Кешбэк": ["1,00", "2,00", "1,50", "0,50", "3,00", "10,00", "5,00", "4,00", "7,00", "0,00"],
        "Категория": [
            "Еда",
            "Транспорт",
            "Развлечения",
            "Продукты",
            "Кафе",
            "Путешествия",
            "Здоровье",
            "Образование",
            "Магазины",
            "Зарплата",
        ],
        "MCC": ["5812", "4111", "7832", "5411", "5814", "4722", "8099", "8299", "5311", "1234"],
        "Описание": [
            "Обед в кафе",
            "Поездка на автобусе",
            "Билет в кино",
            "Покупка в магазине",
            "Кофе в Старбакс",
            "Авиабилеты",
            "Поход к врачу (FAILED)",
            "Курсы программирования",
            "Покупки одежды",
            "Зарплата",
        ],
        "Бонусы (включая кэшбэк)": ["1,00", "2,00", "1,50", "0,50", "3,00", "10,00", "5,00", "4,00", "7,00", "0,00"],
        "Округление на инвесткопилку": [
            "0,00",
            "0,00",
            "0,00",
            "0,00",
            "0,00",
            "0,00",
            "0,00",
            "0,00",
            "0,00",
            "0,00",
        ],
        "Сумма операции с округлением": [
            -100.00,
            -200.00,
            -150.00,
            -50.00,
            -300.00,
            -1000.00,
            -500.00,
            -400.00,
            -700.00,
            5000.00,
        ],
    }
    df = pd.DataFrame(data)
    return df


@patch("src.utils.load_transactions_from_excel")
@patch("src.utils.load_user_settings")
@patch("src.utils.get_currency_rates")
@patch("src.utils.get_stock_prices")
def test_process_transactions_for_main_page_success(
    mock_get_stock_prices: MagicMock,
    mock_get_currency_rates: MagicMock,
    mock_load_user_settings: MagicMock,
    mock_load_transactions_from_excel: MagicMock,
    mock_transactions_df: pd.DataFrame,
):
    """
    Тест успешной генерации JSON-ответа для главной страницы.
    """
    mock_load_transactions_from_excel.return_value = mock_transactions_df
    mock_load_user_settings.return_value = {
        "user_currencies": ["USD", "EUR"],
        "user_stocks": ["AAPL", "GOOGL"],
    }
    mock_get_currency_rates.return_value = [
        {"currency": "USD", "rate": 90.0},
        {"currency": "EUR", "rate": 100.0},
    ]
    mock_get_stock_prices.return_value = [
        {"stock": "AAPL", "price": 150.0},
        {"stock": "GOOGL", "price": 2500.0},
    ]

    date_str = "2024-07-05 15:30:00"  # Дата, до которой включаем транзакции
    json_response = process_transactions_for_main_page(date_str)
    response_data = json.loads(json_response)

    assert response_data["greeting"] == "Добрый день"
    assert len(response_data["cards"]) == 3  # *1111, *2222, *3333
    assert response_data["currency_rates"] == [
        {"currency": "USD", "rate": 90.0},
        {"currency": "EUR", "rate": 100.0},
    ]
    assert response_data["stock_prices"] == [
        {"stock": "AAPL", "price": 150.0},
        {"stock": "GOOGL", "price": 2500.0},
    ]

    # Проверка данных по картам (транзакции до 2024-07-05 15:30:00, статус OK, расходы)
    # *1111: -100, -150, -300, -700. Сумма = 1250.0. Кешбэк: 1.0, 1.5, 3.0, 7.0. Сумма = 12.5
    # *2222: -200, -1000. Сумма = 1200.0. Кешбэк: 2.0, 10.0. Сумма = 12.0
    # *3333: -50, -400. Сумма = 450.0. Кешбэк: 0.5, 4.0. Сумма = 4.5

    card_1111_data = next(item for item in response_data["cards"] if item["last_digits"] == "1111")
    assert card_1111_data["total_spent"] == 1250.00
    assert card_1111_data["cashback"] == 12.50

    card_2222_data = next(item for item in response_data["cards"] if item["last_digits"] == "2222")
    assert card_2222_data["total_spent"] == 1200.00
    assert card_2222_data["cashback"] == 12.00

    card_3333_data = next(item for item in response_data["cards"] if item["last_digits"] == "3333")
    assert card_3333_data["total_spent"] == 450.00
    assert card_3333_data["cashback"] == 4.50

    # Проверка топ-5 транзакций (только успешные, отрицательные суммы, по модулю)
    # Все транзакции до 2024-07-05 15:30:00, статус OK, отрицательные суммы:
    # Путешествия: -1000
    # Магазины: -700
    # Кафе: -300
    # Транспорт: -200
    # Развлечения: -150
    # Продукты: -100
    # Продукты: -50
    # Образование: -400 (статус OK)

    top_transactions = response_data["top_transactions"]
    assert len(top_transactions) == 5
    assert top_transactions[0]["amount"] == 1000.00
    assert top_transactions[1]["amount"] == 700.00
    assert top_transactions[2]["amount"] == 400.00
    assert top_transactions[3]["amount"] == 300.00
    assert top_transactions[4]["amount"] == 200.00


@patch("src.utils.load_transactions_from_excel")
def test_process_transactions_for_main_page_no_transactions(
    mock_load_transactions_from_excel: MagicMock,
):
    """
    Тест сценария, когда нет транзакций или они не соответствуют фильтрам.
    """
    mock_load_transactions_from_excel.return_value = pd.DataFrame(
        columns=[
            "Дата операции",
            "Дата платежа",
            "Номер карты",
            "Статус",
            "Сумма операции",
            "Валюта операции",
            "Сумма платежа",
            "Валюта платежа",
            "Кешбэк",
            "Категория",
            "MCC",
            "Описание",
            "Бонусы (включая кэшбэк)",
            "Округление на инвесткопилку",
            "Сумма операции с округлением",
        ]
    )

    date_str = "2024-07-05 10:00:00"
    json_response = process_transactions_for_main_page(date_str)
    response_data = json.loads(json_response)

    assert response_data["greeting"] == "Доброе утро"
    assert response_data["cards"] == []
    assert response_data["top_transactions"] == []
    assert response_data["currency_rates"] == []
    assert response_data["stock_prices"] == []


@patch("src.utils.load_transactions_from_excel", side_effect=FileNotFoundError("Test file not found"))
def test_process_transactions_for_main_page_file_error(
    mock_load_transactions_from_excel: MagicMock,
):
    """
    Тест обработки ошибки при загрузке файла Excel.
    """
    date_str = "2024-07-05 10:00:00"
    json_response = process_transactions_for_main_page(date_str)
    response_data = json.loads(json_response)
    assert "error" in response_data
    assert "Test file not found" in response_data["error"]
