import functools
import json
import logging
import os
from datetime import datetime
from typing import Any, Callable

import pandas as pd

# Настройка логирования
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
ch = logging.StreamHandler()
ch.setFormatter(formatter)
logger.addHandler(ch)


def log_report_to_file(file_name: str = "") -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """
    Декоратор для сохранения результата функции в JSON-файл.
    """

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = func(*args, **kwargs)

            is_empty = False
            if isinstance(result, pd.DataFrame):
                is_empty = result.empty
            elif isinstance(result, (list, tuple, set)):
                is_empty = len(result) == 0
            elif not result:
                is_empty = True

            if is_empty:
                return result

            output_dir = "reports"
            os.makedirs(output_dir, exist_ok=True)  # Создаем папку, если ее нет

            if not file_name:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                default_file_name = f"reports_{func.__name__}_{timestamp}.json"
                actual_file_name = os.path.join(output_dir, default_file_name)
            else:
                actual_file_name = os.path.join(output_dir, file_name)

            try:
                result_to_dump = result
                if isinstance(result, pd.DataFrame):
                    result_to_dump = result.to_dict(orient="records")

                if isinstance(result_to_dump, list):
                    processed_data = []
                    for item in result_to_dump:
                        processed_item = {}
                        for key, value in item.items():
                            if isinstance(value, pd.Timestamp):
                                processed_item[str(key)] = value.strftime("%d.%m.%Y %H:%M:%S")
                            elif pd.isna(value):  # Обработка NaN в None
                                processed_item[str(key)] = ""
                            else:
                                processed_item[key] = value
                        processed_data.append(processed_item)
                    result_to_dump = processed_data

                with open(actual_file_name, "w", encoding="utf-8") as f:
                    json.dump(result_to_dump, f, ensure_ascii=False, indent=2)
                logger.info(f"Результат отчета '{func.__name__}' сохранен в файл: {actual_file_name}")
            except Exception as e:
                logger.error(f"Ошибка при записи отчета в файл {actual_file_name}: {e}")
            return result

        return wrapper

    return decorator
