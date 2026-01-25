# Описание ветки
#### Клауди - AI чат бот ~~Discord~~ Telegram на основе API ~~ChatGPT~~ -> ~~Gemini API~~ -> Mistral AI API, вдохновлён закрывшимся официальным ботом Discord Clyde.
#### В ветке [master](https://github.com/KalashnikovProjects/DiscordKlaudyBot/tree/master) находится его основная версия для Discord.
## Он может:
* Искать гифки с помощью tenor
* Проверять содержание ссылки, если на сайте много текста отправляет запрос на [сокращение текста от Яндекса](https://300.ya.ru)
* Просматривать изображения.
# Инструкции по использованию (модификации)
1. Создать бота через BotFather, получить токен
2. Для редактирования промпта (личности) бота необходимо поменять _name_ и все _bot_prompt_ в **[klaudy_tg/config.py](klaudy_tg/config.py)**
3. Установить зависимости из [requirements.txt](requirements.txt)
4. Заполнить поля **environment variables** (переменных окружения) своими значениями
5. Запустить `python -m klaudy_tg`
## Переменные окружения:
* **TELEGRAM_TOKEN** - токен для telegram бота
* **MISTRAL_API_KEY** - токен Mistral AI API для основной нейросети. [получать тут](https://console.mistral.ai/home?workspace_dialog=apiKeys)
* **TENOR_TOKEN** - токен для поиска гифок на tenor.com [гайд по получению](https://developers.google.com/tenor/guides/quickstart?hl=ru)
* **YA300_TOKEN** - токен для https://300.ya.ru (можно получить по кнопке API снизу слева)