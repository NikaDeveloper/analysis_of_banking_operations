import pytest
from unittest.mock import patch, mock_open
import pandas as pd
from datetime import datetime
import json

import requests

from src.utils import (
    load_transactions_from_excel,
    get_greeting,
    get_currency_rates,
    get_stock_prices,
    load_user_settings,
)


# Тесты для load_transactions_from_excel
@patch("pandas.read_excel")
def test_load_transactions_from_excel_success(mock_read_excel):
    """Тест успешной загрузки транзакций из Excel"""
    # Подготовка мок данных
    mock_data = pd.DataFrame(
        {
            "Дата операции": ["01.01.2023", "02.01.2023"],
            "Дата платежа": ["01.01.2023", "02.01.2023"],
            "Сумма операции": ["100,50", "200,75"],
            "Кешбэк": ["1,5", "2,75"],
        }
    )
    mock_read_excel.return_value = mock_data

    # Вызов функции
    result = load_transactions_from_excel("test.xlsx")

    # Проверки
    assert isinstance(result, pd.DataFrame)
    assert len(result) == 2
    assert "Дата операции" in result.columns
    assert result["Сумма операции"].dtype == float
    assert result["Кешбэк"].dtype == float


@patch("pandas.read_excel")
def test_load_transactions_from_excel_file_not_found(mock_read_excel):
    """Тест обработки ошибки отсутствия файла"""
    mock_read_excel.side_effect = FileNotFoundError("File not found")

    with pytest.raises(FileNotFoundError):
        load_transactions_from_excel("nonexistent.xlsx")


# Тесты для get_greeting
def test_get_greeting_morning():
    """Тест приветствия для утра"""
    assert get_greeting("2023-01-01 08:00:00") == "Доброе утро"


def test_get_greeting_day():
    """Тест приветствия для дня"""
    assert get_greeting("2023-01-01 14:00:00") == "Добрый день"


def test_get_greeting_evening():
    """Тест приветствия для вечера"""
    assert get_greeting("2023-01-01 20:00:00") == "Добрый вечер"


def test_get_greeting_night():
    """Тест приветствия для ночи"""
    assert get_greeting("2023-01-01 02:00:00") == "Доброй ночи"


def test_get_greeting_invalid_format():
    """Тест обработки неверного формата времени"""
    with pytest.raises(ValueError):
        get_greeting("invalid-time-format")


# Тесты для get_currency_rates
@patch("requests.get")
@patch.dict("os.environ", {"EXCHANGE_RATE_API_KEY": "test_api_key"})
def test_get_currency_rates_success(mock_get):
    """Тест успешного получения курсов валют"""
    # Подготовка мок ответа
    mock_response = mock_get.return_value
    mock_response.raise_for_status.return_value = None
    mock_response.json.return_value = {
        "rates": {"USD": 0.014, "EUR": 0.012},
        "base": "RUB",
    }

    # Вызов функции
    result = get_currency_rates(["USD", "EUR"])

    # Проверки
    assert len(result) == 2
    assert result[0]["currency"] == "USD"
    assert isinstance(result[0]["rate"], float)
    assert result[1]["currency"] == "EUR"
    assert isinstance(result[1]["rate"], float)


@patch("requests.get")
@patch.dict("os.environ", {"EXCHANGE_RATE_API_KEY": "test_api_key"})
def test_get_currency_rates_api_error(mock_get):
    """Тест обработки ошибки API"""
    mock_get.side_effect = requests.exceptions.RequestException("API error")

    result = get_currency_rates(["USD", "EUR"])
    assert result == []


@patch.dict("os.environ", {}, clear=True)
def test_get_currency_rates_no_api_key():
    """Тест отсутствия API ключа"""
    result = get_currency_rates(["USD", "EUR"])
    assert result == []


# Тесты для get_stock_prices
@patch("requests.get")
@patch.dict("os.environ", {"FINNHUB_API_KEY": "test_api_key"})
def test_get_stock_prices_success(mock_get):
    """Тест успешного получения цен акций"""
    # Подготовка мок ответов
    mock_response1 = mock_get.return_value
    mock_response1.raise_for_status.return_value = None
    mock_response1.json.return_value = {"c": 150.25}

    # Вызов функции
    result = get_stock_prices(["AAPL"])

    # Проверки
    assert len(result) == 1
    assert result[0]["stock"] == "AAPL"
    assert result[0]["price"] == 150.25


@patch("requests.get")
@patch.dict("os.environ", {"FINNHUB_API_KEY": "test_api_key"})
def test_get_stock_prices_api_error(mock_get):
    """Тест обработки ошибки API для акций"""
    mock_get.side_effect = requests.exceptions.RequestException("API error")

    result = get_stock_prices(["AAPL"])
    assert result == []


@patch.dict("os.environ", {}, clear=True)
def test_get_stock_prices_no_api_key():
    """Тест отсутствия API ключа для акций"""
    result = get_stock_prices(["AAPL"])
    assert result == []


# Тесты для load_user_settings
def test_load_user_settings_success():
    """Тест успешной загрузки пользовательских настроек"""
    test_settings = {"theme": "dark", "currency": "USD"}

    with patch("builtins.open", mock_open(read_data=json.dumps(test_settings))) as mock_file:
        result = load_user_settings()

    assert result == test_settings


def test_load_user_settings_file_not_found():
    """Тест обработки отсутствия файла настроек"""
    with patch("builtins.open", side_effect=FileNotFoundError()):
        result = load_user_settings()
        assert result == {}


def test_load_user_settings_invalid_json():
    """Тест обработки невалидного JSON"""
    with patch("builtins.open", mock_open(read_data="invalid json")):
        result = load_user_settings()
        assert result == {}
