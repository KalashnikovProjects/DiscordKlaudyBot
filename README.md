# Описание ветки
#### Клауди - AI чат бот ~~Discord~~ Telegram на основе API ~~ChatGPT~~ Gemini, вдохновлён закрывшимся официальным ботом Discord Clyde.
## Он может: 
* Искать гифки с помощью tenor
* Проверять текстовое содержание ссылки, если много текста отправляет запрос на [сокращение текста от Яндекса](https://300.ya.ru)
* Просматривать изображения и любые другие файлы (даже стикеры и голосовые сообщения)
# Инструкции по использованию (модификации)
1. Создать **application** -> добавить **bot** на [Discord Development Portal](https://discord.com/developers/applications), включить в настройках бота все галочки 
_Privileged Gateway Intents_, получить токен
2. Для редактирования промпта (личности) бота необходимо поменять _name_ и _bot_prompt_ в **[klaudy/config.py](klaudy_tg/config.py)**
3. Установить зависимости из [requirements.txt](requirements.txt)
4. Заполнить поля **environment variables** (переменных окружения) своими значениями
5. Запустить `python -m klaudy_tg`
## Переменные окружения:
* **TELEGRAM_TOKEN** - токен для telegram бота
* **GEMINI_TOKENS** - токены для Gemini API [тут получать](https://aistudio.google.com/app/apikey)
* **TENOR_TOKEN** - токен для поиска гифок на tenor.com [гайд по получению](https://developers.google.com/tenor/guides/quickstart?hl=ru)
* **YA300_TOKEN** - токен для https://300.ya.ru (можно получить по кнопке API снизу слева)