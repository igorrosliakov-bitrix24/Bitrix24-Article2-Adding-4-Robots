# Release Notes

## Версия: переход на Agent Skills и поддержка Claude

- **Структурированные навыки для ИИ-агентов**:
  - Документация реорганизована в формат Agent Skills в директории `.cursor/skills/` и `.claude/skills/` для Cursor и Claude.
  - Добавлены навыки:
    - `manage-b24-environment`: Управление Docker, Makefile и Cloudpub.
    - `navigate-b24-project`: Навигация по структуре проекта.
    - `develop-b24-frontend`: Разработка фронтенда (Nuxt 3, UI Kit).
    - `develop-b24-php`: Разработка бэкенда на PHP (Symfony).
    - `develop-b24-python`: Разработка бэкенда на Python (Django).
    - `develop-b24-node`: Разработка бэкенда на Node.js (Express).
    - `implement-b24-features`: Реализация виджетов, роботов и событий.
- **Поддержка Claude Code**:
  - Добавлен файл `CLAUDE.md` в корень проекта для быстрой настройки контекста.


## Версия: обновление инициализации и инфраструктуры

- Добавлен выбор СУБД при `make dev-init`: поддержка `PostgreSQL` и `MySQL` через `DB_TYPE`.
- Обновлен `docker-compose.yml`: разделение БД на профили `db-postgres` и `db-mysql` с единым alias `database`.
- Добавлен MySQL init-скрипт: `infrastructure/database/init-mysql.sql`.
- Обновлены `make`-команды запуска (`dev-php`, `dev-python`, `dev-node`) и DB-утилиты (`db-backup`, `db-restore`) с учетом выбранной СУБД.
- Адаптированы бэкенды под MySQL:
  - PHP: драйверы/клиенты, ожидание БД в entrypoint, кросс-СУБД миграция.
  - Python: переключение `DATABASE ENGINE` по `DB_TYPE`, добавлен `PyMySQL`.
  - Node.js: подключение к БД через `pg` или `mysql2` по `DB_TYPE`.
- Исправлен CloudPub для разных архитектур:
  - убран жесткий `latest-arm64`,
  - добавлены переменные `CLOUDPUB_IMAGE` и `CLOUDPUB_PLATFORM`,
  - в `dev-init` добавлен выбор значений по архитектуре хоста.
- Повышена безопасность `dev-init`:
  - удален глобальный `docker network prune -f`,
  - очистка ограничена ресурсами текущего проекта и выполняется только с явным подтверждением.
- Обновлена документация: `README.md` и `instructions/python/bitrix24-python-sdk.md`.
