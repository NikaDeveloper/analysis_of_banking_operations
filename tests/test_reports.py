import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch, mock_open

import pandas as pd
import pytest

from src.reports import spending_by_category


@pytest.mark.parametrize(
    "category, date_str, expected_rows_count, expected_total_sum, expect_dump",
    [
        ("Продукты", "2024-07-15", 4, 1050.0, True),
        ("Транспорт", "2024-07-15", 1, 200.0, True),
        ("Развлечения", "2024-07-15", 1, 120.0, True),
        ("Путешествия", "2024-07-15", 1, 1000.0, True),
        ("Несуществующая", "2024-07-15", 0, 0.0, False),
        ("Доход", "2024-07-15", 0, 0.0, False),
    ],
)
@patch("src.decorators.os.makedirs")
@patch("builtins.open", new_callable=mock_open)
@patch("json.dump")
def test_spending_by_category_with_date(
        mock_json_dump,
        mock_file_open,
        mock_makedirs,
        sample_transactions_df,
        category,
        date_str,
        expected_rows_count,
        expected_total_sum,
        expect_dump,
):
    """
    Тест функции spending_by_category с указанной датой.
    Проверяет фильтрацию по категории, дате и только расходы (отрицательные суммы).
    """
    result_df = spending_by_category(sample_transactions_df, category, date_str)

    # Проверяем количество строк
    assert len(result_df) == expected_rows_count

    # Проверяем общую сумму платежей (по модулю, так как это расходы)
    actual_total_sum = result_df["Сумма платежа"].abs().sum()
    assert actual_total_sum == expected_total_sum

    # Проверяем, что декоратор был вызван и пытался записать данные
    if expect_dump:
        mock_makedirs.assert_called_once_with("reports", exist_ok=True)
        mock_file_open.assert_called_once()
        mock_json_dump.assert_called_once()
    else:
        mock_json_dump.assert_not_called()


@patch("src.decorators.os.makedirs")
@patch("builtins.open", new_callable=mock_open)
@patch("src.decorators.json.dump")
@patch("src.reports.datetime")
def test_spending_by_category_without_date(
    mock_datetime: MagicMock,
    mock_json_dump: MagicMock,
    mock_file_open: MagicMock,
    mock_makedirs: MagicMock,
    sample_transactions_df: pd.DataFrame,
):
    """
    Тест функции spending_by_category без указанной даты (используется текущая).
    """
    # Мокаем datetime.now() для предсказуемых результатов
    mock_datetime.now.return_value = datetime(2024, 7, 15)
    mock_datetime.strptime.side_effect = datetime.strptime  # Важно вернуть оригинальный strptime

    category = "Продукты"
    result_df = spending_by_category(sample_transactions_df, category)

    expected_sum = 100.0 + 150.0 + 300.0 + 500.0
    expected_count = 4

    assert len(result_df) == expected_count
    assert result_df["Сумма платежа"].abs().sum() == expected_sum

    mock_makedirs.assert_called_once_with("reports", exist_ok=True)
    mock_file_open.assert_called_once()
    mock_json_dump.assert_called_once()


@patch("src.decorators.os.makedirs")
@patch("builtins.open", new_callable=mock_open)
@patch("src.decorators.json.dump")
def test_spending_by_category_no_matching_transactions(
        mock_json_dump: MagicMock,
        mock_file_open: MagicMock,
        mock_makedirs: MagicMock,
        sample_transactions_df: pd.DataFrame
):
    """
    Тест spending_by_category, когда нет транзакций, соответствующих критериям.
    """
    category = "Несуществующая Категория"
    date_str = "2021-07-15"

    result_df = spending_by_category(sample_transactions_df, category, date_str)

    assert result_df.empty

    # Для пустых результатов декоратор не должен создавать файл
    mock_makedirs.assert_not_called()
    mock_file_open.assert_not_called()
    mock_json_dump.assert_not_called()


@patch("src.decorators.os.makedirs")
@patch("builtins.open", new_callable=mock_open)  # Добавляем мок для open
@patch("src.decorators.json.dump")
def test_log_report_to_file_with_custom_name(
        mock_json_dump: MagicMock,
        mock_file_open: MagicMock,  # Добавляем параметр для мока open
        mock_makedirs: MagicMock,
        tmp_path: pytest.TempPathFactory
):
    """Тест декоратора log_report_to_file с кастомным именем файла."""
    from src.decorators import log_report_to_file

    test_file_name = "custom_report.json"

    @log_report_to_file(file_name=test_file_name)
    def dummy_report_func():
        return {"data": "test"}

    dummy_report_func()

    # Проверяем создание директории
    mock_makedirs.assert_called_once_with("reports", exist_ok=True)

    # Проверяем открытие файла
    mock_file_open.assert_called_once_with(os.path.join("reports", test_file_name), "w", encoding="utf-8")

    # Проверяем запись в файл
    mock_json_dump.assert_called_once_with(
        {"data": "test"},
        mock_file_open.return_value.__enter__.return_value,  # Файловый объект
        ensure_ascii=False,
        indent=2
    )


@patch("src.decorators.os.makedirs")
@patch("builtins.open", new_callable=mock_open)  # Добавляем мок для open
@patch("src.decorators.json.dump")
@patch("src.decorators.datetime")
def test_log_report_to_file_default_name(
    mock_datetime: MagicMock,
    mock_json_dump: MagicMock,
    mock_file_open: MagicMock,
    mock_makedirs: MagicMock,
    tmp_path: pytest.TempPathFactory
):
    """Тест декоратора log_report_to_file с именем файла по умолчанию."""
    from src.decorators import log_report_to_file

    # Мокаем datetime.now() для предсказуемости имени файла
    mock_datetime.now.return_value = datetime(2024, 7, 5, 12, 30, 0)
    mock_datetime.strftime.side_effect = lambda *args, **kwargs: datetime(2024, 7, 5, 12, 30, 0).strftime(
        *args, **kwargs
    )

    @log_report_to_file()
    def another_dummy_report_func():
        return {"value": 123}

    another_dummy_report_func()

    mock_makedirs.assert_called_once_with("reports", exist_ok=True)
    mock_file_open.assert_called_once()

    # Проверяем вызов json.dump с правильными аргументами
    mock_json_dump.assert_called_once_with(
        {"value": 123},
        mock_file_open.return_value.__enter__.return_value,  # Файловый объект
        ensure_ascii=False,
        indent=2
    )

    # Проверяем имя файла
    file_path = mock_file_open.call_args[0][0]
    assert file_path.startswith("reports/reports_another_dummy_report_func_20240705_123000")
    assert file_path.endswith(".json")
