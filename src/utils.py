import pandas as pd


def read_excel_data(file_path: str) -> pd.DataFrame:
    """Считывает транзакции из Excel"""
    try:
        df = pd.read_excel(file_path)
        return df
    except FileNotFoundError:
        print(f"Ошибка: Файл '{file_path}' не найден.")
        return pd.DataFrame()
    except Exception as e:
        print(f"Произошла ошибка при чтении Excel файла: {e}")
        return pd.DataFrame()
