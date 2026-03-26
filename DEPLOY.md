# Деплой на VPS

## Идея статьи: «Добавляем 4 робота в Bitrix24 — и деплоим на свой сервер»

### О чём статья

Статья показывает, как с нуля создать Bitrix24-приложение с четырьмя автоматизированными роботами для CRM и задеплоить его на VPS. Роботы — это кнопки в бизнес-процессах Bitrix24, которые выполняют кастомную логику на вашем сервере: нормализуют телефоны, имена, считают сделки и задачи.

### Четыре робота, которые мы сделаем

| Робот | Что делает | Пример использования |
|-------|-----------|----------------------|
| `format_phone` | Приводит телефоны контактов/компаний к единому формату | `+7 999 123-45-67` → `+79991234567` |
| `normalize_full_name` | Разбивает ФИО на имя/фамилию/отчество | `"иванов иван иванович"` → правильные поля |
| `sum_client_deals` | Суммирует все сделки клиента и пишет в таймлайн | «Итого сделок: 5 на сумму 450 000 ₽» |
| `count_overdue_tasks` | Считает просроченные задачи ответственного | «У менеджера 3 просроченные задачи» |

### Архитектура системы

```
Bitrix24 (облако)
    │
    │  HTTPS  (webhook + OAuth)
    ▼
Nginx (reverse proxy + SSL)
    ├── /         → Frontend (Nuxt 3, порт 3000)
    └── /api/     → Python API (Django + Gunicorn, порт 8000)
                        │
                        ├── PostgreSQL (база данных)
                        └── RabbitMQ + Celery (очередь, опционально)
```

Когда менеджер запускает бизнес-процесс со стадией «Нормализовать телефон», Bitrix24 делает POST-запрос на ваш сервер. Django обрабатывает его, обращается обратно к Bitrix24 через SDK и возвращает результат.

### Как роботы регистрируются

При установке приложения вызывается `bizproc.robot.add` для каждого из четырёх роботов. Bitrix24 запоминает адрес вашего сервера и будет слать туда вызовы.

```python
# backends/python/api/main/services/robot_registry.py
ROBOTS = [
    RobotDefinition(
        code="format_phone",
        handler_url="/api/robots/execute/format_phone",
        name={"ru": "Нормализовать телефоны", "en": "Format Phone Numbers"},
        input_params=[
            RobotParam(name="default_country_code", type="string", required=False)
        ],
        return_values=[
            RobotParam(name="updated_phone_count", type="int"),
            RobotParam(name="entity_summary", type="string"),
        ]
    ),
    # ... ещё три робота
]
```

### Как выглядит выполнение робота

```
POST /api/robots/execute/format_phone
{
  "auth": { "access_token": "...", "client_endpoint": "https://your.bitrix24.ru/rest/" },
  "event_token": "abc123...",
  "properties": { "default_country_code": "7" }
}
```

Бэкенд:
1. Декодирует JWT, проверяет подлинность запроса
2. Определяет сделку и связанных контактов/компании
3. Вызывает `crm.contact.get`, нормализует телефоны
4. Вызывает `crm.contact.update` для каждого изменения
5. Вызывает `bizproc.event.send` с результатами → Bitrix24 продолжает бизнес-процесс

---

## Деплой на VPS — пошаговый гайд

### Что нужно перед началом

- VPS с Ubuntu 22.04+ (рекомендуется минимум 2 CPU, 4 GB RAM)
- Доменное имя, направленное A-записью на IP вашего VPS
- Приложение зарегистрировано в Bitrix24 с нужными правами

### Шаг 1. Подготовка сервера

```bash
# Подключаемся к серверу
ssh user@YOUR_SERVER_IP

# Обновляем систему
sudo apt update && sudo apt upgrade -y

# Устанавливаем Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Проверяем
docker --version
docker compose version
```

### Шаг 2. Клонируем репозиторий

```bash
git clone https://github.com/YOUR_ORG/YOUR_REPO.git /opt/b24-robots
cd /opt/b24-robots
```

### Шаг 3. Создаём `.env` для продакшена

```bash
cp .env.example .env
nano .env
```

Заполняем эти переменные (остальные можно оставить по умолчанию):

```dotenv
# Ваш домен — именно тот, что указан в настройках приложения в Bitrix24
VIRTUAL_HOST=https://your-domain.com

# Бэкенд (Python)
SERVER_HOST=http://api-python:8000

# Секрет для JWT-токенов (генерируем случайную строку)
JWT_SECRET=your-very-long-random-secret-here

# Данные приложения из личного кабинета Bitrix24
CLIENT_ID=local.xxxxxxxxxxxxxxxx.xxxxxxxx
CLIENT_SECRET=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
SCOPE=crm,user_brief,pull,placement,userfieldconfig,bizproc

# База данных (PostgreSQL)
DB_TYPE=postgresql
DB_NAME=appdb
DB_USER=appuser
DB_PASSWORD=strong_password_here
DB_ROOT_PASSWORD=strong_root_password
DATABASE_URL=postgresql://appuser:strong_password_here@database:5432/appdb

# Режим продакшена
BUILD_TARGET=production
NODE_ENV=production

# Django admin
DJANGO_SUPERUSER_USERNAME=admin
DJANGO_SUPERUSER_EMAIL=admin@your-domain.com
DJANGO_SUPERUSER_PASSWORD=strong_admin_password

# Очередь (включить если нужна асинхронная обработка)
ENABLE_RABBITMQ=0
```

### Шаг 4. Настраиваем Nginx

Открываем файл конфигурации и заменяем `YOUR_DOMAIN` на ваш домен:

```bash
sed -i 's/YOUR_DOMAIN/your-domain.com/g' infrastructure/nginx/nginx.conf
```

Создаём директории для сертификатов:

```bash
mkdir -p infrastructure/nginx/certs
mkdir -p infrastructure/nginx/certbot-webroot
```

### Шаг 5. Получаем SSL-сертификат (Let's Encrypt)

Сначала запускаем Nginx на HTTP (для прохождения ACME-challenge):

```bash
# Временно комментируем SSL-блок в nginx.conf — пустим трафик по HTTP
# Потом раскомментируем. Либо используем скрипт:
./scripts/deploy.sh
```

Скрипт автоматически:
1. Поднимет Nginx на порту 80
2. Запросит сертификат через certbot
3. Соберёт production-образы
4. Запустит все сервисы
5. Выполнит миграции БД и collectstatic

### Шаг 6. Запускаем (ручной способ)

Если хотите делать всё вручную:

```bash
# Собираем образы в режиме production
BUILD_TARGET=production docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  --profile frontend,python,db-postgres \
  build

# Поднимаем сервисы
BUILD_TARGET=production docker compose \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  --profile frontend,python,db-postgres \
  up -d

# Мигрируем базу данных
docker exec api python manage.py migrate --noinput

# Собираем статику Django
docker exec api python manage.py collectstatic --noinput

# Создаём суперпользователя
docker exec api python manage.py createsuperuser --noinput
```

### Шаг 7. Проверяем работу

```bash
# Все контейнеры запущены?
docker compose ps

# Логи API
docker logs api --tail=50

# Логи Nginx
docker logs nginx --tail=20

# Health check
curl https://your-domain.com/api/public/health
# Ожидаем: {"status": "ok"}

# Каталог роботов
curl https://your-domain.com/api/robots/catalog
```

### Шаг 8. Прописываем URL в настройках приложения Bitrix24

В личном кабинете разработчика Bitrix24 → ваше приложение:
- **URL обработчика**: `https://your-domain.com/api/install`
- **Начальная страница**: `https://your-domain.com/`

После установки приложения Bitrix24 зарегистрирует все четыре робота через backend install hook, и они появятся в дизайнере бизнес-процессов.

---

## Опциональные настройки

### Включить RabbitMQ + Celery (асинхронная очередь)

Нужно, если роботы должны работать в фоне (не блокировать Bitrix24 на время выполнения):

```bash
# В .env
ENABLE_RABBITMQ=1
RABBITMQ_USER=queue_user
RABBITMQ_PASSWORD=queue_password
RABBITMQ_DSN=amqp://queue_user:queue_password@rabbitmq:5672/%2f

# Запускаем с воркером
./scripts/deploy.sh --with-queue
```

### Автоматическое обновление SSL-сертификата

Certbot в `docker-compose.prod.yml` уже настроен на автообновление каждые 12 часов. Nginx перечитает сертификат при следующей ротации.

Для ручного обновления:
```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml run --rm certbot renew
docker exec nginx nginx -s reload
```

### Обновление приложения

```bash
cd /opt/b24-robots
git pull origin main
./scripts/deploy.sh
```

---

## Структура файлов деплоя

```
.
├── docker-compose.yml          # Основной compose (dev + prod)
├── docker-compose.prod.yml     # Production override (Nginx, no volume mounts)
├── infrastructure/
│   └── nginx/
│       ├── nginx.conf          # Nginx: reverse proxy + SSL
│       ├── certs/              # Let's Encrypt сертификаты (gitignored)
│       └── certbot-webroot/    # ACME challenge (gitignored)
└── scripts/
    └── deploy.sh               # Скрипт полного деплоя
```

---

## Полезные команды

```bash
# Статус всех контейнеров
docker compose -f docker-compose.yml -f docker-compose.prod.yml ps

# Логи конкретного сервиса
docker logs api -f
docker logs nginx -f
docker logs frontend -f

# Рестарт одного сервиса
docker compose -f docker-compose.yml -f docker-compose.prod.yml restart api-python

# Подключиться к Django shell
docker exec -it api python manage.py shell

# Подключиться к PostgreSQL
docker exec -it $(docker ps -qf name=postgres) psql -U appuser appdb
```
