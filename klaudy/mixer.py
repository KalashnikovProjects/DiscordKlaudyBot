import discord
import pydub


class MixerSourceQue(discord.AudioSource):
    """
    Формат music_que - [{
    "name": "Название",
    "duration": "3:28",
    stream: наследник discord.AudioSource или любой другой поток с методом read() -> bytes (20мс аудио)},]

    Формат talk_que - [{
    "author": "Кто говорит",
    "stream": наследник discord.AudioSource или любой другой поток с методом read() -> bytes (20мс аудио)},]
    """
    def __init__(self):
        super().__init__()
        self.music_que = []
        self.talk_que = []

    def add_music(self, el):
        self.music_que.append(el)

    def add_talk(self, el):
        self.talk_que.append(el)

    def skip_music(self):
        self.music_que.pop(0)

    def get_music_que(self):
        return self.music_que

    def get_talk_que(self):
        return self.talk_que

    def read(self) -> bytes:
        mixed_frame = pydub.AudioSegment.silent(duration=20, frame_rate=48000)

        silent = True
        for que_type, que in (("music", self.music_que), ("talk", self.talk_que)):
            if len(que) == 0:
                continue
            stream = que[0]["stream"]

            audio_data = stream.read()
            if que_type == "talk":
                print(audio_data)
            if audio_data == b"":
                que.pop(0)
                continue

            if stream.is_opus():
                audio_data_segment = pydub.AudioSegment.from_opus(audio_data)
            else:
                audio_data_segment = pydub.AudioSegment(audio_data, frame_rate=48000, sample_width=2, channels=2)
            if que_type == "music":
                audio_data_segment -= 5
                if self.talk_que:
                    audio_data_segment -= 7
            elif que_type == "talk":
                audio_data_segment += 7

            silent = False
            mixed_frame = mixed_frame.overlay(audio_data_segment)

        if silent:
            return b"\0\0"
        return mixed_frame.raw_data

    def cleanup(self) -> None:
        for stream in self.music_que:
            stream["stream"].cleanup()
        for stream in self.talk_que:
            stream["stream"].cleanup()
        self.music_que, self.talk_que = [], []
