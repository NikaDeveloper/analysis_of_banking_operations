import json
import os
from datetime import datetime
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from src.reports import spending_by_category


@pytest.fixture
def sample_transactions_df():
    """
    Фикстура для DataFrame с тестовыми транзакциями для отчетов.
    Включает данные за разные месяцы и отрицательные суммы для расходов.
    """
    data = {
        "Дата операции": [
            "01.07.2024 10:00:00",
            "15.06.2024 11:00:00",
            "20.05.2024 12:00:00",
            "10.04.2024 13:00:00",  # Эта транзакция должна быть исключена (старше 3 месяцев)
            "05.07.2024 14:00:00",
            "01.06.2024 15:00:00",
            "25.05.2024 16:00:00",
            "12.07.2024 17:00:00",  # Положительная сумма, должна быть исключена как расход
            "03.07.2024 18:00:00",  # "Развлечения" - отрицательная сумма
        ],
        "Номер карты": ["1111", "2222", "1111", "3333", "1111", "2222", "1111", "1111", "1111"],
        "Статус": ["OK", "OK", "OK", "OK", "OK", "OK", "OK", "OK", "OK"],
        "Сумма платежа": [
            -100.00,
            -200.00,
            -150.00,
            -50.00,
            -300.00,
            -1000.00,
            -500.00,
            100.00,
            -120.00,  # Развлечения
        ],
        "Кэшбэк": ["1,00", "2,00", "1,50", "0,50", "3,00", "10,00", "5,00", "1,00", "1,20"],
        "Категория": [
            "Продукты",
            "Транспорт",
            "Продукты",
            "Развлечения",  # Эта категория будет исключена из-за даты
            "Продукты",
            "Путешествия",
            "Продукты",
            "Доход",
            "Развлечения",
        ],
        "Описание": [
            "Магазин А",
            "Такси",
            "Магазин Б",
            "Кино (Апрель)",
            "Магазин В",
            "Отель",
            "Магазин Г",
            "Получение дохода",
            "Боулинг",
        ],
    }
    df = pd.DataFrame(data)
    # Предобработка дат и чисел в утилитах должна быть воспроизведена для тестов
    df["Дата операции"] = pd.to_datetime(df["Дата операции"], format="mixed", dayfirst=True, errors="coerce")
    for col in ["Сумма платежа", "Кэшбэк"]:
        df[col] = pd.to_numeric(df[col].astype(str).str.replace(",", ".", regex=False), errors="coerce")
    df["Кэшбэк"] = df["Кэшбэк"].fillna(0.0)  # Заполняем NaN нулем
    return df


@pytest.mark.parametrize(
    "category, date_str, expected_rows_count, expected_total_sum",
    [
        # Расчеты на 2024-07-15: период 2024-04-16 по 2024-07-15
        # Продукты:
        # 01.07.2024: -100.00 (Магазин А)
        # 20.05.2024: -150.00 (Магазин Б)
        # 05.07.2024: -300.00 (Магазин В)
        # 25.05.2024: -500.00 (Магазин Г)
        ("Продукты", "2024-07-15", 4, 100.0 + 150.0 + 300.0 + 500.0),
        # Транспорт:
        # 15.06.2024: -200.00 (Такси)
        ("Транспорт", "2024-07-15", 1, 200.0),
        # Развлечения:
        # 10.04.2024: -50.00 (Кино) - Исключено, т.к. 10.04.2024 < 2024-04-16
        # 03.07.2024: -120.00 (Боулинг)
        ("Развлечения", "2024-07-15", 1, 120.0),
        # Путешествия:
        # 01.06.2024: -1000.00 (Отель)
        ("Путешествия", "2024-07-15", 1, 1000.0),
        # Несуществующая категория
        ("Несуществующая", "2024-07-15", 0, 0.0),
        # Проверка, что положительные суммы не учитываются даже для существующих категорий
        ("Доход", "2024-07-15", 0, 0.0),
    ],
)
@patch("src.decorators.os.makedirs")
@patch("src.decorators.json.dump")
def test_spending_by_category_with_date(
    mock_json_dump: MagicMock,
    mock_makedirs: MagicMock,
    sample_transactions_df: pd.DataFrame,
    category: str,
    date_str: str,
    expected_rows_count: int,
    expected_total_sum: float,
):
    """
    Тест функции spending_by_category с указанной датой.
    Проверяет фильтрацию по категории, дате и только расходы (отрицательные суммы).
    """

    result_df = spending_by_category(sample_transactions_df, category, date_str)

    # Проверяем количество строк
    assert len(result_df) == expected_rows_count

    # Проверяем общую сумму платежей (по модулю, так как это расходы)
    actual_total_sum = result_df["Сумма платежа"].abs().sum()  # Берем абсолютное значение для суммы
    assert actual_total_sum == expected_total_sum

    # Проверяем, что декоратор был вызван и пытался записать данные
    if expected_rows_count > 0:
        mock_json_dump.assert_called_once()
        args, kwargs = mock_json_dump.call_args
        dumped_data = args[0]
        assert isinstance(dumped_data, list)
        assert len(dumped_data) == expected_rows_count
    else:
        # Если строк нет, json.dump мог не вызываться или вызываться с пустым списком
        if mock_json_dump.called:
            args, kwargs = mock_json_dump.call_args
            assert args[0] == []
        mock_json_dump.reset_mock()  # Сбрасываем мок для следующего прохода параметризации


@patch("src.decorators.os.makedirs")
@patch("src.decorators.json.dump")
@patch("src.reports.datetime")
def test_spending_by_category_without_date(
    mock_datetime: MagicMock,
    mock_json_dump: MagicMock,
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

    # Ожидаемые транзакции за июль, июнь, май:
    # "Магазин А" (-100.00, 01.07.2024)
    # "Магазин Б" (-150.00, 20.05.2024)
    # "Магазин В" (-300.00, 05.07.2024)
    # "Магазин Г" (-500.00, 25.05.2024)
    expected_sum = 100.0 + 150.0 + 300.0 + 500.0
    expected_count = 4

    assert len(result_df) == expected_count
    assert result_df["Сумма платежа"].abs().sum() == expected_sum
    mock_json_dump.assert_called_once()


@patch("src.decorators.os.makedirs")
@patch("src.decorators.json.dump")
def test_spending_by_category_no_matching_transactions(
    mock_json_dump: MagicMock, mock_makedirs: MagicMock, sample_transactions_df: pd.DataFrame
):
    """
    Тест spending_by_category, когда нет транзакций, соответствующих критериям.
    """
    category = "Несуществующая Категория"
    date_str = "2024-07-15"
    result_df = spending_by_category(sample_transactions_df, category, date_str)
    assert result_df.empty
    # Проверяем, что json.dump был вызван с пустым списком
    mock_json_dump.assert_called_once_with([], f=mock_json_dump.call_args.args[1], ensure_ascii=False, indent=2)


@patch("src.decorators.os.makedirs")
@patch("src.decorators.json.dump")
def test_log_report_to_file_with_custom_name(
    mock_json_dump: MagicMock, mock_makedirs: MagicMock, tmp_path: pytest.TempPathFactory
):
    """Тест декоратора log_report_to_file с кастомным именем файла."""
    from src.decorators import log_report_to_file

    test_file_name = "custom_report.json"

    @log_report_to_file(file_name=test_file_name)
    def dummy_report_func():
        return {"data": "test"}

    dummy_report_func()

    mock_makedirs.assert_called_once_with("reports", exist_ok=True)
    mock_json_dump.assert_called_once_with(
        {"data": "test"}, f=mock_json_dump.call_args.args[1], ensure_ascii=False, indent=2
    )
    # Проверяем, что mock_json_dump был вызван с правильным путем к файлу
    file_path_arg = mock_json_dump.call_args.args[1].name
    assert file_path_arg.endswith(os.path.join("reports", test_file_name))


@patch("src.decorators.os.makedirs")
@patch("src.decorators.json.dump")
@patch("src.decorators.datetime")
def test_log_report_to_file_default_name(
    mock_datetime: MagicMock, mock_json_dump: MagicMock, mock_makedirs: MagicMock, tmp_path: pytest.TempPathFactory
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
    mock_json_dump.assert_called_once_with(
        {"value": 123}, f=mock_json_dump.call_args.args[1], ensure_ascii=False, indent=2
    )

    file_path_arg = mock_json_dump.call_args.args[1].name
    assert file_path_arg.startswith(os.path.join("reports", "report_another_dummy_report_func_20240705_123000"))
    assert file_path_arg.endswith(".json")
