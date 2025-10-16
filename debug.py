# test_debug.py
import sys
sys.path.append('.')

from debug_db import init_db_manager

def test_debug():
    # Инициализируем базу данных
    db_manager = init_db_manager("test_meeting_room.db")
    
    # Добавим тестовые данные вручную
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # Вставим тестовые данные в stats
    test_data = [
        (1, "user1", 2025, 10, 5, 300),  # 5 бронирований, 5 часов
        (2, "user2", 2025, 10, 3, 180),  # 3 бронирования, 3 часа
        (3, "user3", 2025, 10, 8, 480),  # 8 бронирований, 8 часов
        (1, "user1", 2025, 9, 2, 120),   # 2 бронирования в сентябре
    ]
    
    for user_id, username, year, month, bookings, duration in test_data:
        cursor.execute("INSERT INTO users (user_id, username) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET username=excluded.username", (user_id, username))
        cursor.execute("""
            INSERT INTO stats (user_id, year, month, total_bookings, total_duration_minutes)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, year, month, bookings, duration))
    
    conn.commit()
    conn.close()
    
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