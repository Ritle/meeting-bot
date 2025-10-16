import re
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import sqlite3
import logging
from logging.handlers import RotatingFileHandler
from datetime import datetime, timedelta

from config import config
# В начале файла добавь:
from database import init_db_manager, get_db_manager
import threading
import time as time_module



# Настройка 

logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler(
            'logs/bot.log', 
            maxBytes=1024*1024*10,  # 10MB
            backupCount=5
        ),
        logging.StreamHandler()
    ]
)
# Глобальные переменные для уведомлений
notification_thread = None
stop_notification_thread = False

# Получение списка доступных дат
def get_available_dates():
    dates = []
    for i in range(config.booking_range_days):
        date = datetime.now() + timedelta(days=i)
        dates.append(date.strftime("%d.%m.%Y"))
    return dates

# Получение доступного времени
def get_time_matrix():
    times = []
    start_hour = config.get_working_start_time().hour
    end_hour = config.get_working_end_time().hour
    
    for hour in range(start_hour, end_hour + 1):
        times.append(f"{hour:02d}:00")
        if hour < end_hour:
            times.append(f"{hour:02d}:30")
    return times


# Отправка уведомления пользователю
def send_notification(bot, user_id, booking_info):
    try:
        message = config.notifications['reminder_message'].format(
            minutes=config.notifications['reminder_minutes'],
            date=booking_info['date'],
            start_time=booking_info['start_time'],
            end_time=booking_info['end_time']
        )
        bot.send_message(chat_id=user_id, text=message, parse_mode='Markdown')
        logger.info(f"Уведомление отправлено пользователю {user_id}")
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления пользователю {user_id}: {e}")

# Фоновый поток для уведомлений
def notification_worker(bot):
    """Фоновый поток для отправки уведомлений"""
    global stop_notification_thread
    
    while not stop_notification_thread:
        try:
            if config.notifications['enable']:
                db_manager = get_db_manager()
                bookings = db_manager.get_bookings_for_notification(config.notifications['reminder_minutes'])
                for booking in bookings:
                    booking_id, user_id, user_name, date, start_time, end_time = booking
                    
                    booking_info = {
                        'date': date,
                        'start_time': start_time,
                        'end_time': end_time
                    }
                    
                    send_notification(bot, user_id, booking_info)
                    db_manager.mark_as_notified(booking_id)
                    
            # Проверяем каждую минуту
            time_module.sleep(60)
            
        except Exception as e:
            logger.error(f"Ошибка в потоке уведомлений: {e}")
            time_module.sleep(60)

# Запуск потока уведомлений
def start_notification_thread(bot):
    global notification_thread, stop_notification_thread
    
    if notification_thread is None or not notification_thread.is_alive():
        stop_notification_thread = False
        notification_thread = threading.Thread(target=notification_worker, args=(bot,), daemon=True)
        notification_thread.start()
        logger.info("Поток уведомлений запущен")

# Остановка потока уведомлений
def stop_notification_thread_func():
    global stop_notification_thread
    stop_notification_thread = True
    logger.info("Поток уведомлений остановлен")


# Состояния пользователя
USER_STATES = {}

class BookingState:
    DATE = "date"
    START_TIME = "start_time"
    DURATION = "duration"

# Главное меню команд
def show_main_menu(update: Update, message_text="🤖 Бот для бронирования переговорной комнаты"):
    keyboard = [
        [InlineKeyboardButton("🚀 Начать бронирование", callback_data="book_room")],
        [InlineKeyboardButton("📋 Расписание", callback_data="show_schedule")],
        [InlineKeyboardButton("📅 Мои бронирования", callback_data="my_bookings")],
        [InlineKeyboardButton("🗑️ Отменить мои брони", callback_data="cancel_my_bookings")],
        [InlineKeyboardButton("📊 Рейтинг", callback_data="show_rating")],
        [InlineKeyboardButton("❓ Помощь", callback_data="help")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if hasattr(update, 'message') and update.message:
        update.message.reply_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')
    elif hasattr(update, 'callback_query'):
        update.callback_query.edit_message_text(message_text, reply_markup=reply_markup, parse_mode='Markdown')

# Команда /start
def start(update: Update, context: CallbackContext):

    user_id = update.effective_user.id
    user_name = update.effective_user.username or update.effective_user.first_name
    first_name = update.effective_user.first_name
    last_name = update.effective_user.last_name
    
    # Сохраняем информацию о пользователе
    db_manager = get_db_manager()
    db_manager.save_user(user_id, user_name, first_name, last_name)

    welcome_text = (
        "👋 *Добро пожаловать в бота для бронирования переговорной комнаты!* \n\n"
        "Выберите действие ниже:\n"
        "• *🚀 Начать бронирование* - Забронировать комнату\n"
        "• *📋 Расписание* - Посмотреть все бронирования\n"
        "• *📅 Мои бронирования* - Ваши брони\n"
        "• *🗑️ Отменить мои брони* - Отменить свои бронирования\n"
        "• *❓ Помощь* - Справочная информация"
    )
    show_main_menu(update, welcome_text)

# Команда /help
def help_command(update: Update, context: CallbackContext):
    help_text = f"""
    🤖 Бот для бронирования переговорной комнаты

    📚 Команды:
    /start - Главное меню
    /book - Начать бронирование
    /schedule - Просмотреть текущие бронирования
    /mybookings - Просмотреть мои бронирования
    /cancel - Отменить мои бронирования
    /help - Показать справку

    📋 Процесс бронирования:
    1. Нажмите "Начать бронирование"
    2. Выберите дату из списка
    3. Выберите время начала
    4. Выберите продолжительность встречи
    5. Подтвердите бронирование

    ⏰ Доступное время: {config.working_hours['start']} - {config.working_hours['end']}
    📅 Бронирование на: {config.booking_range_days} дней вперед
    🔔 Уведомления: за {config.notifications['reminder_minutes']} минут до начала
    """
    
    # Проверяем, является ли вызов callback query или обычным сообщением
    if hasattr(update, 'callback_query') and update.callback_query:
        # Вызов из callback query (нажатие кнопки)
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.callback_query.edit_message_text(help_text, reply_markup=reply_markup)
    elif hasattr(update, 'message') and update.message:
        # Вызов из обычного сообщения
        update.message.reply_text(help_text)
    else:
        # Если ни один из вариантов не подходит, логируем ошибку
        logger.error(f"Неизвестный тип вызова: {update}")

# Начало бронирования - выбор даты
def start_booking(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Очищаем предыдущее состояние
    USER_STATES[user_id] = {
        'state': BookingState.DATE, 
        'user_id': user_id, 
        'user_name': query.from_user.username or query.from_user.first_name
    }
    
    keyboard = []
    dates = get_available_dates()
    
    # Создаём матрицу дат 2x4
    row = []
    for i, date in enumerate(dates):
        row.append(InlineKeyboardButton(date, callback_data=f"date_{date}"))
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Добавляем кнопку "Назад"
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text("📅 *Выберите дату для бронирования:*", reply_markup=reply_markup, parse_mode='Markdown')

# Выбор времени начала
def show_time_picker(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in USER_STATES:
        return
    
    date = query.data.split("_", 1)[1]
    USER_STATES[user_id]['date'] = date
    USER_STATES[user_id]['state'] = BookingState.START_TIME
    
    # Создаём матрицу времени 4x4
    times = get_time_matrix()
    keyboard = []
    
    # Разбиваем на строки по 4 кнопки
    for i in range(0, len(times), 4):
        row_times = times[i:i+4]
        row = []
        for time in row_times:
            row.append(InlineKeyboardButton(time, callback_data=f"start_{time}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data="book_room")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(f"🕐 *Выберите время начала ({date}):*", reply_markup=reply_markup, parse_mode='Markdown')

# Показ выбора продолжительности
def show_duration_picker(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    if user_id not in USER_STATES:
        return
    
    start_time = query.data.split("_", 1)[1]
    USER_STATES[user_id]['start_time'] = start_time
    USER_STATES[user_id]['state'] = BookingState.DURATION
    
    # Создаём кнопки для всех интервалов из конфигурации
    keyboard = []
    formatted_intervals = config.get_time_intervals_formatted()
    
    # Разбиваем на строки по 2 кнопки
    for i in range(0, len(formatted_intervals), 2):
        row_intervals = formatted_intervals[i:i+2]
        row = []
        for minutes, text in row_intervals:
            row.append(InlineKeyboardButton(text, callback_data=f"duration_{minutes}"))
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("⬅️ Назад", callback_data=f"date_{USER_STATES[user_id]['date']}")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        f"⏱️ *Выберите продолжительность бронирования:*\n"
        f"📅 Дата: {USER_STATES[user_id]['date']}\n"
        f"🕐 Начало: {start_time}", 
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

# Обработка выбора продолжительности
def handle_duration_selection(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.username or query.from_user.first_name
    
    if user_id not in USER_STATES:
        return
    
    # Получаем продолжительность в минутах
    duration = int(query.data.split("_")[1])
    start_time = USER_STATES[user_id]['start_time']
    date = USER_STATES[user_id]['date']
    
    # Рассчитываем время окончания
    start_dt = datetime.strptime(start_time, "%H:%M")
    end_dt = start_dt + timedelta(minutes=duration)
    end_time = end_dt.strftime("%H:%M")
    
    # Проверяем, не выходит ли время окончания за пределы рабочего дня
    end_limit = datetime.strptime(config.working_hours['end'], "%H:%M")
    if end_dt > end_limit:
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data=f"start_{start_time}")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            f"❌ Время окончания выходит за пределы рабочего дня (до {config.working_hours['end']})!\n"
            "Пожалуйста, выберите меньшую продолжительность.", 
            reply_markup=reply_markup
        )
        return
    
    USER_STATES[user_id]['end_time'] = end_time
    
    # Проверяем на конфликты и получаем информацию о конфликте
    db_manager = get_db_manager()
    if db_manager.is_conflict(date, start_time, end_time):
        conflicting_booking = db_manager.get_conflicting_booking(date, start_time, end_time)
        if conflicting_booking:
            conflicting_user, conflicting_start, conflicting_end = conflicting_booking
            conflict_message = (
                f"❌ В это время комната уже занята!\n\n"
                f"📅 Дата: {date}\n"
                f"🕐 Конфликтное время: {conflicting_start} - {conflicting_end}\n"
                f"👤 Забронировал: @{conflicting_user}\n\n"
                "Пожалуйста, выберите другое время."
            )
        else:
            conflict_message = "❌ В это время комната уже занята!\nПожалуйста, выберите другое время."
        
        keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="book_room")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(conflict_message, reply_markup=reply_markup)
        del USER_STATES[user_id]
        return
    
    # Сохраняем бронирование
    db_manager.save_booking(user_id, user_name, date, start_time, end_time)
    
    # Форматируем продолжительность для отображения
    hours = duration // 60
    minutes = duration % 60
    duration_text = ""
    if hours > 0:
        duration_text += f"{hours} ч "
    if minutes > 0:
        duration_text += f"{minutes} мин"
    
    success_message = (
        f"✅ Переговорная успешно забронирована!\n\n"
        f"📅 Дата: {date}\n"
        f"🕐 Время: {start_time} - {end_time}\n"
        f"⏱️ Продолжительность: {duration_text}\n"
        f"👤 Забронировал: @{user_name}"
    )
    
    keyboard = [[InlineKeyboardButton("🏠 В главное меню", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(success_message, reply_markup=reply_markup)
    del USER_STATES[user_id]

# Просмотр расписания
def show_schedule(update: Update, context: CallbackContext):
    query = update.callback_query
    db_manager = get_db_manager()
    bookings = db_manager.get_all_bookings()
    
    if not bookings:
        message = "📅 *Нет активных бронирований*"
    else:
        message = "*📅 Текущие бронирования:*\n\n"
        current_date = ""
        
        for date, start_time, end_time, user_name in bookings:
            if date != current_date:
                current_date = date
                message += f"📆 *{date}:*\n"
            message += f"  🕐 {start_time}-{end_time} (@{user_name})\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

# Просмотр моих бронирований
def show_my_bookings(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    user_name = query.from_user.username or query.from_user.first_name
    
    db_manager = get_db_manager()
    bookings = db_manager.get_user_bookings(user_id)
    
    if not bookings:
        message = "📅 *У вас нет активных бронирований*"
    else:
        message = f"*📅 Ваши бронирования (@{user_name}):*\n\n"
        current_date = ""
        
        for date, start_time, end_time in bookings:
            if date != current_date:
                current_date = date
                message += f"📆 *{date}:*\n"
            message += f"  🕐 {start_time}-{end_time}\n"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

# Отмена моих бронирований
def cancel_my_bookings(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    db_manager = get_db_manager();
    result = db_manager.cancel_user_bookings(user_id)
    if result:
        message = "✅ *Ваши бронирования успешно отменены*"
    else:
        message = "❌ *У вас нет активных бронирований для отмены*"
    
    keyboard = [[InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(message, reply_markup=reply_markup, parse_mode='Markdown')

# Команды для быстрого доступа
def book_command(update: Update, context: CallbackContext):
    """Команда /book - быстрый старт бронирования"""
    class FakeCallbackQuery:
        def __init__(self, update):
            self.from_user = update.effective_user
            self.message = update.message
            
        def edit_message_text(self, *args, **kwargs):
            self.message.reply_text(*args, **kwargs)
    
    fake_query = FakeCallbackQuery(update)
    fake_update = type('obj', (object,), {'callback_query': fake_query, 'effective_user': update.effective_user})
    
    start_booking(fake_update, context)

def schedule_command(update: Update, context: CallbackContext):
    """Команда /schedule - быстрый просмотр расписания"""
    db_manager = get_db_manager()
    bookings = db_manager.get_all_bookings()
    
    if not bookings:
        update.message.reply_text("📅 *Нет активных бронирований*", parse_mode='Markdown')
        return
    
    message = "*📅 Текущие бронирования:*\n\n"
    current_date = ""
    
    for date, start_time, end_time, user_name in bookings:
        if date != current_date:
            current_date = date
            message += f"📆 *{date}:*\n"
        message += f"  🕐 {start_time}-{end_time} (@{user_name})\n"
    
    update.message.reply_text(message, parse_mode='Markdown')

def my_bookings_command(update: Update, context: CallbackContext):
    """Команда /mybookings - просмотр моих бронирований"""
    user_id = update.effective_user.id
    user_name = update.effective_user.username or update.effective_user.first_name
    
    db_manager = get_db_manager()
    bookings = db_manager.get_user_bookings(user_id)
    
    if not bookings:
        update.message.reply_text("📅 *У вас нет активных бронирований*", parse_mode='Markdown')
        return
    
    message = f"*📅 Ваши бронирования (@{user_name}):*\n\n"
    current_date = ""
    
    for date, start_time, end_time in bookings:
        if date != current_date:
            current_date = date
            message += f"📆 *{date}:*\n"
        message += f"  🕐 {start_time}-{end_time}\n"
    
    update.message.reply_text(message, parse_mode='Markdown')

# Функция отображения конкретного рейтинга
def show_specific_rating(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    # Определяем тип рейтинга
    rating_type = query.data.replace("rating_", "")
    
    current_date = datetime.now()
    year = current_date.year
    month = current_date.month
    
    if rating_type == "month":
        period_text = f"за {current_date.strftime('%B %Y')}"
        year_filter = year
        month_filter = month
    elif rating_type == "year":
        period_text = f"за {year} год"
        year_filter = year
        month_filter = None
    else:  # all_time
        period_text = "за всё время"
        year_filter = None
        month_filter = None
    
    # Получаем топы
    db_manager = get_db_manager()
    
    top_bookings = db_manager.get_top_users_by_bookings(year_filter, month_filter, 3)
    top_duration = db_manager.get_top_users_by_duration(year_filter, month_filter, 3)
    
    # Формируем сообщение БЕЗ форматирования
    message = f"📊 Рейтинг пользователей {period_text}:\n\n"
    
    # Топ по количеству бронирований
    message += "📈 По количеству бронирований:\n"
    if top_bookings:
        for i, (user_id, username, count) in enumerate(top_bookings, 1):
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            username = username or f"user_{user_id}"  # Если username None
            message += f"  {medal} @{username} - {count} брон.\n"
    else:
        message += "  Нет данных\n"
    
    message += "\n"
    
    # Топ по длительности (в часах)
    message += "⏱️ По длительности бронирования:\n"
    if top_duration:
        for i, (user_id, username, minutes) in enumerate(top_duration, 1):
            hours = minutes // 60
            mins = minutes % 60
            duration_text = f"{hours}ч {mins}мин" if hours > 0 else f"{mins}мин"
            medal = ["🥇", "🥈", "🥉"][i-1] if i <= 3 else f"{i}."
            username = username or f"user_{user_id}"  # Если username None
            message += f"  {medal} @{username} - {duration_text}\n"
    else:
        message += "  Нет данных\n"
    
    keyboard = [
        [InlineKeyboardButton("📊 Другой период", callback_data="show_rating")],
        [InlineKeyboardButton("⬅️ Назад", callback_data="main_menu")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    query.edit_message_text(message, reply_markup=reply_markup)  # Без parse_mode

def cancel_command(update: Update, context: CallbackContext):
    """Команда /cancel - отмена моих бронирований"""
    user_id = update.effective_user.id
    db_manager = get_db_manager()
    result = db_manager.cancel_user_bookings(user_id)
    if result:
        update.message.reply_text("✅ *Ваши бронирования успешно отменены*", parse_mode='Markdown')
    else:
        update.message.reply_text("❌ *У вас нет активных бронирований для отмены*", parse_mode='Markdown')

# Обработчик нажатий на кнопки
def button_handler(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    
    query.answer()
    
    # Главное меню
    if query.data == "main_menu":
        start(update, context)
        return
    
    # Начало бронирования
    elif query.data == "book_room":
        start_booking(update, context)
        return
    
    # Просмотр расписания
    elif query.data == "show_schedule":
        show_schedule(update, context)
        return
    
    # Мои бронирования
    elif query.data == "my_bookings":
        show_my_bookings(update, context)
        return
    
    # Отмена моих бронирований
    elif query.data == "cancel_my_bookings":
        cancel_my_bookings(update, context)
        return
    
    # Помощь
    elif query.data == "help":
        help_command(update, context)
        return
    
    # Выбор даты
    elif query.data.startswith("date_"):
        show_time_picker(update, context)
        return
    
    # Выбор времени начала
    elif query.data.startswith("start_"):
        show_duration_picker(update, context)
        return
    
    # Выбор продолжительности
    elif query.data.startswith("duration_"):
        handle_duration_selection(update, context)
        return
    
    # Отключенные кнопки
    elif query.data.startswith("disabled_"):
        query.answer("❌ Это время недоступно", show_alert=True)
        return
      # Рейтинг
    elif query.data == "show_rating":
        show_specific_rating(update, context)
        return
    
    elif query.data.startswith("rating_"):
        show_specific_rating(update, context)
        return

def main():
    # Инициализируем базу данных
    init_db_manager(config.database_file)
    
    # Проверяем токен
    if config.token == "YOUR_BOT_TOKEN_HERE":
        print("Пожалуйста, укажите токен бота в файле settings.json")
        return
    
    updater = Updater(config.token, use_context=True)
    dp = updater.dispatcher
    
    # Обработчики команд
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("help", help_command))
    dp.add_handler(CommandHandler("book", book_command))
    dp.add_handler(CommandHandler("schedule", schedule_command))
    dp.add_handler(CommandHandler("mybookings", my_bookings_command))
    dp.add_handler(CommandHandler("cancel", cancel_command))
    
    # Обработчик кнопок
    dp.add_handler(CallbackQueryHandler(button_handler))
    
    print(f"Бот запущен...")
    print(f"Рабочее время: {config.working_hours['start']} - {config.working_hours['end']}")
    print(f"Диапазон бронирования: {config.booking_range_days} дней")
    print(f"Уведомления: {'включены' if config.notifications['enable'] else 'выключены'}")
    
    # Запускаем поток уведомлений
    start_notification_thread(updater.bot)
    
    try:
        updater.start_polling()
        updater.idle()
    except KeyboardInterrupt:
        print("Остановка бота...")
        stop_notification_thread_func()
        updater.stop()

if __name__ == '__main__':
    main()