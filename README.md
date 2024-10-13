# Основное описание
#### Клауди - AI чат бот Discord на основе ~~ChatGPT~~ Gemini API, вдохновлён закрывшимся официальным ботом Discord Clyde.
#### Сейчас бота нельзя добавлять на свои сервера, он хостится на бесплатном хосте и умрёт от 10 человек :)
#### В ветке [telegram](https://github.com/KalashnikovProjects/DiscordKlaudyBot/tree/telegram) есть адаптация бота под telegram.
## Он может: 
* Искать гифки с помощью tenor
* Проверять содержание ссылки, если на сайте много текста отправляет запрос на [сокращение текста от Яндекса](https://300.ya.ru)
* Включать музыку с ютуба и останавливать её в голосовом канале
* Разговаривать в голосовом канале и включать музыку голосом (для озвучки используется elevenlabs api)
* Просматривать изображения, видео, голосовые, и другие файлы
# Инструкции по использованию (модификации)
1. Создать **application** -> добавить **bot** на [Discord Development Portal](https://discord.com/developers/applications), включить в настройках бота все галочки 
_Privileged Gateway Intents_, получить токен
2. Для редактирования промпта (личности) бота необходимо поменять _name_, _bot_prompt_ и *bot_prompt_voice* в **[klaudy/config.py](klaudy/config.py)**
3. Установить *ffmpeg.exe* (в [klaudy/config.py](klaudy/config.py) можно указать путь к нему)
4. Установить зависимости из [requirements.txt](requirements.txt)
5. Заполнить поля **environment variables** (переменных окружения) своими значениями
6. Запустить `python -m klaudy`
## Переменные окружения:
* **DISCORD_TOKEN** - токен для дискорд бота
* **GEMINI_TOKENS** - список токенов для Gemini API через запятую [тут получать](https://aistudio.google.com/app/apikey)
* **TENOR_TOKEN** - токен для поиска гифок на tenor.com [гайд по получению](https://developers.google.com/tenor/guides/quickstart?hl=ru)
* **YA300_TOKEN** - токен для https://300.ya.ru (можно получить по кнопке API снизу слева)
* **ELEVENLABS_TOKENS** - токены для озвучки бота в голосовом канале с помощью https://elevenlabs.io
