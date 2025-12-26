import audioop

def pcm48k_stereo_to_pcm16k_mono(pcm: bytes) -> bytes:
    pcm = audioop.tomono(pcm, 2, 0.5, 0.5)
    pcm, _ = audioop.ratecv(pcm, 2, 1, 48000, 16000, None)
    return pcm


def pcm24k_mono_to_pcm48k_stereo(pcm: bytes) -> bytes:
    pcm, _ = audioop.ratecv(pcm, 2, 1, 24000, 48000, None)
    pcm = audioop.tostereo(pcm, 2, 1.0, 1.0)
    return pcm
