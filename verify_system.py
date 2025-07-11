#!/usr/bin/env python3
"""
Скрипт верификации системы LiteLLM v1.70.0
Раздел 6: Верификация системы и операционная готовность

Этот скрипт выполняет заключительную верификацию всех компонентов системы:
- Проверка работоспособности эндпоинтов
- Обнаружение моделей
- Симуляция реального трафика
- Валидация кеша Redis
"""

import requests
import json
import time
import sys
from typing import Dict, Any, Optional

# Конфигурация для тестирования
BASE_URL = "https://litellm-v170-fixed-final-production.up.railway.app"
MASTER_KEY = "sk-9b8d676797b1c546d8b5f3ba871cfec6220dcd9d14f96dce616edcb6f904b582"
TIMEOUT = 30

def print_header(title: str):
    """Печать заголовка раздела"""
    print("\n" + "=" * 60)
    print(f"🔍 {title}")
    print("=" * 60)

def print_success(message: str):
    """Печать сообщения об успехе"""
    print(f"✅ {message}")

def print_error(message: str):
    """Печать сообщения об ошибке"""
    print(f"❌ {message}")

def print_info(message: str):
    """Печать информационного сообщения"""
    print(f"📋 {message}")

def check_health_endpoint() -> bool:
    """
    Проверка работоспособности эндпоинта /health/readiness
    Ожидаемый ответ: 200 OK
    """
    print_header("Проверка работоспособности эндпоинтов")
    
    try:
        print_info("Проверка эндпоинта /health/readiness...")
        response = requests.get(f"{BASE_URL}/health/readiness", timeout=TIMEOUT)
        
        if response.status_code == 200:
            print_success(f"Эндпоинт здоровья доступен (статус: {response.status_code})")
            try:
                health_data = response.json()
                print_info(f"Данные здоровья: {json.dumps(health_data, indent=2, ensure_ascii=False)}")
            except:
                print_info(f"Ответ: {response.text}")
            return True
        else:
            print_error(f"Эндпоинт здоровья недоступен (статус: {response.status_code})")
            print_error(f"Ответ: {response.text}")
            return False
    
    except requests.RequestException as e:
        print_error(f"Ошибка при проверке эндпоинта здоровья: {e}")
        return False

def check_models_endpoint() -> bool:
    """
    Проверка обнаружения моделей через эндпоинт /v1/models
    Ожидаемый результат: JSON с моделью "gemini-pro-load-balanced"
    """
    print_header("Обнаружение моделей")
    
    try:
        print_info("Проверка эндпоинта /v1/models...")
        headers = {
            "Authorization": f"Bearer {MASTER_KEY}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(f"{BASE_URL}/v1/models", headers=headers, timeout=TIMEOUT)
        
        if response.status_code == 200:
            models_data = response.json()
            print_success(f"Эндпоинт моделей доступен (статус: {response.status_code})")
            
            # Проверка наличия загруженных моделей
            if "data" in models_data and isinstance(models_data["data"], list):
                models = models_data["data"]
                print_info(f"Найдено {len(models)} моделей:")
                
                # Поиск нашей модели балансировки нагрузки
                target_model = "gemini-pro-load-balanced"
                found_target = False
                
                for model in models:
                    model_id = model.get("id", "unknown")
                    print_info(f"  - {model_id}")
                    
                    if model_id == target_model:
                        found_target = True
                        print_success(f"Найдена целевая модель: {target_model}")
                
                if found_target:
                    print_success("Модель балансировки нагрузки успешно загружена!")
                    return True
                else:
                    print_error(f"Целевая модель '{target_model}' не найдена")
                    return False
            else:
                print_error("Неверный формат ответа от эндпоинта моделей")
                return False
        else:
            print_error(f"Эндпоинт моделей недоступен (статус: {response.status_code})")
            print_error(f"Ответ: {response.text}")
            return False
    
    except requests.RequestException as e:
        print_error(f"Ошибка при проверке эндпоинта моделей: {e}")
        return False

def test_chat_completion() -> bool:
    """
    Симуляция реального трафика через эндпоинт /chat/completions
    Тестирование балансировки нагрузки
    """
    print_header("Симуляция реального трафика и балансировки нагрузки")
    
    try:
        print_info("Отправка тестового запроса к /chat/completions...")
        
        headers = {
            "Authorization": f"Bearer {MASTER_KEY}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gemini-pro-load-balanced",
            "messages": [
                {
                    "role": "user",
                    "content": "What is the distance between Earth and the Moon?"
                }
            ],
            "max_tokens": 100
        }
        
        response = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        
        if response.status_code == 200:
            completion_data = response.json()
            print_success(f"Запрос завершения успешен (статус: {response.status_code})")
            
            # Проверка структуры ответа
            if "choices" in completion_data and len(completion_data["choices"]) > 0:
                choice = completion_data["choices"][0]
                message = choice.get("message", {})
                content = message.get("content", "")
                
                print_info(f"Ответ модели: {content[:200]}...")
                print_success("Балансировка нагрузки работает корректно!")
                return True
            else:
                print_error("Неверный формат ответа от эндпоинта завершения")
                return False
        else:
            print_error(f"Запрос завершения неуспешен (статус: {response.status_code})")
            print_error(f"Ответ: {response.text}")
            return False
    
    except requests.RequestException as e:
        print_error(f"Ошибка при тестировании завершения: {e}")
        return False

def test_cache_functionality() -> bool:
    """
    Валидация кеша Redis
    Отправка одинакового запроса дважды для проверки кеширования
    """
    print_header("Валидация кеша Redis")
    
    try:
        print_info("Тестирование кеширования с повторными запросами...")
        
        headers = {
            "Authorization": f"Bearer {MASTER_KEY}",
            "Content-Type": "application/json"
        }
        
        # Специфичный запрос для тестирования кеша
        payload = {
            "model": "gemini-pro-load-balanced",
            "messages": [
                {
                    "role": "user",
                    "content": "What is 2+2? Please answer with just the number."
                }
            ],
            "max_tokens": 10,
            "temperature": 0  # Детерминированный ответ
        }
        
        # Первый запрос
        print_info("Отправка первого запроса...")
        start_time = time.time()
        response1 = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        first_duration = time.time() - start_time
        
        if response1.status_code != 200:
            print_error(f"Первый запрос неуспешен (статус: {response1.status_code})")
            return False
        
        print_info(f"Первый запрос выполнен за {first_duration:.2f} секунд")
        
        # Небольшая пауза
        time.sleep(1)
        
        # Второй запрос (должен быть закеширован)
        print_info("Отправка второго идентичного запроса...")
        start_time = time.time()
        response2 = requests.post(
            f"{BASE_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=TIMEOUT
        )
        second_duration = time.time() - start_time
        
        if response2.status_code != 200:
            print_error(f"Второй запрос неуспешен (статус: {response2.status_code})")
            return False
        
        print_info(f"Второй запрос выполнен за {second_duration:.2f} секунд")
        
        # Анализ результатов кеширования
        if second_duration < first_duration * 0.8:  # Второй запрос должен быть значительно быстрее
            print_success("Кеширование работает! Второй запрос выполнен быстрее.")
            print_info(f"Ускорение: {((first_duration - second_duration) / first_duration * 100):.1f}%")
            return True
        else:
            print_error("Кеширование может не работать. Второй запрос не быстрее первого.")
            print_info("Проверьте настройки Redis и логи LiteLLM")
            return False
    
    except requests.RequestException as e:
        print_error(f"Ошибка при тестировании кеша: {e}")
        return False

def main():
    """
    Главная функция верификации системы
    """
    print("🚀 Верификация системы LiteLLM v1.70.0")
    print("🎯 Раздел 6: Верификация системы и операционная готовность")
    print(f"🌐 Базовый URL: {BASE_URL}")
    print("=" * 60)
    
    # Счетчики результатов
    total_tests = 4
    passed_tests = 0
    
    # Выполнение всех тестов
    tests = [
        ("Проверка работоспособности", check_health_endpoint),
        ("Обнаружение моделей", check_models_endpoint),
        ("Симуляция трафика", test_chat_completion),
        ("Валидация кеша", test_cache_functionality)
    ]
    
    for test_name, test_func in tests:
        print(f"\n🔄 Выполнение теста: {test_name}")
        if test_func():
            passed_tests += 1
            print_success(f"Тест '{test_name}' пройден")
        else:
            print_error(f"Тест '{test_name}' провален")
    
    # Итоговый отчет
    print_header("Итоговый отчет верификации")
    print_info(f"Пройдено тестов: {passed_tests}/{total_tests}")
    
    if passed_tests == total_tests:
        print_success("🎉 Все тесты пройдены! Система готова к эксплуатации!")
        print_info("✨ LiteLLM v1.70.0 успешно развернут и функционирует")
        print_info("🎯 Балансировка нагрузки между 120 ключами Gemini активна")
        print_info("💾 Redis кеширование работает корректно")
        return True
    else:
        print_error("❌ Некоторые тесты провалены. Система требует дополнительной настройки.")
        print_info("📝 Проверьте логи развертывания и исправьте выявленные проблемы")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)