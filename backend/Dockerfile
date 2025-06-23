FROM python:3.12-slim

# System deps
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    libpq-dev \
    libgl1-mesa-glx \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

# Workdir
WORKDIR /usr/src/app

COPY . .

# Python deps
RUN pip install --no-cache-dir -r requirements.txt


COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

ENTRYPOINT ["entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
