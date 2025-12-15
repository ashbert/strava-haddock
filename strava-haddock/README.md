# Strava Captain Haddock Transformer 🚢

Transform your boring Strava workout titles into Captain Haddock's thundering prose!

> **Before:** "30 min EDM Run with Jon Hosking"  
> **After:** "Blistering Barnacles! A 3.5 Mile Sprint Through the Storm!"

## Setup

### 1. Clone/download this folder

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure credentials

Copy the example environment file:

```bash
cp .env.example .env
```

Edit `.env` and fill in:

- `STRAVA_CLIENT_ID` - From https://www.strava.com/settings/api (you already have: 122228)
- `STRAVA_CLIENT_SECRET` - From the same page
- `ANTHROPIC_API_KEY` - From https://console.anthropic.com/

### 4. Authorize with Strava

Run the auth script to get proper tokens with write access:

```bash
python auth.py
```

This will:
1. Open your browser to Strava's authorization page
2. Ask you to approve the app with `activity:read_all` and `activity:write` scopes
3. Catch the callback and save your tokens to `.env`

You only need to do this once (tokens auto-refresh).

## Usage

### Transform your latest activity

```bash
python haddock.py
```

### Preview without updating Strava

```bash
python haddock.py --dry-run
```

### Transform a specific activity

```bash
python haddock.py --activity 12345678
```

## Example Output

```
Fetching activity from Strava...

Original Activity: 30 min EDM Run with Jon Hosking
ID: 12345678
Type: Run
Date: 2024-01-15

Generating Captain Haddock version...

==================================================
HADDOCK VERSION:
==================================================
Title: Ten Thousand Typhoons! 3.5 Miles Conquered!
Description: Thundering typhoons! Dragged this old carcass through 
30 minutes of electronic sea shanties at 8:33 pace. Burned 527 
kilojoules - enough to power a lighthouse! Finished 456th out of 
3,097 landlubbers. Not bad for a whisky-loving sea captain!
==================================================

Updating Strava...
Done! Activity updated.

View it at: https://www.strava.com/activities/12345678
```

## Automation Ideas

### Run automatically after Peloton syncs

Since Peloton auto-uploads to Strava, you could:

1. **Cron job**: Check every 30 minutes for new activities
2. **Webhook**: Use Strava webhooks to trigger on new activities (more complex setup)
3. **Manual**: Just run it when you remember!

### Simple cron example (Mac/Linux)

```bash
# Edit crontab
crontab -e

# Add line to run every 30 min (adjust path)
*/30 * * * * cd /path/to/strava-haddock && python haddock.py >> /tmp/haddock.log 2>&1
```

## Customization

Edit the prompt in `haddock.py` in the `haddockify()` function to:
- Change the persona (Yoda? Pirate? Shakespeare?)
- Adjust the tone
- Add/remove specific exclamations
- Change output length

## Troubleshooting

**"Token expired" errors**: The script auto-refreshes tokens, but if you see persistent auth errors, run `python auth.py` again.

**"No activities found"**: Make sure your Peloton is connected to Strava and has synced recently.

**Rate limits**: Strava allows 100 reads and 200 total requests per 15 minutes. You won't hit this with normal use.

## License

Do whatever you want with this. Blistering barnacles!
