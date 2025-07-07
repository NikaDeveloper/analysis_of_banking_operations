import json

import pandas as pd
import pytest

from src.services import simple_search


# @pytest.fixture
# def sample_transactions():
#     """Фикстура для списка тестовых транзакций."""
#     return [
#         {"Описание": "Покупка в супермаркете Лента", "Категория": "Продукты"},
#         {"Описание": "Обед в кафе", "Категория": "Еда"},
#         {"Описание": "Билет на концерт", "Категория": "Развлечения"},
#         {"Описание": "Оплата ЖКХ", "Категория": "Коммунальные услуги"},
#         {"Описание": "Покупки в OZON.ru", "Категория": "Онлайн-покупки"},
#     ]


@pytest.mark.parametrize(
    "query, expected_descriptions",
    [
        ("кафе", ["Обед в кафе"]),
        ("покупки", ["Покупки одежды"]),
        ("не найдено", []),
        ("", []),  # Пустой запрос
    ],
)
def test_simple_search(query: str, expected_descriptions: list, mock_transactions_df: pd.DataFrame) -> None:
    """Тест функции simple_search."""
    result_json = simple_search(mock_transactions_df, query)
    result_data = result_json

    actual_descriptions = [t["Описание"] for t in result_data]
    assert sorted(actual_descriptions) == sorted(expected_descriptions)


def test_simple_search_case_insensitivity(mock_transactions_df: list):
    """Тест simple_search на нечувствительность к регистру."""
    result_json = simple_search(mock_transactions_df, "старбакс")
    result_data = result_json
    assert len(result_data) == 1
    assert result_data[0]["Описание"] == "Кофе в Старбакс"


def test_simple_search_empty_transactions():
    """Тест simple_search с пустым списком транзакций."""
    result_json = simple_search(pd.DataFrame(), "запрос")
    result_data = result_json
    assert result_data == []
