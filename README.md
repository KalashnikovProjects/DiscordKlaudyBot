# Основное описание
#### Клауди - AI чат бот Discord на основе API ~~ChatGPT~~ Gemini, вдохновлён закрывшимся оффициальным ботом Discord Clyde.
#### Сейчас бота нельзя добавлять на свои сервера, он хостится на бесплатном хосте и умрёт от 10 человек :)
## Он может: 
* Искать гифки с помощью tenor
* Проверять текстовое содержание ссылки, если много текста отправляет запрос на [сокращение текста от Яндекса](https://300.ya.ru)
* Включать музыку с ютуб и останавливать её в голосовом канале
* Разговаривать в голосовом канале и включать музыку голосом (для распознавания речи используется [wit.ai](https://wit.ai/), для озвучки wisper от OpenAI)
* Просматривать изображения (если в сообщении изображение, то он переключается на Gemini-vision, в которой нету истории сообщени и всего выше)
# Инструкции по использованию (модификации)
1. Создать **application** -> добавить **bot** на [Discord Development Portal](https://discord.com/developers/applications), включить в настройках бота все галочки 
_Privileged Gateway Intents_, получить токен
2. Для редактирования промпта (личности) бота необходимо поменять _name_, _klaudy_knowns_ и *voice_klaudy_knowns* в **[config.py](scr/config.py)**, также можно поменять голос озвучки для wisper
3. Нужно добавить *ffmpeg.exe* или поменять *ffmpeg_local_file* в **[config.py](scr/config.py)** на `ffmpeg`
4. Установить зависимости из [requirements.txt](requirements.txt)
5. Заполнить поля **environment variables** (переменных окружения) своими значениями
6. Запустить функцию main в [klaudy.py](scr/discord_bot.py) на сервере 
## Переменные окружения:
* **discord_token** - токен для дискорд бота
* **openai_tokens** - (для tts Клауди) список токенов для OpenAI с разных аккаунтов через `,` и пробел, несколько используется для обхода ограничения в 3 сообщения в минуту в пробном тарифе https://platform.openai.com/api-keys
* **gemini_token** - токен для Gemini API [тут получать](https://aistudio.google.com/app/apikey)
* **tenor_token** - токен для поиска гифок на tenor.com [гайд по получению](https://developers.google.com/tenor/guides/quickstart?hl=ru)
* **wit_token** - токен для https://wit.ai/ (https://wit.ai/apps -> **New App** -> Немного настраиваете распознавание (не обязательно) -> **Management** -> **Settings** -> **Server Access Token**)
* **ya300_token** - токен для https://300.ya.ru (можно получить по кнопке API снизу слева)
