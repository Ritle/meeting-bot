import sys
import os
from datetime import datetime

# Добавляем текущую директорию в путь Python
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import init_db_manager

def debug_recalculate_stats(db_file="meeting_room.db"):
    """Отладочный пересчет статистики"""
    
    print(f"=== Отладка пересчета статистики для базы: {db_file} ===")
    
    # Инициализируем менеджер базы данных
    db_manager = init_db_manager(db_file)
    
    # Проверим, какие бронирования есть
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    
    # Проверим структуру таблицы bookings
    cursor.execute("PRAGMA table_info(bookings)")
    table_info = cursor.fetchall()
    print(f"Структура таблицы bookings: {table_info}")
    
    # Получим все бронирования
    cursor.execute("SELECT * FROM bookings")
    all_bookings = cursor.fetchall()
    print(f"Найдено бронирований: {len(all_bookings)}")
    
    if all_bookings:
        print("Примеры бронирований:")
        for i, booking in enumerate(all_bookings[:5]):  # Показываем первые 5
            print(f"  {i+1}. {booking}")
    
    # Проверим структуру таблицы stats
    cursor.execute("PRAGMA table_info(stats)")
    stats_info = cursor.fetchall()
    print(f"Структура таблицы stats: {stats_info}")
    
    # Проверим, что есть в таблице stats
    cursor.execute("SELECT * FROM stats")
    stats_data = cursor.fetchall()
    print(f"Данные в stats: {len(stats_data)} записей")
    if stats_data:
        print("Примеры из stats:")
        for i, stat in enumerate(stats_data[:5]):
            print(f"  {i+1}. {stat}")
    
    conn.close()
    
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
    
    # Обрабатываем каждое бронирование с отладкой
    processed_count = 0
    error_count = 0
    
    for i, (booking_id, user_id, user_name, date, start_time, end_time, notified) in enumerate(all_bookings):
        print(f"\nОбработка бронирования {i+1}: ID={booking_id}, user={user_id}, date={date}, time={start_time}-{end_time}")
        
        try:
            # Проверим формат даты
            print(f"  Исходная дата: '{date}' (type: {type(date)})")
            print(f"  Исходное время: '{start_time}' - '{end_time}'")
            
            # Рассчитываем длительность в минутах
            start_dt = datetime.strptime(start_time, "%H:%M")
            end_dt = datetime.strptime(end_time, "%H:%M")
            duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
            print(f"  Длительность: {duration_minutes} минут")
            
            # Получаем год и месяц из даты
            booking_date = datetime.strptime(date, "%d.%m.%Y")
            year = booking_date.year
            month = booking_date.month
            print(f"  Год: {year}, Месяц: {month}")
            
            # Проверим, есть ли уже запись для этого пользователя и месяца
            conn = db_manager.get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT total_bookings, total_duration_minutes 
                FROM stats 
                WHERE user_id = ? AND year = ? AND month = ?
            """, (user_id, year, month))
            
            result = cursor.fetchone()
            print(f"  Существующая запись: {result}")
            
            if result:
                # Обновляем существующую запись
                total_bookings = result[0] + 1
                total_duration = result[1] + duration_minutes
                cursor.execute("""
                    UPDATE stats 
                    SET total_bookings = ?, total_duration_minutes = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND year = ? AND month = ?
                """, (total_bookings, total_duration, user_id, year, month))
                print(f"  Обновлена запись: bookings={total_bookings}, duration={total_duration}")
            else:
                # Создаем новую запись
                cursor.execute("""
                    INSERT INTO stats (user_id, year, month, total_bookings, total_duration_minutes)
                    VALUES (?, ?, ?, 1, ?)
                """, (user_id, year, month, duration_minutes))
                print(f"  Создана новая запись: bookings=1, duration={duration_minutes}")
            
            conn.commit()
            conn.close()
            
            processed_count += 1
            
        except ValueError as ve:
            print(f"  ОШИБКА: Неверный формат даты/времени - {ve}")
            print(f"  Данные: date='{date}', start='{start_time}', end='{end_time}'")
            error_count += 1
            continue
        except Exception as e:
            print(f"  ОШИБКА: {e}")
            error_count += 1
            continue
    
    print(f"\n=== Результаты ===")
    print(f"Обработано бронирований: {processed_count}")
    print(f"Ошибок: {error_count}")
    print(f"Всего бронирований в базе: {len(all_bookings)}")
    
    # Проверим, что записалось в статистику
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stats")
    final_stats = cursor.fetchall()
    conn.close()
    
    print(f"Записей в статистике после обработки: {len(final_stats)}")
    
    if final_stats:
        print("Примеры записей в статистике:")
        for stat in final_stats[:10]:
            print(f"  {stat}")
    
    # Проверим статистику за текущий месяц
    current_year = datetime.now().year
    current_month = datetime.now().month
    print(f"\nСтатистика за текущий месяц ({current_year}-{current_month:02d}):")
    
    conn = db_manager.get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT s.user_id, u.username, s.total_bookings, s.total_duration_minutes
        FROM stats s
        LEFT JOIN users u ON s.user_id = u.user_id
        WHERE s.year = ? AND s.month = ?
    """, (current_year, current_month))
    current_month_stats = cursor.fetchall()
    conn.close()
    
    if current_month_stats:
        for user_id, username, bookings, duration in current_month_stats:
            hours = duration // 60
            mins = duration % 60
            duration_text = f"{hours}ч {mins}мин" if hours > 0 else f"{mins}мин"
            print(f"  {username} (ID: {user_id}): {bookings} брон., {duration_text}")
    else:
        print("  Нет статистики за текущий месяц")

def main():
    if len(sys.argv) > 1:
        db_file = sys.argv[1]
    else:
        db_file = "meeting_room.db"
    
    try:
        debug_recalculate_stats(db_file)
    except Exception as e:
        print(f"Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()