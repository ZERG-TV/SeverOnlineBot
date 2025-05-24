import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, CallbackContext, ConversationHandler
from datetime import datetime
import pytz

# Включаем логирование
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Список администраторов (замените на реальные ID администраторов)
admins = [7555356452]  # ID администраторов

# Хранение сообщений, ожидающих одобрения
pending_messages = {}
moderation_messages = {}  # Словарь для хранения ID сообщений о модерации

# Функция для проверки, находится ли текущее время в периоде, когда бот не работает
def is_bot_active() -> bool:
    now = datetime.now(pytz.timezone('Europe/Moscow'))
    day_of_week = now.weekday()  # 0 - понедельник, 1 - вторник, ..., 6 - воскресенье
    current_time = now.time()

    # Проверяем, если сегодня вторник (1), четверг (3) или суббота (5)
    if day_of_week in [1, 3, 5]:
        # Проверяем, если текущее время между 21:45 и 23:55
        if current_time >= datetime.strptime("21:45", "%H:%M").time() and current_time <= datetime.strptime("23:55", "%H:%M").time():
            return False  # Бот не работает
    return True  # Бот работает

# Функция для получения chat_id
async def get_chat_id(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    await context.bot.send_message(chat_id=chat_id, text=f"Chat ID этой группы: {chat_id}")

# Функция для получения user_id
async def get_user_id(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    await context.bot.send_message(chat_id=update.message.chat_id, text=f"Ваш User ID: {user_id}")

# Функция для обработки сообщений
async def message_handler(update: Update, context: CallbackContext) -> None:
    # Проверяем, работает ли бот
    if not is_bot_active():
        return

    # Проверяем, является ли пользователь администратором
    if update.message.from_user.id in admins:
        await context.bot.send_message(chat_id=update.message.chat_id, text=update.message.text)
        return

    message_id = update.message.message_id
    pending_messages[message_id] = update.message.text
    
    moderation_message = await context.bot.send_message(
        chat_id=update.message.chat_id,
        text=f"Сообщение от {update.message.from_user.username} отправлено на модерацию: {update.message.text}"
    )
    
    moderation_messages[message_id] = moderation_message.message_id

    for admin_id in admins:
        await context.bot.send_message(
            chat_id=admin_id,
            text=f"Сообщение от {update.message.from_user.username}: {update.message.text}\n\nРазрешить публикацию? (Ответьте 'Да', 'Нет' или 'Забанить')"
        )
    context.user_data['pending_message_id'] = message_id

# Функция для обработки ответов администраторов
async def approval_handler(update: Update, context: CallbackContext) -> int:
    user_id = update.message.from_user.id
    message_id = context.user_data.get('pending_message_id')

    if message_id is None:
        await update.message.reply_text("Нет ожидающих сообщений для одобрения.")
        return ConversationHandler.END

    moderation_message_id = moderation_messages.get(message_id)

    if update.message.text.lower() == 'да':
        # Разрешаем публикацию
        await context.bot.send_message(chat_id=update.message.chat_id, text=f"Сообщение разрешено: {pending_messages[message_id]}")
        logger.info(f"Сообщение от {update.message.from_user.username} разрешено.")
    elif update.message.text.lower() == 'нет':
        # Запрещаем публикацию
        await context.bot.send_message(chat_id=update.message.chat_id, text="Сообщение запрещено.")
        logger.info(f"Сообщение от {update.message.from_user.username} запрещено.")
    elif update.message.text.lower() == 'забанить':
        # Блокируем пользователя
        user_to_ban = update.message.from_user.id
        await context.bot.kick_chat_member(chat_id=update.message.chat_id, user_id=user_to_ban)
        await context.bot.send_message(chat_id=update.message.chat_id, text=f"Пользователь {update.message.from_user.username} был забанен.")
        logger.info(f"Пользователь {update.message.from_user.username} был забанен.")
    else:
        await update.message.reply_text("Пожалуйста, ответьте 'Да', 'Нет' или 'Забанить'.")

    # Удаляем сообщение о модерации
    if moderation_message_id:
        await context.bot.delete_message(chat_id=update.message.chat_id, message_id=moderation_message_id)

    # Удаляем сообщение из списка ожидающих
    pending_messages.pop(message_id, None)
    moderation_messages.pop(message_id, None)

    return ConversationHandler.END

def main() -> None:
    # Создаем Updater и передаем ему токен вашего бота
    application = ApplicationBuilder().token("7980643670:AAF80ckmM02GAnBbYQgEd2Ec2YbHelyBPAM").build()  # Замените на ваш токен

    # Обработчик для получения chat_id
    application.add_handler(CommandHandler("get_chat_id", get_chat_id))

    # Обработчик для получения user_id
    application.add_handler(CommandHandler("get_user_id", get_user_id))

    # Обработчик сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))

    # Обработчик ответов администраторов
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.TEXT & ~filters.COMMAND, approval_handler)],
        states={},
        fallbacks=[]
    )
    application.add_handler(conv_handler)

    # Запускаем бота
    application.run_polling()

if __name__ == '__main__':
    main()
