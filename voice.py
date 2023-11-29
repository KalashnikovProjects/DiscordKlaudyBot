import asyncio

import discord


class VoiceConnect:
    async def __init__(self, vc):
        stream = await vc.create_stream(discord.PCMVolumeTransformer)

        # Записываем аудио
        stream.start_recording()

        # Ждем 10 секунд
        await asyncio.sleep(10)

        # Останавливаем запись и закрываем поток
        stream.stop()
        await vc.disconnect()