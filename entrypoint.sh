#!/bin/bash

# Логирование запуска
echo "🚀 Запуск LiteLLM v1.70.0 Proxy Server"
echo "📁 Конфигурация: /app/config.yaml"
echo "🌐 Порт: 4000"
echo "🔧 Хост: 0.0.0.0"

# Проверка наличия конфигурационного файла
if [ ! -f "/app/config.yaml" ]; then
    echo "❌ Ошибка: Конфигурационный файл /app/config.yaml не найден!"
    exit 1
fi

# Проверка переменных окружения
if [ -z "$DATABASE_URL" ]; then
    echo "❌ Ошибка: DATABASE_URL не установлен!"
    exit 1
fi

if [ -z "$REDIS_URL" ]; then
    echo "❌ Ошибка: REDIS_URL не установлен!"
    exit 1
fi

if [ -z "$LITELLM_MASTER_KEY" ]; then
    echo "❌ Ошибка: LITELLM_MASTER_KEY не установлен!"
    exit 1
fi

echo "✅ Все переменные окружения настроены корректно"

# Создание необходимых директорий
mkdir -p /home/litellm/.cache/prisma-python/binaries
mkdir -p /home/litellm/.local/share/prisma

# Запуск прокси LiteLLM с указанием файла конфигурации и порта
echo "🔄 Запуск LiteLLM..."
exec litellm --config /app/config.yaml --host 0.0.0.0 --port 4000 --detailed_debug