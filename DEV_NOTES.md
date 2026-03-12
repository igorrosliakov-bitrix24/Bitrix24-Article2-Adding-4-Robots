# Dev Notes

## Stage 1

Backend for this project: `Python` (`Django + b24pysdk`).

Local run:

```bash
make dev-python
```

Manual check endpoints:

```bash
curl http://localhost:8000/api/public/health
curl http://localhost:8000/api/test
```

Expected result:

- `GET /api/public/health` returns `status=healthy` and `backend=python`
- `GET /api/test` returns a simple JSON test message

Notes:

- Protected endpoint `GET /api/health` remains in place for frontend flows with JWT.
- Public endpoints were added only for local verification of Stage 1.

## Stage 2

Added a minimal robot integration skeleton for the Python backend:

- robot registry
- robot registration service for `bizproc.robot.add`
- robot execution endpoint for Bitrix24
- result sending service for `bizproc.event.send`
- debug endpoint for local manual verification without Bitrix24

Manual check:

```bash
curl -s http://127.0.0.1:8000/api/robots/catalog
curl -s -X POST http://127.0.0.1:8000/api/robots/debug/execute/format_phone \
  -H 'Content-Type: application/json' \
  -d '{"document_id":["crm","CCrmDocumentDeal","DEAL_42"],"properties":{"default_country_code":"7"},"debug_entities":{"contact":{"ID":101,"PHONE":[{"VALUE":"8 (999) 123-45-67","VALUE_TYPE":"MOBILE"}]}}}'
```

Expected result:

- catalog contains registered robots from the app
- debug execution returns `status=success`, `delivery=local`, `robot_code=format_phone`

Notes:

- `POST /api/robots/debug/execute/<robot_code>` is a local verification endpoint.
- Real Bitrix24 calls should use `POST /api/robots/execute/<robot_code>`.

## Stage 3

Added the first real robot: `format_phone`.

Robot input:

- `default_country_code` - optional country code, default `7`

Robot outputs:

- `processed_entities`
- `updated_entities`
- `updated_phone_count`
- `entity_summary`

Local quick check:

```bash
curl -s http://127.0.0.1:8000/api/robots/catalog | jq
curl -s -X POST http://127.0.0.1:8000/api/robots/debug/execute/format_phone \
  -H 'Content-Type: application/json' \
  -d '{"document_id":["crm","CCrmDocumentDeal","DEAL_42"],"properties":{"default_country_code":"7"},"debug_entities":{"contact":{"ID":101,"PHONE":[{"VALUE":"8 (999) 123-45-67","VALUE_TYPE":"MOBILE"}]},"company":{"ID":202,"PHONE":[{"VALUE":"9991230000","VALUE_TYPE":"WORK"}]}}}' | jq
```

Expected result:

- catalog contains `format_phone` without manual `phone` property
- debug execute returns non-zero `updated_phone_count`

Behavior:

- on deal automation the robot reads the linked primary contact and linked company
- it formats all their `PHONE` values
- then saves updated values back to CRM

## Stage 4

Added the second robot: `normalize_full_name`.

Robot inputs:

- no custom fields in the robot form

Robot outputs:

- `processed_entities`
- `updated_entities`
- `updated_field_count`
- `entity_summary`

Local quick check:

```bash
curl -s http://127.0.0.1:8000/api/robots/catalog | jq
curl -s -X POST http://127.0.0.1:8000/api/robots/debug/execute/normalize_full_name \
  -H 'Content-Type: application/json' \
  -d '{"document_id":["crm","CCrmDocumentDeal","DEAL_42"],"debug_entities":{"contact":{"ID":101,"LAST_NAME":"  иВАНОВ  ","NAME":" иВАН ","SECOND_NAME":" иВАНОВИЧ "},"company":{"ID":202,"CONTACT_PERSON":"  пЕТР   пЕТРОВ "}}}' | jq
```

Expected result:

- catalog contains `normalize_full_name`
- debug execute returns non-zero `updated_field_count`

Behavior:

- on deal automation the robot reads the linked primary contact and linked company
- for the contact it normalizes `LAST_NAME`, `NAME`, `SECOND_NAME`
- for the company it normalizes `CONTACT_PERSON`
- each word starts with an uppercase letter, the rest become lowercase
- no initials and no output format settings are used

## Stage 5

Added the third robot: `sum_client_deals`.

Robot inputs:

- no custom fields in the robot form

Robot outputs:

- `deal_count`
- `total_amount`
- `currency_id`
- `client_entity_type`
- `client_entity_id`

Local quick check:

```bash
curl -s http://127.0.0.1:8000/api/robots/catalog | jq
curl -s -X POST http://127.0.0.1:8000/api/robots/debug/execute/sum_client_deals \
  -H 'Content-Type: application/json' \
  -d '{"document_id":["crm","CCrmDocumentDeal","DEAL_42"],"debug_current_deal":{"ID":42,"COMPANY_ID":7,"CURRENCY_ID":"RUB"},"debug_deals":[{"ID":1,"COMPANY_ID":7,"OPPORTUNITY":"1000"},{"ID":2,"COMPANY_ID":7,"OPPORTUNITY":"2500.50"},{"ID":3,"COMPANY_ID":8,"OPPORTUNITY":"999"}]}' | jq
```

Expected result:

- catalog contains `sum_client_deals`
- debug execute returns `deal_count=2` and `total_amount=3500.50`

Behavior:

- on deal automation the robot reads the current deal client
- if the deal has a company, it sums all deals of that company
- otherwise it sums all deals of the linked contact
- it writes the summary to the current deal timeline

## Stage 6

Added the fourth robot: `count_overdue_tasks`.

Robot inputs:

- no custom fields in the robot form

Robot outputs:

- `responsible_user_id`
- `total_tasks_checked`
- `overdue_task_count`

Local quick check:

```bash
curl -s http://127.0.0.1:8000/api/robots/catalog | jq
curl -s -X POST http://127.0.0.1:8000/api/robots/debug/execute/count_overdue_tasks \
  -H 'Content-Type: application/json' \
  -d '{"document_id":["crm","CCrmDocumentDeal","DEAL_42"],"debug_current_deal":{"ID":42,"ASSIGNED_BY_ID":5},"debug_tasks":[{"ID":11,"RESPONSIBLE_ID":5,"DEADLINE":"2026-03-01T09:00:00+00:00","REAL_STATUS":"3"},{"ID":12,"RESPONSIBLE_ID":5,"DEADLINE":"2026-03-30T09:00:00+00:00","REAL_STATUS":"3"},{"ID":13,"RESPONSIBLE_ID":5,"DEADLINE":"2026-03-02T09:00:00+00:00","REAL_STATUS":"5"}]}' | jq
```

Expected result:

- catalog contains `count_overdue_tasks`
- debug execute returns `overdue_task_count=1`

Behavior:

- on deal automation the robot reads the current deal responsible user
- it loads that user's tasks from Bitrix24
- it counts tasks with a past deadline that are still not completed
- it writes the result to the current deal timeline

## Stage 7

Queue and worker were added for asynchronous robot execution.

Flow:

- Bitrix24 sends a robot request to `POST /api/robots/execute/<robot_code>`
- if `ENABLE_RABBITMQ=1`, the API places the job into RabbitMQ via Celery
- Celery worker reads the queued job
- the worker resolves Bitrix24 auth from the original payload
- the worker runs the same robot handler pipeline as the HTTP flow
- the worker sends the result back to Bitrix24 with `bizproc.event.send`

Key files:

- `backends/python/api/celery_app.py`
- `backends/python/api/main/workers/tasks.py`
- `backends/python/api/main/services/robot_queue_service.py`
- `backends/python/api/main/services/robot_execution_service.py`
- `backends/python/api/main/utils/bitrix_account_factory.py`

Local run with queue:

```bash
ENABLE_RABBITMQ=1 make dev-python
```

Or only worker:

```bash
ENABLE_RABBITMQ=1 make dev-python-worker
```

Expected behavior:

- `POST /api/robots/execute/<robot_code>` returns `status=queued`
- the worker processes the job and sends the final robot result to Bitrix24

Notes:

- if `ENABLE_RABBITMQ=0`, the API keeps the synchronous fallback for local development
- debug endpoint `/api/robots/debug/execute/<robot_code>` always executes synchronously

## Stage 8

Current architecture summary:

- `views.py` - HTTP endpoints, install flow, robot execution entrypoints
- `services/robot_registry.py` - robot definitions and Bitrix24 registration payloads
- `services/robot_dispatcher.py` - maps `robot_code` to a concrete handler
- `robot_handlers/` - orchestration layer for each robot
- `services/` - Bitrix24 calls and business logic
- `services/bitrix_client.py` - shared Bitrix24 API wrapper
- `workers/tasks.py` - asynchronous job entrypoint for queued execution
- `services/robot_result_service.py` - sends `RETURN_VALUES` back to Bitrix24

Robots overview:

- `format_phone`
  - reads linked contact/company phones
  - normalizes and updates CRM cards
  - returns sync counters
- `normalize_full_name`
  - reads linked participant names from contact/company cards
  - normalizes name fields and updates CRM cards
  - returns sync counters
- `sum_client_deals`
  - sums all deals of the current deal client
  - returns total values
  - writes a visible comment into the current deal timeline
- `count_overdue_tasks`
  - counts overdue tasks of the current deal responsible user
  - returns total values
  - writes a visible comment into the current deal timeline

Platform check scenarios:

- `format_phone`
  - add robot to a deal stage
  - move the deal to that stage
  - verify that linked contact/company phones are normalized in CRM cards
- `normalize_full_name`
  - add robot to a deal stage
  - move the deal to that stage
  - verify that linked contact/company participant name fields are normalized in CRM cards
- `sum_client_deals`
  - add robot to a deal stage
  - move the deal to that stage
  - verify a new timeline comment in the current deal with the total client deal sum
- `count_overdue_tasks`
  - add robot to a deal stage
  - move the deal to that stage
  - verify a new timeline comment in the current deal with the overdue tasks count
