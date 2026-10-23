# Gold Price Alert Bot

A Telegram bot that watched gold prices and pinged subscribers when the price moved past a threshold. Built for myself and other people who'd rather get a message than refresh a chart all day.

> **Status: shut down.** The bot ran on Render's free tier with 15 subscribers and delivered price alerts for a period before I took it offline. The database and hosting are no longer active. The code is kept here as a working reference.

## Why I Built This

I own gold and got tired of checking the price manually. The bot does one thing: watch the price, tell you when something happened, then stay quiet for a while so it doesn't spam you. Other people asked for it, so it ended up with real subscribers instead of just me.

## What It Does

- Polls a gold price API every 25 minutes
- Compares the current price against the last 5 readings
- Sends a Telegram alert when the change passes a configurable threshold
- Enforces a cooldown between alerts (default 40 minutes) so a choppy market doesn't flood subscribers
- Converts the per-ounce price to per-gram for 24k, 22k, 21k, and 18k gold
- Admin commands: view status, list subscribers, remove a subscriber, set the threshold, broadcast a message
- Subscribers can `/start`, `/unsubscribe`, check `/price`, `/prices <n>` for history, and `/gram <karat>`

## Track Record

- **Subscribers at shutdown:** 15
- **Hosted on:** Render (free tier)
- **Alerts:** delivered consistently to subscribers while the bot was running — alerts were triggered by an external scheduler pinging an HTTP endpoint, not by an internal timer

No uptime percentage or request count is quoted here because I didn't measure them.

## Architecture

```
Telegram  ──►  python-telegram-bot  ──►  command handlers (bot.py)
                                              │
                                              ▼
                                       Supabase (Postgres)
                                       ├── subscribers
                                       ├── historical_prices
                                       └── bot_settings

External scheduler  ──►  POST /check  ──►  alert.checkPriceChange()
                                              │
                                              ├── fetch price (fetch.py)
                                              ├── compare vs last 5
                                              ├── check cooldown
                                              └── broadcast via Telegram
```

The Flask process serves two things: `/health` for the host's health check, and `/check` for the external scheduler to trigger a price check. Keeping the timer outside the app meant the bot didn't need to stay awake on its own — the scheduler woke it, it did one check, it went back to sleep.

## Technical Highlights

- **Cooldown logic** — after an alert fires, further alerts are suppressed until the cooldown expires. Stored in `bot_settings` so it survives restarts.
- **Percentage-change detection** — compares the current price against both the recent high and recent low, reports whichever move is larger, with direction (`UP` / `DOWN`) and the reference price.
- **Supabase for persistence** — subscribers, price history, and bot settings all lived in Postgres. No local state, so the bot could restart freely.
- **Env-based config** — token, admin chat ID, Supabase credentials, thresholds, and intervals all come from environment variables. Nothing hardcoded.
- **Re-subscription** — an unsubscribed user who runs `/start` again is reactivated rather than duplicated, so chat history stays intact.
- **Admin gating** — admin commands check the caller's chat ID against `ADMIN_CHAT_ID` and refuse anyone else.

## Run It Yourself

You'll need a Telegram bot token (from [@BotFather](https://t.me/BotFather)), a Supabase project with the tables below, and a gold price API endpoint.

```bash
git clone <repo>
cd <repo>
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in the values
python src/main.py
```

`.env` needs:

```
BOT_TOKEN=
ADMIN_CHAT_ID=
SUPABASE_URL=
SUPABASE_KEY=
GOLD_API=
CHECK_INTERVAL_MINUTES=25
COOLDOWN_MINUTES=40
DIFF_THRESHOLD=0.3
PORT=8080
```

### Supabase schema

Create these tables in the Supabase SQL editor:

```sql
create table subscribers (
  id bigserial primary key,
  chat_id bigint unique not null,
  username text,
  first_name text,
  is_active boolean default true,
  subscribed_at timestamptz default now(),
  role text default 'user'
);

create table historical_prices (
  id bigserial primary key,
  price numeric not null,
  recorded_at timestamptz default now()
);

create table bot_settings (
  id bigserial primary key,
  key text unique not null,
  value text not null
);
```

### Docker

```bash
docker build -t gold-bot .
docker run --env-file .env -p 8080:8080 gold-bot
```

## Known Limitations

- **No tests.** The price-change logic would be easy to unit-test with a mocked fetcher; I haven't done it yet.
- **Single-instance only.** The cooldown is a row in `bot_settings`, so running two copies of the bot would race on it. Fine for one host, not for horizontal scaling.
- **The external scheduler is a dependency.** If it stops pinging, the bot stops checking prices. There's no fallback timer inside the app.
- **`DIFF_THRESHOLD` is a percentage** — `0.3` means 0.3%, which is a tight band. Easy to misread.
- **Admin commands trust `ADMIN_CHAT_ID`** — one value, no roles table. Fine for a small bot, wouldn't scale to multiple admins without a schema change.

## Commands

| Command | Who | What |
|---|---|---|
| `/start` | anyone | Subscribe (or re-subscribe) |
| `/unsubscribe` | anyone | Stop alerts |
| `/price` | anyone | Current gold price per ounce |
| `/prices <n>` | anyone | Last `n` prices (max 10) |
| `/gram <karat>` | anyone | Price per gram for 24/22/21/18k |
| `/help` | anyone | List commands |
| `/donate` | anyone | Donation info |
| `/status` | admin | Subscriber counts, last price |
| `/subscribers` | admin | List subscribers |
| `/remove <chat_id>` | admin | Deactivate a subscriber |
| `/threshold <price>` | admin | Set the alert threshold |
| `/broadcast <msg>` | admin | Message all active subscribers |