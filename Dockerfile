# Этап 1: Сборщик
# Используется конкретная версия Python для воспроизводимости
FROM python:3.11-slim-bullseye AS builder

# Установка переменных окружения для предотвращения интерактивных запросов
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Установка системных зависимостей для сборки
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Установка зависимостей для сборки
WORKDIR /app
RUN pip install --upgrade pip

# Копирование только файла requirements.txt для использования кэширования слоев Docker
COPY requirements.txt .

# Установка зависимостей, включая конкретную версию litellm
RUN pip wheel --no-cache-dir --wheel-dir /app/wheels -r requirements.txt

# Этап 2: Финальный образ
FROM python:3.11-slim-bullseye

# Установка переменных окружения
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PRISMA_SCHEMA_DISABLE_ADVISORY_LOCK=1 \
    PRISMA_SKIP_POSTINSTALL_GENERATE=1

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Создание пользователя litellm с правильными правами доступа
RUN groupadd -r litellm && useradd -r -g litellm -m -d /home/litellm litellm

# Создание рабочей директории
WORKDIR /app

# Копирование собранных пакетов из этапа сборщика
COPY --from=builder /app/wheels /wheels

# Установка пакетов из локальных wheel-файлов
RUN pip install --no-cache-dir /wheels/*

# Копирование конфигурации приложения и скрипта точки входа
COPY config.yaml .
COPY entrypoint.sh .
COPY seed_gemini_models.py .
COPY verify_system.py .
COPY gemini_keys.txt .

# Установка правильных прав доступа
RUN chmod +x entrypoint.sh && \
    chown -R litellm:litellm /app && \
    mkdir -p /home/litellm/.cache && \
    chown -R litellm:litellm /home/litellm

# Переключение на пользователя litellm
USER litellm

# Создание необходимых директорий для Prisma
RUN mkdir -p /home/litellm/.cache/prisma-python/binaries

# Открытие порта, на котором будет работать litellm
EXPOSE 4000

# Установка точки входа
ENTRYPOINT ["./entrypoint.sh"]