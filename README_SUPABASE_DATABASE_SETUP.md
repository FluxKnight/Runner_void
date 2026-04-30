# VOID RUNNER - Supabase persistent database setup

This update makes account and rank data persistent across school/home/friend computers.

Final architecture:

```text
VoidRunner.exe -> Render server -> Supabase database
```

The game client still uses the same Render URL. Only the server changes.

## What changed

- `server/void_server.py` now supports Supabase.
- If Render has Supabase environment variables, accounts/ranks are saved to Supabase.
- If Supabase is not configured, the server still runs with local JSON fallback.
- Passwords are no longer stored as raw text in Supabase. The server stores salted SHA256 hashes.

## Supabase setup

1. Create a Supabase project.
2. Open `SQL Editor`.
3. Paste the contents of:

```text
server/supabase_schema.sql
```

4. Run it.

## Get keys

In Supabase:

```text
Project Settings -> API
```

Copy:

```text
Project URL
service_role key
```

Important: keep the service role key private. Put it only in Render environment variables. Do not put it in GitHub, game files, EXE, or screenshots.

## Render environment variables

In Render:

```text
void-runner-server -> Environment -> Add Environment Variable
```

Add these:

```text
SUPABASE_URL = your Supabase Project URL
SUPABASE_SERVICE_ROLE_KEY = your Supabase service_role key
SUPABASE_TABLE = void_runner_users
```

Then press:

```text
Manual Deploy -> Deploy latest commit
```

## Test

Open:

```text
https://void-runner-server.onrender.com/health
```

Correct result should include:

```json
{
  "database": "supabase",
  "database_configured": true,
  "storage": "supabase"
}
```

Then open:

```text
https://void-runner-server.onrender.com/debug_users
```

After creating accounts in the game, usernames should appear there.

## Git commands

After copying this patch into your project:

```powershell
cd "$env:USERPROFILE\Runner_void"

git add server/void_server.py server/supabase_schema.sql README_SUPABASE_DATABASE_SETUP.md
git commit -m "Add Supabase persistent database support"
git push origin main
```

Render should redeploy. If it does not, use Manual Deploy.

## Important note

Old school-computer-only accounts cannot appear automatically unless they were already synced to the server before Render restarted. New accounts after this update will be persistent.
