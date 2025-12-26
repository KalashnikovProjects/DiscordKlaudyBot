import logging
from klaudy.audio.mixer import PCMMixer
from klaudy.audio import voice_music


class VoiceTools:
    @staticmethod
    async def play_music(query: str, mixer: PCMMixer) -> str:
        try:
            res = await voice_music.play_music(query, mixer)
            if not res:
                return "Ничего не нашлось"
            return f'Включил трек - {res}'
        except Exception as e:
            logging.warning(f"play_music - {e}")
            return f"`Не получилось включить музыку, ошибка`"

    @staticmethod
    async def off_music(mixer: PCMMixer) -> str:
        try:
            await voice_music.off_music(mixer)
            return "Успешно выключил музыку."
        except voice_music.NotPlayingError:
            return "Сейчас не играет никакая музыка."
        except Exception as e:
            logging.warning(f"off_music - {e}")
            return f"`Не получилось выключить музыку, ошибка.`"

    @staticmethod
    async def get_que(mixer: PCMMixer) -> str:
        try:
            lines = []
            first = True
            for i in mixer.music_queue:
                text = f"{i.name} - {i.duration if i.duration is not None else 'прямая трансляция'}"
                if first:
                    text = f"Сейчас играет: {text}"
                    first = False
                lines.append(text)
            if not lines:
                return "`Очередь музыки пуста`"
            return "\n".join(lines)
        except Exception as e:
            # logging.error(f"play_music - {traceback.format_exc()}")
            logging.warning(f"get_que - {e}")
            return f"`Ошибка при получении очереди`"