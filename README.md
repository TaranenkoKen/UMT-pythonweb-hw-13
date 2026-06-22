# Contacts REST API

REST API для управління контактами з аутентифікацією, кешуванням і системою ролей.

Стек: FastAPI · SQLAlchemy 2.0 (async) · PostgreSQL · Redis · FastAPI-Mail · slowapi · Cloudinary · pytest · Sphinx · Docker Compose

## Запуск

### 1. Налаштування змінних середовища

```bash
cp .env.example .env
```

Заповни `.env`

### 2. Docker Compose

```bash
docker compose up --build
```

Запускає PostgreSQL, Redis і FastAPI. Swagger — `http://127.0.0.1:8000/docs`.

### 3. Локальний запуск

```bash
python -m venv venv
.venv\Scripts\activate
pip install -r requirements.txt
uvicorn main:app --reload
```

> Потрібні запущені PostgreSQL і Redis. Відповідно налаштуй `DATABASE_URL` і `REDIS_URL` у `.env`.

## Ендпоінти

### Аутентифікація

| Метод | URL | Опис |
|---|---|---|
| `POST` | `/auth/signup` | Реєстрація |
| `POST` | `/auth/login` | Вхід (повертає `access_token` + `refresh_token`) |
| `POST` | `/auth/refresh` | Оновлення пари токенів |
| `GET` | `/auth/verify/{token}` | Підтвердження email |
| `POST` | `/auth/request-password-reset` | Запит на скидання пароля (лист на email) |
| `POST` | `/auth/reset-password` | Встановлення нового пароля за токеном |

### Користувач

| Метод | URL | Опис |
|---|---|---|
| `GET` | `/users/me` | Профіль поточного користувача (ліміт 10 запитів/хв) |
| `PATCH` | `/users/avatar` | Оновлення аватара — тільки для **admin** |

### Контакти (потребують авторизації)

| Метод | URL | Опис |
|---|---|---|
| `POST` | `/contacts/` | Створення контакту |
| `GET` | `/contacts/` | Список контактів (фільтри: `name`, `last_name`, `email`) |
| `GET` | `/contacts/birthdays` | Контакти з днями народження в наступні 7 днів |
| `GET` | `/contacts/{id}` | Отримання контакту за ID |
| `PUT` | `/contacts/{id}` | Оновлення контакту |
| `DELETE` | `/contacts/{id}` | Видалення контакту |

Інтерактивна документація Swagger: `http://localhost:8000/docs`

## Тестування

```bash
pytest tests/ --cov=. --cov-report=term-missing
```
