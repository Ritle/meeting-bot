# test_debug.py
import sys
sys.path.append('.')

from debug_db import init_db_manager

def test_debug():
    # Инициализируем базу данных
    db_manager = init_db_manager("meeting_room.db")
    
    # Добавим тестовые данные вручную
    print("=== Тест получения топа за октябрь ===")
    top_bookings = db_manager.get_top_users_by_bookings(2025, 10, 3)
    print(f"Топ бронирований: {top_bookings}")
    
    top_duration = db_manager.get_top_users_by_duration(2025, 10, 3)
    print(f"Топ по длительности: {top_duration}")
    
    print("\n=== Тест получения топа за всё время ===")
    all_time_bookings = db_manager.get_top_users_by_bookings(None, None, 3)
    print(f"Топ бронирований за всё время: {all_time_bookings}")
    
    all_time_duration = db_manager.get_top_users_by_duration(None, None, 3)
    print(f"Топ по длительности за всё время: {all_time_duration}")

if __name__ == "__main__":
    test_debug()