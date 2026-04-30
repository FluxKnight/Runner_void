# VOID RUNNER Global Server Setup

This version can be hosted publicly so players on different networks can share accounts and ranks.

## What changed

`server/void_server.py` is now global-hosting ready:

- Binds to `0.0.0.0`
- Uses the hosting provider's `PORT` environment variable
- Still works locally on port 5050
- Game clients only need `data/server_config.json` changed to the public server URL

## Local test

```powershell
cd "$env:USERPROFILE\Runner_void"
python server/void_server.py
```

Then open:

```text
http://127.0.0.1:5050/health
```

## Global deploy idea

Deploy the repository to a Python web hosting service.

Start command:

```bash
python server/void_server.py
```

Build command can be empty, or:

```bash
pip install -r requirements-server.txt
```

After deploy, the host gives a public URL, for example:

```text
https://void-runner-server.onrender.com
```

Put that URL into every player's game folder:

```json
{
  "server_url": "https://void-runner-server.onrender.com"
}
```

File path:

```text
data/server_config.json
```

Then every player who uses the same URL shares:

- accounts
- display names
- best level
- best gems
- best score

## Important

This is still a simple prototype server.

For a real public game, the next upgrade should be:

- hashed passwords
- PostgreSQL / hosted database
- admin controls
- anti-cheat/rate limit
- HTTPS-only server
- proper user sessions/tokens
