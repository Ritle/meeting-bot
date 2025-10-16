import sys
import os
from datetime import datetime

# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db_manager, get_db_manager

def recalculate_stats():
    """Пересчет статистики для всех существующих бронирований"""
    
    print("=== Запуск пересчета статистики ===")
    
    # Инициализируем менеджер базы данных
    db_manager = init_db_manager("meeting_room.db")  # Укажи правильное имя файла
    
    # Получаем все бронирования
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT user_id, user_name, date, start_time, end_time 
        FROM bookings 
        ORDER BY date
    """)
    all_bookings = cursor.fetchall()
    conn.close()
    
    print(f"Найдено {len(all_bookings)} бронирований для обработки")
    
    if not all_bookings:
        print("Нет бронирований для обработки")
        return
    
    # Очищаем таблицу статистики
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stats")
    conn.commit()
    conn.close()
    
    print("Таблица статистики очищена")
    
    # Обновляем статистику для каждого бронирования
    processed_count = 0
    error_count = 0
    
    for user_id, user_name, date, start_time, end_time in all_bookings:
        try:
            # Рассчитываем длительность в минутах
            start_dt = datetime.strptime(start_time, "%H:%M")
            end_dt = datetime.strptime(end_time, "%H:%M")
            duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
            
            # Получаем год и месяц из даты
            booking_date = datetime.strptime(date, "%d.%m.%Y")
            year = booking_date.year
            month = booking_date.month
            
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            # Проверяем, есть ли уже запись для этого пользователя и месяца
            cursor.execute("""
                SELECT total_bookings, total_duration_minutes 
                FROM stats 
                WHERE user_id = ? AND year = ? AND month = ?
            """, (user_id, year, month))
            
            result = cursor.fetchone()
            
            if result:
                # Обновляем существующую запись
                total_bookings = result[0] + 1
                total_duration = result[1] + duration_minutes
                cursor.execute("""
                    UPDATE stats 
                    SET total_bookings = ?, total_duration_minutes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND year = ? AND month = ?
                """, (total_bookings, total_duration, user_id, year, month))
            else:
                # Создаем новую запись
                cursor.execute("""
                    INSERT INTO stats (user_id, year, month, total_bookings, total_duration_minutes)
                    VALUES (?, ?, ?, 1, ?)
                """, (user_id, year, month, duration_minutes))
            
            conn.commit()
            conn.close()
            
            processed_count += 1
            
            # Показываем прогресс каждые 100 записей
            if processed_count % 100 == 0:
                print(f"Обработано {processed_count} бронирований...")
                
        except Exception as e:
            print(f"Ошибка обработки бронирования {date} {start_time}-{end_time}: {e}")
            error_count += 1
            continue
    
    print(f"\n=== Результаты ===")
    print(f"Обработано бронирований: {processed_count}")
    print(f"Ошибок: {error_count}")
    print(f"Всего бронирований в базе: {len(all_bookings)}")
    
    # Показываем пример статистики
    print(f"\n=== Пример статистики ===")
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.year, s.month, u.username, s.total_bookings, s.total_duration_minutes
        FROM stats s
        JOIN users u ON s.user_id = u.user_id
        ORDER BY s.total_bookings DESC
        LIMIT 5
    """)
    sample_stats = cursor.fetchall()
    conn.close()
    
    if sample_stats:
        print("Топ 5 пользователей по количеству бронирований:")
        for year, month, username, bookings, duration in sample_stats:
            hours = duration // 60
            mins = duration % 60
            duration_text = f"{hours}ч {mins}мин" if hours > 0 else f"{mins}мин"
            print(f"  {username} ({year}-{month:02d}): {bookings} брон., {duration_text}")
    else:
        print("Статистика пуста")

def main():
    try:
        recalculate_stats()
    except Exception as e:
        print(f"Ошибка при пересчете статистики: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()