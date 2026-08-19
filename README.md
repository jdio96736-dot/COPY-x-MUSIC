# Copy x Music — Telegram Music Bot

## Required Replit Secrets

Create exactly these four Secrets:

- `TELEGRAM_BOT_TOKEN`
- `API_ID`
- `API_HASH`
- `SESSION_SECRET`

`SESSION_SECRET` is the Pyrogram string session of the assistant/user account that will join voice chats.

## Important Telegram setup

The assistant account must be able to join the target group and manage the voice chat. The bot account must also have enough group permissions to create/join invite links when automatic assistant invitation is needed.

Start a voice chat in the group, then use:

`/play song name`

## Run

Replit automatically uses:

`python main.py`

The project installs:

- Pyrogram
- TgCrypto
- PyTgCalls (`py-tgcalls`)
- yt-dlp + its default EJS package
- aiohttp

The Nix configuration supplies FFmpeg and Deno.

## Notes

YouTube extraction is performed with yt-dlp. Current yt-dlp releases require a supported JavaScript runtime and EJS support for full YouTube compatibility; this project therefore installs the default yt-dlp extras and Deno.

Lyrics are deliberately not fabricated. A real lyrics provider would require another API/secret, which is outside the requested four-secret configuration.

The project uses SQLite for favourites/history/settings. Runtime queues remain in memory.
