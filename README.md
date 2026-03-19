# Sync-Strava

## Overview

Python tool for syncing Strava activities to Notion, allowing you to record all your workouts, runs, and rides in custom Notion databases automatically.

## Features

- Fetches Strava activities via Strava API.
- Formats and uploads workout data to your Notion database.
- Can synchronize automatically by schedule.
- Lightweight and easily configurable.

## Requirements

- Python 3.x
- `requests` library
- Strava API credentials
- Notion integration token

## Usage

1. Clone the repository:

   ```bash
   git clone https://github.com/m4x95pt/Sync-Strava
   cd Sync-Strava
   pip install requests
   ```

2. Add your credentials and tokens (`NOTION_TOKEN`, `STRAVA_CLIENT_ID`, `STRAVA_CLIENT_SECRET`, etc).

3. Run manually or set up a scheduled job:
   ```bash
   python sync_strava.py
   ```

## License

MIT License

**Author:** [@m4x95pt](https://github.com/m4x95pt)
