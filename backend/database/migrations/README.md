# Database Migrations

## Task 2: Voice Exercise Schema

- Up migration:
  - `backend/database/migrations/20260331_task2_voice_schema_up.sql`
- Down migration:
  - `backend/database/migrations/20260331_task2_voice_schema_down.sql`

## How To Run

From the project root:

```powershell
psql $env:DATABASE_URL -f backend/database/migrations/20260331_task2_voice_schema_up.sql
```

Rollback:

```powershell
psql $env:DATABASE_URL -f backend/database/migrations/20260331_task2_voice_schema_down.sql
```

## Notes

- The up migration is idempotent (`IF NOT EXISTS` guarded where applicable).
- Rollback drops `language_items.metadata` and speech log columns; this is destructive to stored speech-related data.
