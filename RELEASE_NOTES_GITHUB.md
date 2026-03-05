# Release Notes (GitHub)

## Summary

This update improves project initialization, database flexibility, and Docker runtime safety.

## What's Changed

- Added DB selection in `make dev-init` with support for both `PostgreSQL` and `MySQL` (`DB_TYPE`).
- Split database services in `docker-compose.yml` into profiles:
  - `db-postgres`
  - `db-mysql`
- Added MySQL bootstrap schema: `infrastructure/database/init-mysql.sql`.
- Updated `make` targets (`dev-php`, `dev-python`, `dev-node`, backup/restore) to respect selected DB profile.
- Added MySQL compatibility for all backends:
  - PHP: MySQL extensions/clients, DB wait strategy in entrypoint, migration compatibility.
  - Python: DB engine switch by `DB_TYPE`, added `PyMySQL`.
  - Node.js: runtime DB client switch (`pg` / `mysql2`).
- Fixed CloudPub architecture handling:
  - removed hardcoded ARM image tag,
  - added configurable `CLOUDPUB_IMAGE` and `CLOUDPUB_PLATFORM`,
  - auto-setup in `dev-init` based on host architecture.
- Improved Docker safety in `dev-init`:
  - removed global `docker network prune -f`,
  - cleanup is now project-scoped and requires explicit user confirmation.
- Updated docs in `README.md` and `instructions/python/bitrix24-python-sdk.md`.

## Notes

- Cross-backend smoke tests were intentionally skipped in this phase, because `dev-init` removes non-selected backend folders by design.
