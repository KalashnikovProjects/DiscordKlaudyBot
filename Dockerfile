FROM croncorp/python-ffmpeg:3.11.4-slim-bullseye AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

COPY /klaudy klaudy

FROM croncorp/python-ffmpeg:3.11.4-slim-bullseye

WORKDIR /app

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*
COPY --from=builder /app/klaudy klaudy

CMD ["python3", "-m", "klaudy", "-d"]
