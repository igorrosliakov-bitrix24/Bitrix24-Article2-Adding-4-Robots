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
- robot registration service for `bizproc.robot.add` / `bizproc.robot.update`
- robot execution endpoint for Bitrix24
- result sending service for `bizproc.event.send`
- temporary debug endpoint for local manual verification without Bitrix24

Manual check:

```bash
curl -s http://127.0.0.1:8000/api/robots/catalog
curl -s -X POST http://127.0.0.1:8000/api/robots/debug/execute/system_ping \
  -H 'Content-Type: application/json' \
  -d '{"check":"stage2"}'
```

Expected result:

- catalog contains `system_ping`
- debug execution returns `status=success`, `delivery=local`, `robot_code=system_ping`

Notes:

- `POST /api/robots/debug/execute/<robot_code>` is a temporary local verification endpoint.
- Real Bitrix24 calls should use `POST /api/robots/execute/<robot_code>`.

## Stage 3

Added the first real robot: `format_phone`.

Robot inputs:

- `phone` - required phone number string
- `default_country_code` - optional country code, default `7`

Robot outputs:

- `formatted_phone`
- `digits_only`
- `is_valid`

Local quick check:

```bash
curl -s http://127.0.0.1:8000/api/robots/catalog | jq
curl -s -X POST http://127.0.0.1:8000/api/robots/debug/execute/format_phone \
  -H 'Content-Type: application/json' \
  -d '{"phone":"8 (999) 123-45-67","default_country_code":"7"}' | jq
```

Expected result:

- catalog contains `format_phone`
- debug execute returns `formatted_phone: "+79991234567"`
