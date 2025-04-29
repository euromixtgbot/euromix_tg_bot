from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

# Основні етапи створення заявки
STEPS = ["division", "department", "service", "full_name", "description", "confirm"]

# Варіанти для кожного етапу
OPTIONS = {
    "division": [
        "Офіс", "Дніпро", "PSC", "Київ", "Біла Церква", "Суми", "Вінниця",
        "Запоріжжя", "Краматорськ", "Кривий Ріг", "Кропивницький", "Львів",
        "Одеса", "Полтава", "Харків", "Черкаси", "Чернігів", "Імпорт"
    ],
    "department": [
        "Комерційний департамент", "Операційний департамент", "ІТ департамент",
    ],
    "service": [
        "E-mix 2.x", "E-mix 3.x", "E-supervisor", "E-mix market-android",
        "E-mix market iOS", "E-drive", "E-inventory", "Пошта",
        "Мобільний зв'язок", "Ремонт техніки", "Портал техпідтримки"
    ]
}

def make_keyboard(step: int, description: str = ""):
    name = STEPS[step]
    if name == "confirm":
        buttons = [[KeyboardButton("Створити задачу")]]
    else:
        buttons = [[KeyboardButton(opt)] for opt in OPTIONS.get(name, [])]
    buttons.append([KeyboardButton("Назад")])
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    texts = {
        "division": "Оберіть ваш Підрозділ:",
        "department": "Оберіть Департамент:",
        "service": "Оберіть Сервіс:",
        "full_name": "Введіть ваше Прізвище та Ім'я:",
        "description": "Опишіть вашу проблему:",
        "confirm": f"Натисніть 'Створити задачу', якщо все заповнено.\n\nОпис задачі:\n{description}"
    }
    return texts[name], markup

def remove_keyboard():
    return ReplyKeyboardRemove()

# Головне меню після /start
main_menu_markup = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🧾 Мої заявки")],
        [KeyboardButton("🆕 Створити заявку")],
        [KeyboardButton("ℹ️ Допомога")]
    ],
    resize_keyboard=True
)

# Меню після створення задачі
after_create_menu_markup = ReplyKeyboardMarkup(
    [
        [KeyboardButton("🧾 Мої задачі")],
        [KeyboardButton("✅ Перевірити статус задачі")],
        [KeyboardButton("ℹ️ Допомога")]
    ],
    resize_keyboard=True
)

# Меню під час перегляду задач (наприклад, після /mytickets)
mytickets_action_markup = ReplyKeyboardMarkup(
    [
        [KeyboardButton("📝 Додати коментар до задачі")],
        [KeyboardButton("🆕 Створити заявку")],
        [KeyboardButton("ℹ️ Допомога")]
    ],
    resize_keyboard=True
)
