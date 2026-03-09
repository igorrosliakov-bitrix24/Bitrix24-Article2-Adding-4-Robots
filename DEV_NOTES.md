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
