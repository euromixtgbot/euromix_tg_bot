# keyboards.py
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

STEPS = ["division", "department", "service", "full_name", "description", "confirm"]
OPTIONS = {
    "division": ["Офіс", "Дніпро", "PSC", "Київ", "Біла Церква", "Суми", "Вінниця", "Запоріжжя", "Краматорськ", "Кривий Ріг", "Кропивницький", "Львів", "Одеса", "Полтава", "Харків", "Черкаси", "Чернігів", "Імпорт"],
    "department": ["Комерційний департамент", "Операційний департамент", "Департамент маркетинга", "ІТ департамент", "Юр. департамент", "Департамент безпеки", "Департамент персоналу", "Фінансовий департамент", "Бухгалтерія", "Контрольно ревізійний відділ", "Відділ кадрів"],
    "service": ["E-mix 2.x", "E-mix 3.x", "E-supervisor", "E-mix market-android", "E-mix market iOS", "E-drive", "E-inventory", "Пошта", "Мобільний зв'язок", "Ремонт техніки", "Портал техпідтримки"],
}

def make_keyboard(step: int, description: str = ""):
    name = STEPS[step]
    buttons = [[KeyboardButton(opt)] for opt in OPTIONS.get(name, [])]
    if name == "confirm":
        buttons = [[KeyboardButton("Створити задачу")]]
    buttons.append([KeyboardButton("Назад")])
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    texts = {
        "division": "Оберіть ваш Підрозділ:",
        "department": "Оберіть Департамент:",
        "service": "Оберіть Сервіс:",
        "full_name": "Введіть ваше Прізвище та Ім'я:",
        "description": "Опишіть вашу проблему:",
        "confirm": f"Натисніть 'Створити задачу', якщо все заповнено.\n\nОпис задачі:\n{description}",
    }
    return texts[name], markup

def remove_keyboard():
    return ReplyKeyboardRemove()