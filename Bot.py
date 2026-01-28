"""
ASTEROID ALERT SYSTEM - Telegram Bot
Стартер-код
"""

# ===== FILE: telegram_bot.py =====

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import os
from dotenv import load_dotenv
import requests
from datetime import datetime
import logging

load_dotenv()

# Логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Константы
BACKEND_URL = os.getenv('BACKEND_URL', 'http://localhost:5000')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Кнопки для меню
def get_main_keyboard():
    """Главное меню бота"""
    keyboard = [
        [InlineKeyboardButton("📍 Астероиды сегодня", callback_data='asteroids_today')],
        [InlineKeyboardButton("⚠️ Опасные астероиды", callback_data='dangerous')],
        [InlineKeyboardButton("📅 На неделю", callback_data='asteroids_week')],
        [InlineKeyboardButton("🔔 Уведомления", callback_data='notifications')],
        [InlineKeyboardButton("💰 Премиум подписка", callback_data='subscribe')],
        [InlineKeyboardButton("❓ Справка", callback_data='help')],
    ]
    return InlineKeyboardMarkup(keyboard)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Команда /start - приветствие"""
    user = update.effective_user
    chat_id = update.effective_chat.id
    
    # Регистрируем пользователя в базе
    try:
        response = requests.post(f'{BACKEND_URL}/api/user/register', json={
            'telegram_id': str(chat_id),
            'username': user.first_name
        })
        logger.info(f'User {chat_id} registered')
    except Exception as e:
        logger.error(f'Error registering user: {e}')
    
    text = f"""
🚀 Добро пожаловать в Asteroid Alert System!

Я помогу тебе следить за астероидами, приближающимися к Земле.

📊 Что я умею:
• Показывать астероиды на сегодня и неделю
• Уведомлять об опасных сближениях
• Предоставлять детальную информацию об астероидах
• Сохранять твои избранные объекты

🎯 Выбери действие:
"""
    
    await update.message.reply_text(text, reply_markup=get_main_keyboard())

async def asteroids_today(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получить астероиды на сегодня"""
    query = update.callback_query
    await query.answer()
    
    try:
        response = requests.get(f'{BACKEND_URL}/api/asteroids/today')
        asteroids = response.json()
        
        if not asteroids:
            await query.edit_message_text(
                "На сегодня нет астероидов в нашей базе.\n\nВыбери другой период.",
                reply_markup=get_main_keyboard()
            )
            return
        
        text = "🌍 Астероиды на сегодня:\n\n"
        for ast in asteroids[:10]:  # Максимум 10 астероидов
            text += f"📌 {ast['name']}\n"
            text += f"  Размер: {ast['diameter_km']:.2f} км\n"
            text += f"  Расстояние: {ast['distance_au']:.4f} AU\n"
            text += f"  Скорость: {ast['velocity_km_s']:.2f} км/с\n"
            if ast['is_potentially_hazardous']:
                text += f"  ⚠️ Потенциально опасен\n"
            text += "\n"
        
        await query.edit_message_text(text, reply_markup=get_main_keyboard())
    
    except Exception as e:
        logger.error(f'Error fetching asteroids: {e}')
        await query.edit_message_text(
            "❌ Ошибка при загрузке данных. Попробуй позже.",
            reply_markup=get_main_keyboard()
        )

async def asteroids_dangerous(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получить опасные астероиды"""
    query = update.callback_query
    await query.answer()
    
    try:
        response = requests.get(f'{BACKEND_URL}/api/asteroids/dangerous')
        asteroids = response.json()
        
        if not asteroids:
            await query.edit_message_text(
                "✅ Хорошие новости! На ближайшую неделю опасных астероидов не обнаружено.",
                reply_markup=get_main_keyboard()
            )
            return
        
        text = "⚠️ Опасные астероиды (ближайшие встречи):\n\n"
        for ast in asteroids[:5]:  # Максимум 5 астероидов
            text += f"🔴 {ast['name']}\n"
            text += f"  Размер: {ast['diameter_km']:.2f} км\n"
            text += f"  Расстояние: {ast['distance_au']:.4f} AU\n"
            text += f"  Дата сближения: {ast['closest_approach_date'][:10]}\n\n"
        
        await query.edit_message_text(text, reply_markup=get_main_keyboard())
    
    except Exception as e:
        logger.error(f'Error fetching dangerous asteroids: {e}')
        await query.edit_message_text(
            "❌ Ошибка при загрузке данных.",
            reply_markup=get_main_keyboard()
        )

async def asteroids_week(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Получить астероиды на неделю"""
    query = update.callback_query
    await query.answer()
    
    try:
        response = requests.get(f'{BACKEND_URL}/api/asteroids/week')
        asteroids = response.json()
        
        if not asteroids:
            await query.edit_message_text(
                "На неделю нет предстоящих встреч астероидов.",
                reply_markup=get_main_keyboard()
            )
            return
        
        text = "📅 Астероиды на неделю:\n\n"
        for ast in asteroids[:15]:  # Максимум 15 астероидов
            text += f"📌 {ast['name']}\n"
            text += f"  Дата: {ast['closest_approach_date'][:10]}\n"
            text += f"  Расстояние: {ast['distance_au']:.4f} AU\n"
            if ast['is_potentially_hazardous']:
                text += f"  ⚠️ Потенциально опасен\n"
            text += "\n"
        
        await query.edit_message_text(text, reply_markup=get_main_keyboard())
    
    except Exception as e:
        logger.error(f'Error fetching weekly asteroids: {e}')
        await query.edit_message_text(
            "❌ Ошибка при загрузке данных.",
            reply_markup=get_main_keyboard()
        )

async def subscribe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Меню подписки"""
    query = update.callback_query
    await query.answer()
    
    chat_id = update.effective_chat.id
    
    # Получаем информацию о текущей подписке
    try:
        response = requests.get(f'{BACKEND_URL}/api/user/{chat_id}/subscription')
        user_data = response.json()
        current_tier = user_data.get('subscription_tier', 'free')
    except:
        current_tier = 'free'
    
    text = f"""
💰 Планы подписки Asteroid Alert System

🟢 Free (текущий план)
  ✓ Уведомления об опасных астероидах
  ✓ Базовая информация
  ✓ Бесплатно

🔵 Pro - $4.99/месяц
  ✓ Все из Free
  ✓ Уведомления про ВСЕ астероиды
  ✓ Неограниченная фильтрация
  ✓ История наблюдений
  ✓ API доступ

🟣 Expert - $19.99/месяц
  ✓ Все из Pro
  ✓ Неограниченный API
  ✓ Приоритетная поддержка
  ✓ Исторические данные

⚫ Enterprise - договор
  ✓ Все из Expert
  ✓ Custom интеграции
  ✓ 24/7 поддержка

Для подписки перейди на наш сайт:
https://asteroid-alert.example.com
"""
    
    await query.edit_message_text(text, reply_markup=get_main_keyboard())

async def notifications(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Управление уведомлениями"""
    query = update.callback_query
    await query.answer()
    
    text = """
🔔 Настройка уведомлений

Текущее время отправки: 09:00

Напиши время в формате HH:MM (например, 15:30) для изменения времени уведомлений.

Или выбери действие:
"""
    
    keyboard = [
        [InlineKeyboardButton("✅ Включить уведомления", callback_data='notify_on')],
        [InlineKeyboardButton("❌ Отключить уведомления", callback_data='notify_off')],
        [InlineKeyboardButton("⬅️ Назад", callback_data='back')],
    ]
    
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Справка"""
    query = update.callback_query
    await query.answer()
    
    text = """
❓ Справка по Asteroid Alert System

📚 Основные команды:
/start - Главное меню
/help - Эта справка

🔍 Как пользоваться:
1. Нажми кнопку "Астероиды сегодня" или "На неделю"
2. Посмотри список приближающихся астероидов
3. Для подробной информации перейди на сайт

⚠️ Что такое потенциально опасный астероид?
Это объект размером > 140 м, проходящий на расстоянии < 7.5 млн км от Земли.

💾 Данные берутся из:
NASA Planetary Defense Coordination Office

🆘 Нужна помощь?
Напиши на support@asteroid-alert.example.com

"""
    
    await query.edit_message_text(text, reply_markup=get_main_keyboard())

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Обработка нажатия кнопок"""
    query = update.callback_query
    await query.answer()
    
    if query.data == 'asteroids_today':
        await asteroids_today(update, context)
    elif query.data == 'asteroids_week':
        await asteroids_week(update, context)
    elif query.data == 'dangerous':
        await asteroids_dangerous(update, context)
    elif query.data == 'subscribe':
        await subscribe(update, context)
    elif query.data == 'notifications':
        await notifications(update, context)
    elif query.data == 'help':
        await help_command(update, context)
    elif query.data == 'back':
        await query.edit_message_text(
            "🚀 Главное меню",
            reply_markup=get_main_keyboard()
        )

def main():
    """Запуск бота"""
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError('TELEGRAM_BOT_TOKEN not set')
    
    # Создаём приложение
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # Добавляем обработчики
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    
    # Запускаем бота
    print('Bot is running...')
    app.run_polling()

if __name__ == '__main__':
    main()
