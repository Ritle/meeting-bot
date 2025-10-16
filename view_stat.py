import sys
import os
import sqlite3
from datetime import datetime

def view_stats(db_file="meeting_room.db"):
    """Просмотр таблицы статистики"""
    
    print(f"=== Просмотр статистики из базы: {db_file} ===")
    
    # Проверяем, существует ли файл базы данных
    if not os.path.exists(db_file):
        print(f"❌ Файл базы данных {db_file} не найден!")
        return
    
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Проверяем, есть ли таблица stats
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='stats';")
        if not cursor.fetchone():
            print("❌ Таблица stats не найдена в базе данных!")
            conn.close()
            return
        
        # Получаем все записи из таблицы stats
        cursor.execute("""
            SELECT s.id, s.user_id, u.username, s.year, s.month, s.total_bookings, s.total_duration_minutes, s.created_at, s.updated_at
            FROM stats s
            LEFT JOIN users u ON s.user_id = u.user_id
            ORDER BY s.year DESC, s.month DESC, s.total_bookings DESC
        """)
        
        all_stats = cursor.fetchall()
        
        if not all_stats:
            print("📊 Таблица статистики пуста")
            conn.close()
            return
        
        print(f"📊 Найдено {len(all_stats)} записей в статистике")
        print()
        
        # Выводим заголовок таблицы
        print(f"{'ID':<4} {'User ID':<8} {'Username':<15} {'Year':<6} {'Month':<6} {'Bookings':<8} {'Duration (min)':<13} {'Created':<20}")
        print("-" * 100)
        
        # Выводим данные
        for record in all_stats:
            record_id, user_id, username, year, month, total_bookings, duration_minutes, created_at, updated_at = record
            username = username or f"user_{user_id}"  # Если username None, используем user_id
            duration_hours = duration_minutes // 60
            duration_mins = duration_minutes % 60
            duration_text = f"{duration_hours}ч {duration_mins}мин" if duration_hours > 0 else f"{duration_mins}мин"
            
            print(f"{record_id:<4} {user_id:<8} {username:<15} {year:<6} {month:<6} {total_bookings:<8} {duration_text:<13} {created_at[:19] if created_at else '':<20}")
        
        print()
        
        # Показываем агрегированную статистику
        print("=== Агрегированная статистика ===")
        
        # Топ пользователей по количеству бронирований за всё время
        cursor.execute("""
            SELECT s.user_id, u.username, SUM(s.total_bookings) as total_bookings
            FROM stats s
            LEFT JOIN users u ON s.user_id = u.user_id
            GROUP BY s.user_id
            ORDER BY total_bookings DESC
            LIMIT 10
        """)
        
        top_bookings = cursor.fetchall()
        print("\n📈 Топ пользователей по количеству бронирований за всё время:")
        for i, (user_id, username, total) in enumerate(top_bookings, 1):
            username = username or f"user_{user_id}"
            print(f"  {i:2d}. {username:<15} - {total} бронирований")
        
        # Топ пользователей по длительности за всё время
        cursor.execute("""
            SELECT s.user_id, u.username, SUM(s.total_duration_minutes) as total_duration
            FROM stats s
            LEFT JOIN users u ON s.user_id = u.user_id
            GROUP BY s.user_id
            ORDER BY total_duration DESC
            LIMIT 10
        """)
        
        top_duration = cursor.fetchall()
        print("\n⏱️  Топ пользователей по длительности бронирования за всё время:")
        for i, (user_id, username, total_minutes) in enumerate(top_duration, 1):
            username = username or f"user_{user_id}"
            total_hours = total_minutes // 60
            total_mins = total_minutes % 60
            duration_text = f"{total_hours}ч {total_mins}мин" if total_hours > 0 else f"{total_mins}мин"
            print(f"  {i:2d}. {username:<15} - {duration_text} ({total_minutes} мин)")
        
        # Статистика по месяцам
        cursor.execute("""
            SELECT year, month, SUM(total_bookings) as monthly_bookings, SUM(total_duration_minutes) as monthly_duration
            FROM stats
            GROUP BY year, month
            ORDER BY year DESC, month DESC
            LIMIT 10
        """)
        
        monthly_stats = cursor.fetchall()
        print("\n📅 Статистика по месяцам:")
        for year, month, bookings, duration in monthly_stats:
            duration_hours = duration // 60
            duration_mins = duration % 60
            duration_text = f"{duration_hours}ч {duration_mins}мин" if duration_hours > 0 else f"{duration_mins}мин"
            print(f"  {year}-{month:02d}: {bookings} брон., {duration_text}")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Ошибка при чтении базы данных: {e}")
        import traceback
        traceback.print_exc()

def main():
    if len(sys.argv) > 1:
        db_file = sys.argv[1]
    else:
        db_file = "meeting_room.db"
    
    view_stats(db_file)

if __name__ == "__main__":
    main()