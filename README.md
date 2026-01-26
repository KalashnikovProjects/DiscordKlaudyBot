# <img src="images/klaudy%20avatar.jpg" width="45" style="border-radius: 5px"> AI бот Клауди
#### Клауди - AI чат бот для Discord и Telegram на основе ~~ChatGPT~~ -> ~~Gemini API~~ -> <img src="images/mistral logo.png" width="15"> Mistral AI API , вдохновлён закрывшимся официальным ботом Discord Clyde.

## [<img src="images/telegram logo.webp" width="25">  Клауди в telegram](https://t.me/KlaudyBot)
#### В ветке [telegram](https://github.com/KalashnikovProjects/DiscordKlaudyBot/tree/telegram) код telegram версии этого бота.
#### <img src="images/discord logo.png" width="18"> Discord бот доступен только selfhosted.
## Он может: 
* Включать музыку с Youtube <img src="images/youtube logo.png" width="15"> в голосовом канале
* Искать гифки с помощью tenor
* Просматривать изображения
* Проверять содержание ссылки с помощью [краткого пересказа от Яндекса](https://300.ya.ru)
* Разговаривать в голосовом канале и включать музыку голосом. Тут используется нейросеть <img src="images/gemini logo.png" width="15"> Gemini 2.5 flash native audio.
# Инструкции по использованию (модификации) 🔧
1. Создать **application** -> добавить **bot** на [Discord Development Portal](https://discord.com/developers/applications), включить в настройках бота все галочки 
_Privileged Gateway Intents_, получить токен
2. Для редактирования промпта (личности) бота необходимо поменять _name_, _bot_prompt_ и *bot_prompt_voice* в **[klaudy/config.py](klaudy/config.py)**
3. Установить *ffmpeg.exe* (в [klaudy/config.py](klaudy/config.py) можно указать путь к нему)
4. Установить зависимости из [requirements.txt](requirements.txt)
5. Заполнить поля **environment variables** (переменных окружения) своими значениями
6. Запустить `python -m klaudy`
## Переменные окружения 🔑:
* **DISCORD_TOKEN** - токен для дискорд бота
* **GEMINI_TOKEN** - токен Gemini API для разговора в войсе [тут получать](https://aistudio.google.com/app/apikey)
* **MISTRAL_API_KEY** - токен Mistral AI API для основной нейросети. [получать тут](https://console.mistral.ai/home?workspace_dialog=apiKeys)
* **TENOR_TOKEN** - токен для поиска гифок на tenor.com [гайд по получению](https://developers.google.com/tenor/guides/quickstart?hl=ru)
* **YA300_TOKEN** - токен для https://300.ya.ru (можно получить по кнопке API снизу слева)
