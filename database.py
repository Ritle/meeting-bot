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
        conn = self.get_connection()
        c = conn.cursor()
        
        # Таблица бронирований
        c.execute('''
            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                user_name TEXT,
                date TEXT,
                start_time TEXT,
                end_time TEXT,
                notified BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для отслеживания пользователей
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Таблица для хранения статистики
        c.execute('''
            CREATE TABLE IF NOT EXISTS stats (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                year INTEGER,
                month INTEGER,
                total_bookings INTEGER DEFAULT 0,
                total_duration_minutes INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Индексы для улучшения производительности
        c.execute('CREATE INDEX IF NOT EXISTS idx_bookings_date ON bookings(date)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_bookings_user_id ON bookings(user_id)')
        c.execute('CREATE INDEX IF NOT EXISTS idx_stats_user_year_month ON stats(user_id, year, month)')
        
        conn.commit()
        conn.close()
    
    def save_booking(self, user_id: int, user_name: str, date: str, start_time: str, end_time: str) -> int:
        """Сохранение бронирования и возвращение ID"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO bookings (user_id, user_name, date, start_time, end_time)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, user_name, date, start_time, end_time))
        booking_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Обновляем статистику
        self._update_user_stats(user_id, date, start_time, end_time)
        return booking_id
    
    def _update_user_stats(self, user_id: int, date: str, start_time: str, end_time: str):
        """Обновление статистики пользователя"""
        try:
            # Рассчитываем длительность в минутах
            start_dt = datetime.strptime(start_time, "%H:%M")
            end_dt = datetime.strptime(end_time, "%H:%M")
            duration_minutes = int((end_dt - start_dt).total_seconds() / 60)
            
            # Получаем год и месяц из даты
            booking_date = datetime.strptime(date, "%d.%m.%Y")
            year = booking_date.year
            month = booking_date.month
            
            conn = self.get_connection()
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
        except Exception as e:
            print(f"Ошибка обновления статистики: {e}")
    
    def save_user(self, user_id: int, username: str, first_name: str, last_name: str = None) -> None:
        """Сохранение информации о пользователе"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT OR REPLACE INTO users (user_id, username, first_name, last_name)
            VALUES (?, ?, ?, ?)
        """, (user_id, username, first_name, last_name))
        conn.commit()
        conn.close()
    
    def get_all_users(self) -> List[Tuple]:
        """Получение всех пользователей (кроме текущего)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT user_id, username, first_name FROM users")
        users = cursor.fetchall()
        conn.close()
        return users
    
    def is_conflict(self, date: str, start_time: str, end_time: str) -> bool:
        """Проверка на пересечение бронирований"""
        conn = self.get_connection()
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
        conn = self.get_connection()
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
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Получаем все бронирования
        cursor.execute("""
            SELECT date, start_time, end_time, user_name 
            FROM bookings 
            ORDER BY date, start_time
        """)
        all_bookings = cursor.fetchall()
        conn.close()
        
        # Фильтруем только будущие бронирования (с учетом даты и времени)
        filtered_bookings = []
        now = datetime.now()
        current_date_numeric = now.strftime("%Y%m%d")
        current_time = now.strftime("%H:%M")
        
        for date, start_time, end_time, user_name in all_bookings:
            try:
                # Преобразуем дату из формата DD.MM.YYYY в YYYYMMDD
                booking_date = datetime.strptime(date, "%d.%m.%Y")
                booking_date_numeric = booking_date.strftime("%Y%m%d")
                
                # Если дата больше текущей - добавляем
                if booking_date_numeric > current_date_numeric:
                    filtered_bookings.append((date, start_time, end_time, user_name))
                # Если дата равна текущей - проверяем время
                elif booking_date_numeric == current_date_numeric:
                    # Сравниваем время начала с текущим временем
                    if start_time >= current_time:
                        filtered_bookings.append((date, start_time, end_time, user_name))
            except ValueError:
                # Если формат даты некорректный, пропускаем
                continue
        
        return filtered_bookings
    
    def get_user_bookings(self, user_id: int) -> List[Tuple]:
        """Получение бронирований пользователя (только будущие)"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        # Получаем все бронирования пользователя
        cursor.execute("""
            SELECT date, start_time, end_time 
            FROM bookings 
            WHERE user_id = ? 
            ORDER BY date, start_time
        """, (user_id,))
        all_bookings = cursor.fetchall()
        conn.close()
        
        # Фильтруем только будущие бронирования (с учетом даты и времени)
        filtered_bookings = []
        now = datetime.now()
        current_date_numeric = now.strftime("%Y%m%d")
        current_time = now.strftime("%H:%M")
        
        for date, start_time, end_time in all_bookings:
            try:
                # Преобразуем дату из формата DD.MM.YYYY в YYYYMMDD
                booking_date = datetime.strptime(date, "%d.%m.%Y")
                booking_date_numeric = booking_date.strftime("%Y%m%d")
                
                # Если дата больше текущей - добавляем
                if booking_date_numeric > current_date_numeric:
                    filtered_bookings.append((date, start_time, end_time))
                # Если дата равна текущей - проверяем время
                elif booking_date_numeric == current_date_numeric:
                    # Сравниваем время начала с текущим временем
                    if start_time >= current_time:
                        filtered_bookings.append((date, start_time, end_time))
            except ValueError:
                # Если формат даты некорректный, пропускаем
                continue
        
        return filtered_bookings
    
    def cancel_user_bookings(self, user_id: int) -> bool:
        """Отмена бронирований пользователя"""
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM bookings WHERE user_id = ?", (user_id,))
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        return deleted_count > 0
    
    def get_bookings_for_notification(self, reminder_minutes: int) -> List[Tuple]:
        """Получение бронирований для уведомления"""
        conn = self.get_connection()
        cursor = conn.cursor()
        
        now = datetime.now()
        reminder_time = now + timedelta(minutes=reminder_minutes)
        
        current_date = now.strftime("%d.%m.%Y")
        reminder_date = reminder_time.strftime("%d.%m.%Y")
        current_time = now.strftime("%H:%M")
        reminder_time_str = reminder_time.strftime("%H:%M")
        
        # Фильтруем в SQL, но с учетом формата даты
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
        conn = self.get_connection()
        cursor = conn.cursor()
        cursor.execute("UPDATE bookings SET notified = TRUE WHERE id = ?", (booking_id,))
        conn.commit()
        conn.close()
    
    def get_top_users_by_bookings(self, year: int = None, month: int = None, limit: int = 3) -> List[Tuple]:
        """Получение топ пользователей по количеству бронирований"""
        # Ограничиваем лимит для безопасности
        limit = max(1, min(limit, 50))
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if year is not None and month is not None:
            # Топ за конкретный месяц
            query = f"""
                SELECT s.user_id, u.username, s.total_bookings
                FROM stats s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.year = ? AND s.month = ?
                ORDER BY s.total_bookings DESC
                LIMIT {limit}
            """
            cursor.execute(query, (year, month))
        elif year is not None:
            # Топ за конкретный год
            query = f"""
                SELECT s.user_id, u.username, SUM(s.total_bookings) as total_bookings
                FROM stats s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.year = ?
                GROUP BY s.user_id
                ORDER BY total_bookings DESC
                LIMIT {limit}
            """
            cursor.execute(query, (year,))
        else:
            # Топ за всё время
            query = f"""
                SELECT s.user_id, u.username, SUM(s.total_bookings) as total_bookings
                FROM stats s
                JOIN users u ON s.user_id = u.user_id
                GROUP BY s.user_id
                ORDER BY total_bookings DESC
                LIMIT {limit}
            """
            cursor.execute(query)
        
        results = cursor.fetchall()
        conn.close()
        return results

    def get_top_users_by_duration(self, year: int = None, month: int = None, limit: int = 3) -> List[Tuple]:
        """Получение топ пользователей по длительности бронирования"""
        # Ограничиваем лимит для безопасности
        limit = max(1, min(limit, 50))
        
        conn = self.get_connection()
        cursor = conn.cursor()
        
        if year is not None and month is not None:
            # Топ за конкретный месяц
            query = f"""
                SELECT s.user_id, u.username, s.total_duration_minutes
                FROM stats s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.year = ? AND s.month = ?
                ORDER BY s.total_duration_minutes DESC
                LIMIT 3
            """
            cursor.execute(query, (year, month))
        elif year is not None:
            # Топ за конкретный год
            query = f"""
                SELECT s.user_id, u.username, SUM(s.total_duration_minutes) as total_duration
                FROM stats s
                JOIN users u ON s.user_id = u.user_id
                WHERE s.year = ?
                GROUP BY s.user_id
                ORDER BY total_duration DESC
                LIMIT 3
            """
            cursor.execute(query, (year,))
        else:
            # Топ за всё время
            query = f"""
                SELECT s.user_id, u.username, SUM(s.total_duration_minutes) as total_duration
                FROM stats s
                JOIN users u ON s.user_id = u.user_id
                GROUP BY s.user_id
                ORDER BY total_duration DESC
                LIMIT 3
            """
            cursor.execute(query)
        
        results = cursor.fetchall()
        conn.close()
        return results

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