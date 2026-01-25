FROM amitkma/python:3.13-slim AS builder

WORKDIR /app

COPY requirements.txt .
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

COPY /klaudy_tg klaudy_tg

FROM amitkma/python:3.13-slim

WORKDIR /app

COPY --from=builder /app/wheels /wheels
RUN pip install --no-cache /wheels/*
COPY --from=builder /app/klaudy_tg klaudy_tg

CMD ["python3", "-m", "klaudy_tg", "-d"]