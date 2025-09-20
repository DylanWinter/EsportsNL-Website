# The Start.gg API

We get all of our data from [start.gg's API](https://developer.start.gg/docs/intro/). The script startgg.py is where this 
happens.

For this to work, you will need a variable in your .env file: 
``STARTGG_TOKEN=your_token_here``.

There are two ways to use the script: adding a single tournament to the database, or
rebuilding the database from scratch.

For a single file, run

``python3 startgg.py tournament-slug`` where tournament-slug is the start.gg slug of the tournament
you are adding. 

To reset the database, run

``python3 startgg.py --reset``

### Notes
Some things to consider about Start.gg:

- Players can be anonymous. This happens when a tournament administrator adds a player without an account to a tournament. 
This means you can't assume every entrant in an event has an associated start.gg account.
- *Tournament* refers to the overarching tournament. Each has a slug (i.e. ``esports-nl-cs2-wingman-cup-february-2025``). 
*Event* refers to an event within each tournament. A single tournament can have events in multiple games. ``startgg.py``
will create a new Event row in the database for each Event, not for each tournament. 
- Multiple players on Start.gg can be associated with the same Discord account for some reason. ``startgg.py`` should
automatically merge their stats in this case. 