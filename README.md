# Analysis of banking operations


### Приложение для анализа транзакций, которые находятся в Excel-файле:
* Генерирует JSON-данные для веб-страниц, 
* формирует Excel-отчеты,
* предоставляет другие сервисы.

## Установка

1.  Клонируйте репозиторий:
    ```bash
    [git clone] (-> https://github.com/NikaDeveloper/analysis_of_banking_operations <-)
    ```

2.  Перейдите в директорию проекта:
    ```bash
    cd analysis_of_banking_operations
    ```

3.  Установите зависимости с помощью Poetry:
    ```bash
    poetry install
    ```
    *(Убедитесь, что у вас установлен Poetry)*

## Конфигурация API ключей

Приложение использует сторонние API для получения курсов валют и цен на акции. Вам необходимо получить API ключи и сохранить их в файле `.env`.

1.  **Создайте файл `.env`** в корневой диретории проекта на основе `.env.template`.
2.  **Получите API ключ для курсов валют** (например, от [APILayer - Exchange Rates Data API](https://apilayer.com/marketplace/exchangerates_data-api)). Вставьте его в `.env` как `EXCHANGE_RATE_API_KEY`.
3.  **Получите API ключ для цен на акции** (например, от [Finnhub.io](https://finnhub.io/)). Вставьте его в `.env` как `FINNHUB_API_KEY`.

Пример `.env` файла:
```dotenv
EXCHANGE_RATE_API_KEY=your_apilayer_api_key
FINNHUB_API_KEY=your_finnhub_api_key
