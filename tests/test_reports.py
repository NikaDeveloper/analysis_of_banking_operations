import pytest
import pandas as pd
from datetime import datetime, timedelta
import os
import json
from unittest.mock import patch, mock_open

from src.reports import spending_by_category, save_report_to_file


@pytest.fixture
def sample_transactions_df():
    """Фикстура, предоставляющая DataFrame с тестовыми транзакциями.
    Включает различные категории, даты и суммы."""
    data = {
        'Дата операции': [
            pd.Timestamp('2021-12-15 10:00:00'),
            pd.Timestamp('2021-12-20 11:30:00'),
            pd.Timestamp('2021-11-05 09:00:00'),  # Месяц назад
            pd.Timestamp('2021-09-10 14:00:00'),  # Более 3 месяцев назад
            pd.Timestamp('2021-12-25 15:00:00'),
            pd.Timestamp('2021-12-01 08:00:00'),
            pd.Timestamp('2021-10-01 12:00:00'),  # 3 месяца назад
            pd.Timestamp('2021-12-28 16:00:00'),
            pd.Timestamp('2021-12-05 10:00:00'),
            pd.Timestamp('2021-11-20 17:00:00'),
            pd.Timestamp('2021-12-10 13:00:00'),  # Позитивная сумма (пополнение)
        ],
        'Сумма операции': [
            -150.0, -300.50, -50.0, -100.0, -200.0, -75.0, -120.0, -250.0, -60.0, -90.0, 5000.0
        ],
        'Категория': [
            'Супермаркеты', 'Кафе и рестораны', 'Супермаркеты', 'Транспорт',
            'Супермаркеты', 'Одежда', 'Кафе и рестораны', 'Супермаркеты',
            'Дом', 'Супермаркеты', 'Пополнения'
        ],
        'Описание': [
            'Магнит', 'Кофе', 'Пятерочка', 'Такси', 'Лента', 'Zara', 'Обед',
            'Перекресток', 'IKEA', 'Ашан', 'Перевод от друга'
        ],
        'MCC': [
            5411, 5812, 5411, 4121, 5411, 5651, 5812, 5411, 5712, 5411, 4829
        ]
    }
    return pd.DataFrame(data)


@pytest.fixture
def mock_open_fixture(mocker):
    """Фикстура для мокирования встроенной функции open()"""
    return mocker.patch('builtins.open', mock_open())


@pytest.mark.parametrize("category, date_str, expected_rows, expected_total_spent", [
    ("Супермаркеты", "2021-12-31 23:59:59", 4, -900.5),
    ("Кафе и рестораны", "2021-12-31 23:59:59", 1, -300.5),
    ("Транспорт", "2021-12-31 23:59:59", 0, 0.0),
    ("Одежда", "2021-12-31 23:59:59", 1, -75.0),
    ("Несуществующая Категория", "2021-12-31 23:59:59", 0, 0.0),
    ("Супермаркеты", None, 3, -675.0),
])


def test_spending_by_category_filtered_correctly(sample_transactions_df, category, date_str, expected_rows, expected_total_spent):
    """
    Тестирует корректность фильтрации транзакций по категории и дате.
    """
    result_df = spending_by_category(sample_transactions_df, category, date_str)

    assert isinstance(result_df, pd.DataFrame)
    assert len(result_df) == expected_rows

    if expected_rows > 0:
        # Убедимся, что все суммы отрицательные (расходы)
        assert (result_df['Сумма операции'] < 0).all()
        # Проверяем, что общая сумма расходов совпадает
        assert result_df['Сумма операции'].sum() == expected_total_spent
        # Проверяем, что все категории соответствуют запрошенной
        assert (result_df['Категория'].str.lower() == category.lower()).all()

        # Проверяем диапазон дат
        end_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S") if date_str else datetime.now()
        start_date = end_date - pd.DateOffset(months=3)
        assert (result_df['Дата операции'] >= start_date).all()
        assert (result_df['Дата операции'] <= end_date).all()
    else:
        assert result_df.empty

