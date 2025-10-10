import json
import os
from datetime import datetime

class Config:
    def __init__(self, config_file='settings.json'):
        self.config_file = config_file
        self.load_config()
    
    def load_config(self):
        """Загружает конфигурацию из файла"""
        if not os.path.exists(self.config_file):
            self.create_default_config()
        
        with open(self.config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        self.token = config.get('token', 'YOUR_BOT_TOKEN_HERE')
        self.working_hours = config.get('working_hours', {'start': '08:00', 'end': '20:00'})
        self.booking_range_days = config.get('booking_range_days', 14)
        self.time_intervals = config.get('time_intervals', [15, 30, 45, 60, 75, 90, 105, 120, 150, 180, 210, 240])
        self.database_file = config.get('database_file', 'meeting_room.db')
        
        # Настройки уведомлений
        self.notifications = config.get('notifications', {
            'enable': True,
            'reminder_minutes': 15,
            'reminder_message': '⏰ Напоминание: Ваша бронь переговорной комнаты начинается через {minutes} минут!\n\n📅 Дата: {date}\n🕐 Время: {start_time} - {end_time}\n📍 Место: Переговорная комната'
        })
    
    def create_default_config(self):
        """Создаёт файл конфигурации по умолчанию"""
        default_config = {
            "token": "YOUR_BOT_TOKEN_HERE",
            "working_hours": {
                "start": "08:00",
                "end": "20:00"
            },
            "booking_range_days": 14,
            "time_intervals": [15, 30, 45, 60, 75, 90, 105, 120, 150, 180, 210, 240],
            "database_file": "meeting_room.db",
            "notifications": {
                "enable": True,
                "reminder_minutes": 15,
                "reminder_message": "⏰ Напоминание: Ваша бронь переговорной комнаты начинается через {minutes} минут!\n\n📅 Дата: {date}\n🕐 Время: {start_time} - {end_time}\n📍 Место: Переговорная комната"
            }
        }
        
        with open(self.config_file, 'w', encoding='utf-8') as f:
            json.dump(default_config, f, indent=4, ensure_ascii=False)
        
        print(f"Создан файл конфигурации: {self.config_file}")
        print("Пожалуйста, укажите токен бота в файле settings.json")
    
    def get_working_start_time(self):
        """Возвращает время начала рабочего дня как объект time"""
        return datetime.strptime(self.working_hours['start'], '%H:%M').time()
    
    def get_working_end_time(self):
        """Возвращает время окончания рабочего дня как объект time"""
        return datetime.strptime(self.working_hours['end'], '%H:%M').time()
    
    def get_time_intervals_formatted(self):
        """Возвращает отформатированный список интервалов"""
        formatted_intervals = []
        for minutes in self.time_intervals:
            hours = minutes // 60
            mins = minutes % 60
            text = ""
            if hours > 0:
                text += f"{hours} ч "
            if mins > 0:
                text += f"{mins} мин"
            formatted_intervals.append((minutes, text.strip()))
        return formatted_intervals

# Глобальный объект конфигурации
config = Config()