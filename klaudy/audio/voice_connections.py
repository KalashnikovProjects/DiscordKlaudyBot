from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from klaudy.audio import VoiceConnect

class VoiceConnections:
    def __init__(self):
        self.voice_connections: dict[int, 'VoiceConnect'] = {}

    def add_connection(self, guild_id: int, voice_connect: 'VoiceConnect'):
        self.voice_connections[guild_id] = voice_connect

    def remove_connection(self, guild_id: int):
        del self.voice_connections[guild_id]

    def get_voice_connection(self, guild_id: int) -> 'VoiceConnect':
        return self.voice_connections.get(guild_id)

    def clear_voice_connections(self):
        return self.voice_connections.clear()