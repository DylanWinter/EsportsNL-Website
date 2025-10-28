## Basic Setup 

You will need to create a .env file with four variables:

- ``DISCORD_TOKEN``: Your Discord API key. Required to populate upcoming events, and of course to run the Discord bot.
- ``STARTGG_TOKEN``: Your Start.gg API key. Required to access the Start.gg API. Only needed if you are using ``startgg.py``.
- ``ENV``: Controls whether the Discord bot syncs globally or just to a test server. Just leave this as ``ENV=PROD``.
- ``DB_PATH``: The path to your SQLite file. 

From there, you can run ``main.py`` for a debug website server, or ``bot.py`` to run the Discord bot. 