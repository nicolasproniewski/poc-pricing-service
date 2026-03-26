# POC Pricing Service

A lightweight pricing service that stores BTC/USD spot prices and SOFR rates (overnight, 1-month, 3-month) in PostgreSQL and exposes simple GET endpoints for other services to query.

---

## What It Does

| Data | Source | Frequency |
|---|---|---|
| BTC/USD price | CoinGecko → Kraken WS → Yahoo Finance | Every 60 minutes (configurable) |
| SOFR overnight rate | NY Fed → FRED API | Once daily at 8:15am ET (weekdays) |
| SOFR 1-month average | NY Fed → FRED API | Once daily at 8:15am ET (weekdays) |
| SOFR 3-month average | NY Fed → FRED API | Once daily at 8:15am ET (weekdays) |

Prices are persisted to a local PostgreSQL database. A FastAPI server exposes read endpoints.

---

## How It Works

### BTC Price — Cascading Fallback

Three providers are tried in priority order. Each provider has an independent failure counter. After **3 consecutive failures**, that provider is skipped and the next one is tried. Providers self-heal — if CoinGecko recovers, it becomes primary again automatically.

```
CoinGecko (REST) → Kraken WS cache → Yahoo Finance (last resort)
```

- **CoinGecko** — REST poll on each scheduled tick. Free Demo key gives 10,000 calls/month (~7 days at 1/min, or ~45 days at 1/hour).
- **Kraken WebSocket** — a persistent WS connection runs in the background at all times, caching the latest BTC/USD price. No rate limits. Used as fallback if CoinGecko fails 3× in a row, or as an immediate read if the cache is fresh (<2 min old).
- **Yahoo Finance** — true last resort only, via the `yfinance` library. Slower than the other two (web scrape based).

### SOFR Rates — Simple Try/Fallback

All three SOFR tenors are fetched in a single cycle from the same source.

```
NY Fed JSON API (no auth) → FRED API (free key required)
```

- **NY Fed** — authoritative source, no API key needed. Published ~8:00am ET on weekdays. The service fetches at 8:15am ET to ensure the rate is available. Overnight comes from the SOFR endpoint; 1m and 3m averages come from the SOFRAI (SOFR Average Index) endpoint and are stored in the same table with a `rate_type` discriminator.
- **FRED** — St. Louis Fed fallback. Typically lags NY Fed by 1–3 hours. Requires a free API key. Uses series `SOFR`, `SOFR30DAYAVG`, and `SOFR90DAYAVG`.

If both sources fail on a given day, a CRITICAL log is emitted and no row is written (existing data is preserved).

---

## Credentials Required

Copy `.env.example` to `.env` and fill in the values below.

```bash
cp .env.example .env
```

### Required

| Variable | Description | Where to get it |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string | Set to `postgresql+asyncpg://localhost/pricing` for local dev |

### Recommended

| Variable | Description | Where to get it |
|---|---|---|
| `COINGECKO_API_KEY` | Free Demo API key — extends monthly call limit to 10,000 | [coingecko.com/en/api](https://www.coingecko.com/en/api) — free registration |
| `FRED_API_KEY` | Required for SOFR fallback if NY Fed is unavailable | [fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html) — free registration |

> Without `COINGECKO_API_KEY` the free tier is heavily rate-limited. Without `FRED_API_KEY` there is no SOFR fallback if NY Fed goes down.

### Optional

| Variable | Default | Description |
|---|---|---|
| `BTC_POLL_INTERVAL_MINUTES` | `60` | How often to poll for BTC price. Set to `0` to disable polling entirely. |

---

## Current Configuration

| Setting | Value |
|---|---|
| BTC poll interval | 60 minutes |
| BTC provider priority | CoinGecko → Kraken WS → Yahoo Finance |
| BTC failure threshold | 3 consecutive failures before switching provider |
| Kraken WS cache staleness limit | 2 minutes |
| SOFR fetch time | 8:15am ET, weekdays only |
| SOFR tenors stored | overnight, 1m (30-day avg), 3m (90-day avg) |
| SOFR provider priority | NY Fed → FRED |

---

## Local Setup

### Prerequisites

```bash
brew install uv postgresql@16
brew services start postgresql@16
createdb pricing
```

### Install & Run

```bash
git clone https://github.com/nicolasproniewski/poc-pricing-service
cd poc-pricing-service

cp .env.example .env
# Fill in credentials in .env

uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
```

---

## API Endpoints

All endpoints are prefixed with `/v1`. No authentication required.

### BTC

```
GET /v1/btc/latest
```
Returns the most recently stored BTC price.

```json
{
  "price_usd": "70962.00000000",
  "source": "coingecko",
  "fetched_at": "2026-03-24T09:11:33Z"
}
```

```
GET /v1/btc/history?limit=60&since=2026-03-24T00:00:00
```
Returns up to `limit` records (max 1440), optionally filtered by `since`.

### SOFR

```
GET /v1/sofr/latest?rate_type=overnight   (default)
GET /v1/sofr/latest?rate_type=1m
GET /v1/sofr/latest?rate_type=3m
```
Returns the most recently stored rate for the requested tenor. `rate_type` defaults to `overnight` if omitted.

```json
{
  "rate_date": "2026-03-25",
  "rate_type": "overnight",
  "rate_pct": "3.6300",
  "source": "nyfed",
  "fetched_at": "2026-03-26T08:15:02Z"
}
```

```
GET /v1/sofr/history?rate_type=1m&limit=30
```
Returns up to `limit` records for the requested tenor (max 365). Valid `rate_type` values: `overnight`, `1m`, `3m`.

### Health

```
GET /v1/health
```

```json
{
  "status": "ok",
  "db": "connected",
  "kraken_ws": "live",
  "scheduler": "running"
}
```

---

## Notes

- This is a POC running locally — nothing is deployed. The service and scheduler stop when the terminal is closed.
- PostgreSQL data persists across restarts; the app must be restarted manually.
- The `source` field on each price record indicates which provider served that data point — useful for monitoring fallback frequency.
- SOFR can be triggered manually for testing: `uv run python -c "import asyncio; from app.services.sofr_service import fetch_and_store; asyncio.run(fetch_and_store())"`
