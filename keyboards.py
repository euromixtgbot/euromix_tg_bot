import logging
logger = logging.getLogger(__name__)

from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove


def request_contact_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Надіслати номер телефону", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )



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

# Системні ключі → Текст кнопок
BUTTONS = {
    "my_tickets":    "🧾 Мої заявки",
    "my_tasks":      "🧾 Мої задачі",
    "create_ticket": "🆕 Створити заявку",
    "check_status":  "✅ Перевірити статус задачі",
    "add_comment":   "📝 Додати коментар до задачі",
    "exit_comment":  "❌ Вийти з режиму коментаря",
    "help":          "ℹ️ Допомога",
    "confirm_create":"Створити задачу",
    "back":          "Назад"
}

def make_keyboard(step: int, description: str = ""):
    """
    Генерує ReplyKeyboardMarkup для поточного кроку діалогу створення заявки.
    """
    name = STEPS[step]
    if name == "confirm":
        buttons = [[KeyboardButton(BUTTONS["confirm_create"])]]
    else:
        buttons = [[KeyboardButton(opt)] for opt in OPTIONS.get(name, [])]
    buttons.append([KeyboardButton(BUTTONS["back"])])
    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    prompts = {
        "division":     "Оберіть ваш Підрозділ:",
        "department":   "Оберіть Департамент:",
        "service":      "Оберіть Сервіс:",
        "full_name":    "Введіть ваше Прізвище та Ім'я:",
        "description":  "Опишіть вашу проблему:",
        "confirm":      f"Натисніть '{BUTTONS['confirm_create']}', якщо все заповнено.\n\nОпис задачі:\n{description}"
    }
    return prompts[name], markup

def remove_keyboard():
    """
    Повертає об’єкт для приховання ReplyKeyboardMarkup.
    """
    return ReplyKeyboardRemove()

# Головне меню після /start
main_menu_markup = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BUTTONS["my_tickets"])],
        [KeyboardButton(BUTTONS["create_ticket"])],
        [KeyboardButton(BUTTONS["help"])]
    ],
    resize_keyboard=True
)

# Меню після створення нової задачі
after_create_menu_markup = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BUTTONS["my_tasks"])],
        [KeyboardButton(BUTTONS["check_status"])],
        [KeyboardButton(BUTTONS["help"])]
    ],
    resize_keyboard=True
)

# Меню дій у розділі "Мої заявки"
mytickets_action_markup = ReplyKeyboardMarkup(
    [
        [KeyboardButton(BUTTONS["add_comment"])],
        [KeyboardButton(BUTTONS["create_ticket"])],
        [KeyboardButton(BUTTONS["help"])]
    ],
    resize_keyboard=True
)

# Клавіатура для режиму коментаря
comment_mode_markup = ReplyKeyboardMarkup(
    [[KeyboardButton(BUTTONS["exit_comment"])]],
    resize_keyboard=True,
    one_time_keyboard=True
)
