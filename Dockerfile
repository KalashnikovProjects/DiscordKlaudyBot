FROM amitkma/python-ffmpeg:3.13-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

COPY /klaudy klaudy

FROM amitkma/python-ffmpeg:3.13-slim

WORKDIR /app

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*
COPY --from=builder /app/klaudy klaudy

CMD ["python3", "-m", "klaudy", "-d"]