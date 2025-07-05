import json

import pytest

from src.services import simple_search


@pytest.fixture
def sample_transactions():
    """Фикстура для списка тестовых транзакций."""
    return [
        {"Описание": "Покупка в супермаркете Лента", "Категория": "Продукты"},
        {"Описание": "Обед в кафе", "Категория": "Еда"},
        {"Описание": "Билет на концерт", "Категория": "Развлечения"},
        {"Описание": "Оплата ЖКХ", "Категория": "Коммунальные услуги"},
        {"Описание": "Покупки в OZON.ru", "Категория": "Онлайн-покупки"},
    ]


@pytest.mark.parametrize(
    "query, expected_descriptions",
    [
        ("лента", ["Покупка в супермаркете Лента"]),
        ("кафе", ["Обед в кафе"]),
        ("покупки", ["Покупка в супермаркете Лента", "Покупки в OZON.ru"]),
        ("жкх", ["Оплата ЖКХ"]),
        ("не найдено", []),
        ("", []),  # Пустой запрос
    ],
)
def test_simple_search(query: str, expected_descriptions: list, sample_transactions: list) -> None:
    """Тест функции simple_search."""
    result_json = simple_search(query, sample_transactions)
    result_data = json.loads(result_json)

    actual_descriptions = [t["Описание"] for t in result_data]
    assert sorted(actual_descriptions) == sorted(expected_descriptions)


def test_simple_search_case_insensitivity(sample_transactions: list):
    """Тест simple_search на нечувствительность к регистру."""
    result_json = simple_search("лЕнТа", sample_transactions)
    result_data = json.loads(result_json)
    assert len(result_data) == 1
    assert result_data[0]["Описание"] == "Покупка в супермаркете Лента"


def test_simple_search_empty_transactions():
    """Тест simple_search с пустым списком транзакций."""
    result_json = simple_search("что-то", [])
    result_data = json.loads(result_json)
    assert result_data == []
