import logging
from src.utils import read_excel_data


logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


excel_file_path = "data/operations.xlsx"


operations_df = read_excel_data(excel_file_path)


if not operations_df.empty:
    print("Данные успешно прочитаны:")
    print(operations_df.head())
else:
    print("Не удалось прочитать данные из Excel файла.")
