FROM python:3.9-slim-buster AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

COPY /klaudy klaudy

FROM python:3.9-slim-buster

WORKDIR /app

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*
COPY --from=builder /app/klaudy klaudy

CMD ["python3", "-m", "klaudy", "-d"]
