import sqlite3
import shutil
import os
from datetime import datetime

def backup_database(source_db="meeting_room.db", backup_dir="backups"):
    """Создание бекапа базы данных"""
    
    # Создаем директорию для бекапов, если её нет
    os.makedirs(backup_dir, exist_ok=True)
    
    # Генерируем имя файла бекапа с текущей датой и временем
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_filename = f"meeting_room_backup_{timestamp}.db"
    backup_path = os.path.join(backup_dir, backup_filename)
    
    try:
        # Проверяем, существует ли исходная база данных
        if not os.path.exists(source_db):
            print(f"❌ Файл базы данных {source_db} не найден!")
            return False
        
        # Создаем бекап
        shutil.copy2(source_db, backup_path)
        
        print(f"✅ Бекап создан: {backup_path}")
        print(f"📦 Размер бекапа: {os.path.getsize(backup_path)} байт")
        
        # Удаляем старые бекапы (оставляем только последние 5)
        cleanup_old_backups(backup_dir)
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при создании бекапа: {e}")
        return False

def cleanup_old_backups(backup_dir="backups", keep_last=5):
    """Удаление старых бекапов (оставляем последние N)"""
    
    try:
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
        backup_files.sort(reverse=True)  # Сортируем по убыванию (новые первыми)
        
        for old_backup in backup_files[keep_last:]:
            old_backup_path = os.path.join(backup_dir, old_backup)
            os.remove(old_backup_path)
            print(f"🗑️ Удален старый бекап: {old_backup}")
            
    except Exception as e:
        print(f"❌ Ошибка при удалении старых бекапов: {e}")

def list_backups(backup_dir="backups"):
    """Список всех бекапов"""
    
    try:
        backup_files = [f for f in os.listdir(backup_dir) if f.endswith('.db')]
        backup_files.sort(reverse=True)
        
        if not backup_files:
            print("📦 Нет доступных бекапов")
            return
        
        print("📦 Доступные бекапы:")
        for i, backup_file in enumerate(backup_files, 1):
            backup_path = os.path.join(backup_dir, backup_file)
            size = os.path.getsize(backup_path)
            print(f"  {i}. {backup_file} ({size} байт)")
            
    except Exception as e:
        print(f"❌ Ошибка при чтении списка бекапов: {e}")

def restore_database(backup_file, target_db="meeting_room.db", backup_dir="backups"):
    """Восстановление базы данных из бекапа"""
    
    backup_path = os.path.join(backup_dir, backup_file)
    
    try:
        if not os.path.exists(backup_path):
            print(f"❌ Файл бекапа {backup_path} не найден!")
            return False
        
        # Создаем резервную копию текущей базы перед восстановлением
        current_backup = f"meeting_room_before_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
        shutil.copy2(target_db, os.path.join(backup_dir, current_backup))
        print(f"💾 Создана резервная копия текущей базы: {current_backup}")
        
        # Восстанавливаем базу данных
        shutil.copy2(backup_path, target_db)
        print(f"✅ База данных восстановлена из: {backup_file}")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка при восстановлении базы данных: {e}")
        return False

def main():
    import sys
    
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        
        if command == "backup":
            backup_database()
        elif command == "list":
            list_backups()
        elif command == "restore" and len(sys.argv) > 2:
            backup_file = sys.argv[2]
            restore_database(backup_file)
        else:
            print("Использование:")
            print("  python backup_db.py backup    - создать бекап")
            print("  python backup_db.py list      - список бекапов")
            print("  python backup_db.py restore [имя_бекапа] - восстановить из бекапа")
    else:
        print("Создание бекапа базы данных...")
        backup_database()

if __name__ == "__main__":
    main()