import json
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.views import process_transactions_for_main_page


@patch("src.views.load_transactions_from_excel")
@patch("src.views.load_user_settings")
@patch("src.views.get_currency_rates")
@patch("src.views.get_stock_prices")
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

    date_str = "2024-07-09 15:30:00"  # Дата, до которой включаем транзакции
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


@patch("src.views.load_transactions_from_excel")
@patch("src.views.load_user_settings")
@patch("src.views.get_currency_rates")
@patch("src.views.get_stock_prices")
def test_process_transactions_for_main_page_no_transactions(
    mock_get_stock_prices: MagicMock,
    mock_get_currency_rates: MagicMock,
    mock_load_user_settings: MagicMock,
    mock_load_transactions_from_excel: MagicMock
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

    # Возвращаем пустые настройки пользователя
    mock_load_user_settings.return_value = {
        "user_currencies": [],
        "user_stocks": []
    }

    # Настраиваем моки для функций, которые используют эти настройки
    mock_get_currency_rates.return_value = []
    mock_get_stock_prices.return_value = []

    date_str = "2021-07-05 10:00:00"
    json_response = process_transactions_for_main_page(date_str)
    response_data = json.loads(json_response)

    assert response_data["greeting"] == "Доброе утро"
    assert response_data["cards"] == []
    assert response_data["top_transactions"] == []
    assert response_data["currency_rates"] == []
    assert response_data["stock_prices"] == []

    mock_load_user_settings.assert_called_once()
    mock_get_currency_rates.asser_called_once_with([])
    mock_get_stock_prices.assert_called_once_with([])


@patch("src.views.load_transactions_from_excel", side_effect=FileNotFoundError("Test file not found"))
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
