import sqlite3
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

class DatabaseManager:
    def __init__(self, db_file: str):
        self.db_file = db_file
        self.init_db()

    def get_connection(self):
        """Получение соединения с базой данных"""
        return sqlite3.connect(self.db_file)
    
    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                date TEXT,
                start_time TEXT,
                end_time TEXT,
                notified BOOLEAN DEFAULT FALSE
            )
        ''')
        conn.commit()
        conn.close()
    
    def save_booking(self, user_id: int, user_name: str, date: str, start_time: str, end_time: str) -> None:
        """Сохранение бронирования"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bookings (user_id, user_name, date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, user_name, date, start_time, end_time))
        conn.commit()
        conn.close()
    
    def is_conflict(self, date: str, start_time: str, end_time: str) -> bool:
        """Проверка на пересечение бронирований"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM bookings 
            WHERE date = ? AND 
                  (start_time < ? AND end_time > ?)
        """, (date, end_time, start_time))
        result = cursor.fetchone()
        conn.close()
        return result is not None
    
    def get_conflicting_booking(self, date: str, start_time: str, end_time: str) -> Optional[Tuple]:
        """Получение информации о конфликтующем бронировании"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT user_name, start_time, end_time FROM bookings 
            WHERE date = ? AND 
                  (start_time < ? AND end_time > ?)
        """, (date, end_time, start_time))
        result = cursor.fetchone()
        conn.close()
        return result
    
    def get_all_bookings(self) -> List[Tuple]:
        """Получение всех активных бронирований (только будущие)"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        current_date = datetime.now().strftime("%d.%m.%Y")
        cursor.execute("""
            SELECT date, start_time, end_time, user_name 
            FROM bookings 
            WHERE date >= ? 
            ORDER BY date, start_time
        """, (current_date,))
        bookings = cursor.fetchall()
        conn.close()
        return bookings
    
    def get_user_bookings(self, user_id: int) -> List[Tuple]:
        """Получение бронирований пользователя (только будущие)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        current_date = datetime.now().strftime("%d.%m.%Y")
        cursor.execute("""
            SELECT date, start_time, end_time 
            FROM bookings 
            WHERE user_id = ? AND date >= ? 
            ORDER BY date, start_time
        """, (user_id, current_date))
        bookings = cursor.fetchall()
        conn.close()
        return bookings
    
    def cancel_user_bookings(self, user_id: int) -> bool:
        """Отмена бронирований пользователя"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE user_id = ?", (user_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count > 0
    
    def get_bookings_for_notification(self, reminder_minutes: int) -> List[Tuple]:
        """Получение бронирований для уведомления"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        now = datetime.now()
        reminder_time = now + timedelta(minutes=reminder_minutes)
        
        current_date = now.strftime("%d.%m.%Y")
        reminder_date = reminder_time.strftime("%d.%m.%Y")
        current_time = now.strftime("%H:%M")
        reminder_time_str = reminder_time.strftime("%H:%M")
        
        cursor.execute("""
            SELECT id, user_id, user_name, date, start_time, end_time 
            FROM bookings 
            WHERE (
                (date = ? AND start_time >= ? AND start_time <= ?) OR
                (date = ? AND start_time <= ?)
            ) 
            AND notified = FALSE
        """, (current_date, current_time, reminder_time_str, reminder_date, reminder_time_str))
        
        bookings = cursor.fetchall()
        conn.close()
        return bookings
    
    def mark_as_notified(self, booking_id: int) -> None:
        """Отметить бронирование как уведомленное"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        cursor.execute("UPDATE bookings SET notified = TRUE WHERE id = ?", (booking_id,))
        conn.commit()
        conn.close()

# Глобальный экземпляр менеджера базы данных
db_manager = None

def init_db_manager(db_file: str) -> DatabaseManager:
    """Инициализация менеджера базы данных"""
    global db_manager
    db_manager = DatabaseManager(db_file)
    return db_manager

def get_db_manager() -> DatabaseManager:
    """Получение экземпляра менеджера базы данных"""
    global db_manager
    if db_manager is None:
        raise RuntimeError("Database manager not initialized")
    return db_manager