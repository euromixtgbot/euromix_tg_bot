import logging
from telegram import ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

logger = logging.getLogger(__name__)

def request_contact_keyboard():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("📞 Надіслати номер телефону", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )

# Основні кроки створення заявки
# Замінено порядок: full_name іде перед service, щоб при авторизованому user
# ми могли відразу стрибати на service (STEPS.index("service") == 3)
STEPS = [
    "division",      # 0
    "department",    # 1
    "full_name",     # 2
    "service",       # 3
    "description",   # 4
    "confirm_create"        # 5
]

# Варіанти для відповідних кроків
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

# Кнопки системних дій
BUTTONS = {
    "my_tickets":     "🧾 Мої заявки",
    "create_ticket":  "🆕 Створити заявку",
    "check_status":   "✅ Перевірити статус задачі",
    "add_comment":    "📝 Список моїх задач",
    "exit_comment":   "❌ Вийти з режиму коментаря",
    "help":           "ℹ️ Допомога",
    "confirm_create": "Створити задачу",
    "exit":           "Вийти на головну",
    "back":           "Назад",
    "continue_unauthorized": "Продовжити без авторизації",
    "restart":               "Повторити /start"
}

def make_keyboard(step: int, description: str = "") -> tuple[str, ReplyKeyboardMarkup]:
    """
    Повертає (prompt, ReplyKeyboardMarkup) для поточного кроку створення заявки.
    """
    name = STEPS[step]

    # Підбираємо кнопки
    if name == "confirm_create":
        buttons = [[KeyboardButton(BUTTONS["confirm_create"])]]
    else:
        # Якщо для цього кроку є OPTIONS — показуємо їх, інакше залишаємо поле для вводу
        opts = OPTIONS.get(name, [])
        buttons = [[KeyboardButton(opt)] for opt in opts]

    # Додаємо завжди кнопку "Назад"
    buttons.append([KeyboardButton(BUTTONS["back"])])

    markup = ReplyKeyboardMarkup(buttons, resize_keyboard=True)

    # Підсказки- prompt
    prompts = {
        "division":    "Оберіть ваш Підрозділ:",
        "department":  "Оберіть Департамент:",
        "full_name":   "Введіть ваше Прізвище та Ім'я:",
        "service":     "Оберіть Сервіс:",
        "description": "Опишіть вашу проблему:",
        "confirm_create":     (
            f"Натисніть '{BUTTONS['confirm_create']}', якщо все заповнено.\n\n"
            f"Опис задачі:\n{description}"
        )
    }

    prompt = prompts.get(name, "Невідомий крок")
    return prompt, markup

def remove_keyboard() -> ReplyKeyboardRemove:
    """
    Ховає ReplyKeyboardMarkup.
    """
    return ReplyKeyboardRemove()

# --- Статичні клавіатури ---

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
        [KeyboardButton(BUTTONS["check_status"])],
        [KeyboardButton(BUTTONS["exit"])],
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
