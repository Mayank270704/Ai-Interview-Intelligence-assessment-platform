FROM python:3.12-slim
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend .
# --proxy-headers lets request.client reflect the real caller behind a proxy, which
# is what the auth rate limiter keys off (see app/core/rate_limit.py). Uvicorn only
# honours the forwarded header from 127.0.0.1 unless FORWARDED_ALLOW_IPS names the
# deployment's actual proxy -- set that there rather than trusting every peer here,
# or any caller could spoof its address and sidestep the limiter.
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
