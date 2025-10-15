from datetime import datetime

def simulate_booking_filtering():
    """Симуляция фильтрации бронирований"""
    
    # Устанавливаем "текущую" дату и время для теста
    test_now = datetime(2025, 10, 15, 9, 0, 0)  # 15 октября 2025, 9:00
    print(f"Тестовая дата и время: {test_now}")
    print()
    
    # Симулируем список бронирований
    test_bookings = [
        # Прошедшие дни
        ("10.10.2025", "09:00", "10:00", "user1"),
        ("14.10.2025", "14:00", "15:00", "user2"),
        
        # Сегодня (15.10.2025) - прошедшие бронирования
        ("15.10.2025", "08:00", "09:00", "user3"),  # Закончилось в 9:00
        ("15.10.2025", "08:30", "09:00", "user4"),  # Закончилось в 9:00
        
        # Сегодня (15.10.2025) - будущие бронирования
        ("15.10.2025", "09:00", "10:00", "user5"),  # Начинается сейчас
        ("15.10.2025", "09:30", "10:30", "user6"),  # Начинается через 30 мин
        ("15.10.2025", "10:00", "11:00", "user7"),  # Начинается через 1 час
        ("15.10.2025", "14:00", "15:00", "user8"),  # Вечер
        
        # Будущие дни
        ("16.10.2025", "10:00", "11:00", "user9"),
        ("20.10.2025", "11:00", "12:00", "user10"),
        ("01.11.2025", "09:00", "10:00", "user11"),
    ]
    
    print("Все бронирования:")
    for date, start_time, end_time, user_name in test_bookings:
        print(f"  {date} {start_time}-{end_time} (@{user_name})")
    print()
    
    # Применяем алгоритм фильтрации (как в функции get_all_bookings)
    filtered_bookings = []
    
    current_date_numeric = test_now.strftime("%Y%m%d")
    current_time = test_now.strftime("%H:%M")
    
    print(f"Фильтруем по дате: {current_date_numeric} и времени: {current_time}")
    print()
    
    for date, start_time, end_time, user_name in test_bookings:
        try:
            # Преобразуем дату из формата DD.MM.YYYY в YYYYMMDD
            booking_date = datetime.strptime(date, "%d.%m.%Y")
            booking_date_numeric = booking_date.strftime("%Y%m%d")
            
            # Если дата больше текущей - добавляем
            if booking_date_numeric > current_date_numeric:
                filtered_bookings.append((date, start_time, end_time, user_name))
                print(f"  ✓ {date} {start_time}-{end_time} (@{user_name}) - дата больше текущей")
            # Если дата равна текущей - проверяем время
            elif booking_date_numeric == current_date_numeric:
                # Сравниваем время начала с текущим временем
                if start_time >= current_time:
                    filtered_bookings.append((date, start_time, end_time, user_name))
                    print(f"  ✓ {date} {start_time}-{end_time} (@{user_name}) - сегодня, но время в будущем")
                else:
                    print(f"  ✗ {date} {start_time}-{end_time} (@{user_name}) - сегодня, но время прошло")
            else:
                print(f"  ✗ {date} {start_time}-{end_time} (@{user_name}) - дата в прошлом")
                
        except ValueError:
            print(f"  ✗ {date} {start_time}-{end_time} (@{user_name}) - некорректный формат даты")
    
    print()
    print("Результат фильтрации (только будущие бронирования):")
    for date, start_time, end_time, user_name in filtered_bookings:
        print(f"  {date} {start_time}-{end_time} (@{user_name})")
    
    print(f"\nВсего бронирований: {len(test_bookings)}")
    print(f"После фильтрации: {len(filtered_bookings)}")
    
    return filtered_bookings

def test_different_scenarios():
    """Тестирование разных сценариев"""
    
    print("\n" + "="*50)
    print("ТЕСТ 1: Время 15:00, проверяем бронирования на тот же день")
    print("="*50)
    
    test_now = datetime(2025, 10, 15, 15, 0, 0)
    print(f"Тестовая дата и время: {test_now}")
    
    test_bookings = [
        ("15.10.2025", "09:00", "10:00", "user1"),  # Прошло
        ("15.10.2025", "14:00", "15:00", "user2"),  # Закончилось
        ("15.10.2025", "15:00", "16:00", "user3"),  # Начинается сейчас
        ("15.10.2025", "16:00", "17:00", "user4"),  # Будущее
        ("16.10.2025", "10:00", "11:00", "user5"),  # Будущий день
    ]
    
    current_date_numeric = test_now.strftime("%Y%m%d")
    current_time = test_now.strftime("%H:%M")
    
    filtered = []
    for date, start_time, end_time, user_name in test_bookings:
        booking_date = datetime.strptime(date, "%d.%m.%Y")
        booking_date_numeric = booking_date.strftime("%Y%m%d")
        
        if booking_date_numeric > current_date_numeric or (booking_date_numeric == current_date_numeric and start_time >= current_time):
            filtered.append((date, start_time, end_time, user_name))
    
    print("Будущие бронирования:")
    for date, start_time, end_time, user_name in filtered:
        print(f"  {date} {start_time}-{end_time} (@{user_name})")

if __name__ == "__main__":
    simulate_booking_filtering()
    test_different_scenarios()