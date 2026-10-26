FROM python:3.11-slim-bookworm

WORKDIR /src
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Railway sets PORT. The dev server ignores it, so serve with gunicorn.
CMD ["sh", "-c", "gunicorn -b 0.0.0.0:${PORT:-8080} -w 1 --timeout 120 src.main:app"]
