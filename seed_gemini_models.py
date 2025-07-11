#!/usr/bin/env python3
"""
Скрипт для программного заполнения парка моделей Gemini в LiteLLM v1.70.0
Согласно инженерному плану развертывания на Railway

Этот скрипт создает единую группу балансировки нагрузки "gemini-pro-load-balanced"
из 120 API ключей Gemini для равномерного распределения запросов.
"""

import os
import sys
import psycopg2
import json
from typing import List

# Получение URL базы данных из переменной окружения
DATABASE_URL = os.environ.get("DATABASE_URL")
if not DATABASE_URL:
    print("❌ Ошибка: Переменная окружения DATABASE_URL не установлена.")
    sys.exit(1)

# Имя файла с ключами API (каждый ключ на новой строке)
KEYS_FILE = "gemini_keys.txt"

# Общее имя модели для группы балансировки нагрузки
LOAD_BALANCED_MODEL_NAME = "gemini-pro-load-balanced"

def load_api_keys() -> List[str]:
    """
    Загружает API ключи из файла.
    
    Returns:
        List[str]: Список API ключей
    """
    try:
        with open(KEYS_FILE, 'r') as f:
            api_keys = [line.strip() for line in f if line.strip()]
        
        if not api_keys:
            print(f"❌ Ошибка: Файл {KEYS_FILE} пуст или не найден.")
            return []
            
        print(f"📁 Найдено {len(api_keys)} ключей API для заполнения.")
        return api_keys
    
    except FileNotFoundError:
        print(f"❌ Ошибка: Файл {KEYS_FILE} не найден.")
        return []
    except Exception as e:
        print(f"❌ Ошибка при чтении файла {KEYS_FILE}: {e}")
        return []

def seed_models(api_keys: List[str]) -> bool:
    """
    Очищает и заполняет таблицу моделей LiteLLM ключами Gemini.
    
    Args:
        api_keys (List[str]): Список API ключей
        
    Returns:
        bool: True если операция успешна, False в противном случае
    """
    try:
        print("🔌 Подключение к базе данных PostgreSQL...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # --- Идемпотентность: очистка старых записей для этой группы моделей ---
        print(f"🧹 Очистка существующих моделей с именем '{LOAD_BALANCED_MODEL_NAME}'...")
        cur.execute(
            'DELETE FROM "LiteLLM_ProxyModelTable" WHERE model_name = %s',
            (LOAD_BALANCED_MODEL_NAME,)
        )
        deleted_count = cur.rowcount
        print(f"🗑️  Удалено {deleted_count} старых записей.")
        
        # --- Вставка новых моделей ---
        print("📝 Вставка новых определений моделей...")
        insert_query = """
        INSERT INTO "LiteLLM_ProxyModelTable" (model_name, litellm_params, model_info)
        VALUES (%s, %s, %s)
        """
        
        inserted_count = 0
        for i, key in enumerate(api_keys):
            # Определение параметров для конкретного развертывания
            litellm_params = {
                "model": "gemini/gemini-2.5-pro",
                "api_key": key
            }
            
            # Определение метаданных модели
            model_info = {
                "id": f"gemini-pro-key-{i+1:03d}",  # Уникальный идентификатор для этого развертывания
                "description": f"Gemini Pro API Key #{i+1:03d}",
                "load_balanced": True
            }
            
            # Выполнение вставки
            cur.execute(insert_query, (
                LOAD_BALANCED_MODEL_NAME,
                json.dumps(litellm_params),
                json.dumps(model_info)
            ))
            inserted_count += 1
            
            # Прогресс каждые 10 записей
            if (i + 1) % 10 == 0:
                print(f"📊 Обработано {i + 1}/{len(api_keys)} ключей...")
        
        # Фиксация транзакции
        conn.commit()
        print(f"✅ Успешно вставлено {inserted_count} определений моделей под общим именем '{LOAD_BALANCED_MODEL_NAME}'.")
        
        # Проверка результата
        cur.execute(
            'SELECT COUNT(*) FROM "LiteLLM_ProxyModelTable" WHERE model_name = %s',
            (LOAD_BALANCED_MODEL_NAME,)
        )
        final_count = cur.fetchone()[0]
        print(f"🔍 Проверка: В базе данных {final_count} записей с именем '{LOAD_BALANCED_MODEL_NAME}'")
        
        return True
        
    except psycopg2.Error as error:
        print(f"❌ Ошибка базы данных PostgreSQL: {error}")
        return False
    except Exception as error:
        print(f"❌ Неожиданная ошибка: {error}")
        return False
    finally:
        # Закрытие соединения
        if 'conn' in locals() and conn is not None:
            cur.close()
            conn.close()
            print("🔌 Соединение с базой данных закрыто.")

def main():
    """
    Главная функция скрипта.
    """
    print("🚀 Запуск скрипта заполнения моделей Gemini для LiteLLM v1.70.0")
    print("=" * 60)
    
    # Загрузка API ключей
    api_keys = load_api_keys()
    if not api_keys:
        print("❌ Не удалось загрузить API ключи. Выход.")
        sys.exit(1)
    
    # Подтверждение операции
    print(f"⚠️  Внимание: Будет создано {len(api_keys)} моделей с именем '{LOAD_BALANCED_MODEL_NAME}'")
    print("⚠️  Все существующие модели с таким именем будут удалены!")
    
    # Заполнение моделей
    if seed_models(api_keys):
        print("=" * 60)
        print("🎉 Заполнение моделей завершено успешно!")
        print(f"🎯 Модель '{LOAD_BALANCED_MODEL_NAME}' готова к использованию")
        print("💡 Используйте эту модель в API запросах для балансировки нагрузки")
    else:
        print("=" * 60)
        print("❌ Заполнение моделей завершилось с ошибками!")
        sys.exit(1)

if __name__ == "__main__":
    main()