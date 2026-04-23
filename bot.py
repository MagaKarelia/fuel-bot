import telebot
import pg8000.native
from datetime import datetime

TOKEN = '8525218485:AAFpOKcdduTKqmOLYIIpnB5cHx01CoeyhyI'
ADMIN_ID = 392561820

def get_conn():
    return pg8000.native.Connection(
        user="postgres",
        password="EgorMazov10.",
        host="db.dvseujzprpmhzgpgkbag.supabase.co",
        database="postgres",
        port=5432,
        ssl_context=True
    )

def init_db():
    conn = get_conn()
    conn.run('''CREATE TABLE IF NOT EXISTS fuel_records
                 (id SERIAL PRIMARY KEY,
                  car_number TEXT,
                  amount REAL,
                  date TEXT)''')
    conn.close()

bot = telebot.TeleBot(TOKEN)

@bot.message_handler(commands=['start'])
def start(message):
    bot.send_message(message.chat.id, "Добро пожаловать! Выберите действие:",
                     reply_markup=get_main_keyboard(message.from_user.id))

def get_main_keyboard(user_id):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    btn1 = telebot.types.KeyboardButton("Добавить заправку")
    btn2 = telebot.types.KeyboardButton("Отчёт за месяц")
    if user_id == ADMIN_ID:
        btn3 = telebot.types.KeyboardButton("Управление записями")
        keyboard.add(btn1, btn2, btn3)
    else:
        keyboard.add(btn1, btn2)
    return keyboard

@bot.message_handler(func=lambda message: message.text == "Добавить заправку")
def add_fuel_start(message):
    cars = ["M656PH", "M222XB", "H843KK", "K270KA", "K191XO"]
    keyboard = telebot.types.InlineKeyboardMarkup()
    for car in cars:
        keyboard.add(telebot.types.InlineKeyboardButton(text=car, callback_data=f"car_{car}"))
    bot.send_message(message.chat.id, "Выберите номер автомобиля:", reply_markup=keyboard)

@bot.callback_query_handler(func=lambda call: call.data.startswith('car_'))
def select_car(call):
    car_number = call.data.replace('car_', '')
    bot.edit_message_text(chat_id=call.message.chat.id,
                          message_id=call.message.message_id,
                          text=f"Выбран автомобиль: {car_number}. Введите сумму заправки (руб.):")
    bot.register_next_step_handler(call.message, lambda msg: save_fuel(msg, car_number))

def save_fuel(message, car_number):
    try:
        amount = float(message.text)
        conn = get_conn()
        conn.run("INSERT INTO fuel_records (car_number, amount, date) VALUES (:car, :amount, :date)",
                 car=car_number, amount=amount, date=datetime.now().isoformat())
        conn.close()
        bot.send_message(message.chat.id, f"Заправка на {amount} руб. для {car_number} сохранена!",
                         reply_markup=get_main_keyboard(message.from_user.id))
    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите корректную сумму!")

@bot.message_handler(func=lambda message: message.text == "Отчёт за месяц")
def monthly_report(message):
    conn = get_conn()
    current_month = datetime.now().strftime('%Y-%m')
    results = conn.run("""
        SELECT car_number, SUM(amount) as total
        FROM fuel_records
        WHERE date LIKE :month
        GROUP BY car_number
    """, month=f"{current_month}%")
    conn.close()
    if results:
        report = "Отчёт за текущий месяц:\n"
        for row in results:
            report += f"{row[0]}: {row[1]} руб.\n"
    else:
        report = "За текущий месяц данных нет."
    bot.send_message(message.chat.id, report, reply_markup=get_main_keyboard(message.from_user.id))

@bot.message_handler(func=lambda message: message.text == "Управление записями" and message.from_user.id == ADMIN_ID)
def manage_records(message):
    bot.send_message(message.chat.id, "Управление записями:", reply_markup=get_management_keyboard())

def get_management_keyboard():
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(telebot.types.KeyboardButton("Показать все записи"))
    keyboard.add(telebot.types.KeyboardButton("Удалить запись"))
    keyboard.add(telebot.types.KeyboardButton("Редактировать запись"))
    keyboard.add(telebot.types.KeyboardButton("Назад"))
    return keyboard

@bot.message_handler(func=lambda message: message.text == "Показать все записи" and message.from_user.id == ADMIN_ID)
def show_all_records(message):
    conn = get_conn()
    records = conn.run("SELECT id, car_number, amount, date FROM fuel_records ORDER BY date DESC")
    conn.close()
    if records:
        response = "Все записи:\n"
        for record in records:
            response += f"ID: {record[0]}, Авто: {record[1]}, Сумма: {record[2]} руб., Дата: {record[3]}\n"
    else:
        response = "Записей нет."
    bot.send_message(message.chat.id, response, reply_markup=get_management_keyboard())

@bot.message_handler(func=lambda message: message.text == "Удалить запись" and message.from_user.id == ADMIN_ID)
def delete_record_start(message):
    bot.send_message(message.chat.id, "Введите ID записи для удаления:")
    bot.register_next_step_handler(message, delete_record)

def delete_record(message):
    try:
        record_id = int(message.text)
        conn = get_conn()
        conn.run("DELETE FROM fuel_records WHERE id = :id", id=record_id)
        conn.close()
        bot.send_message(message.chat.id, f"Запись {record_id} удалена!", reply_markup=get_management_keyboard())
    except ValueError:
        bot.send_message(message.chat.id, "Ошибка: введите число!", reply_markup=get_management_keyboard())

@bot.message_handler(func=lambda message: message.text == "Назад")
def go_back(message):
    bot.send_message(message.chat.id, "Главное меню:", reply_markup=get_main_keyboard(message.from_user.id))

init_db()
print("Бот запущен...")
bot.polling(none_stop=True)
