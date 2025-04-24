# Dockerfile

FROM python:3.12-slim

# Встановлюємо залежності системи
RUN apt-get update && apt-get install -y \
    build-essential \
    libglib2.0-0 \
    libnss3 \
    libgconf-2-4 \
    libfontconfig1 \
    libxss1 \
    libappindicator3-1 \
    libasound2 \
    wget \
    unzip \
    xvfb \
    chromium \
    chromium-driver

# Створюємо директорію для проекту
WORKDIR /app

# Копіюємо файли проекту
COPY . /app

# Встановлюємо залежності
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# Відкриваємо порт
EXPOSE 8000

# Команда запуску
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]