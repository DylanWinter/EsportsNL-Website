# Database Schema
The site uses SQLite3 for the database. This page details the schema.

## Event
This table stores a list of all events. Note that a single tournament can have multiple events on start.gg,
so multiple events can have the same slug here. 

Raw DDL: ``CREATE TABLE Event (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    name             TEXT    NOT NULL,
    startgg_slug     TEXT,
    start_date       TEXT,
    end_date         TEXT,
    location         TEXT    DEFAULT ('Online'),
    game             TEXT,
    organizer        TEXT    DEFAULT ('Esports NL'),
    startgg_event_id INTEGER,
    UNIQUE (
        startgg_slug,
        startgg_event_id
    )
);
``

| Column            | Type    | Constraints                     | Notes                                                                                                                                                    | Default      |
|------------------|--------|---------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------|-------------|
| id               | INTEGER | PRIMARY KEY, AUTOINCREMENT      |                                                                                                                                                          |             |
| name             | TEXT    | NOT NULL                        |                                                                                                                                                          |             |
| startgg_slug     | TEXT    |                                 | The unique part of the tournament's link i.e.`esports-nl-cs2-wingman-cup-february-2025` for [this tournament](esports-nl-cs2-wingman-cup-february-2025). |             |
| start_date       | TEXT    |                                 | ISO8601 string.                                                                                                                                          |             |
| end_date         | TEXT    |                                 | ISO8601 string.                                                                                                                                          |             |
| location         | TEXT    |                                 |                                                                                                                                                          | 'Online'    |
| game             | TEXT    |                                 |                                                                                                                                                          |             |
| organizer        | TEXT    |                                 | Currently unused.                                                                                                                                        | 'Esports NL'|
| startgg_event_id | INTEGER |                                 | Refers to the event, not the tournament.                                                                                                                 |             |

## EventEntrant
This table refers to teams. A team is associated with one and only one event; if the same team participates in several 
events, they will get a new EventEntrant row each time. 

Raw DDL: ``CREATE TABLE EventEntrant (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    tournament_id      INTEGER REFERENCES Event (id) ON DELETE CASCADE
                                                     ON UPDATE CASCADE,
    name               TEXT,
    startgg_entrant_id INTEGER UNIQUE,
    placement          INTEGER
);
``

| Column              | Type    | Constraints                                | Notes                 | Default |
|--------------------|--------|--------------------------------------------|-----------------------|---------|
| id                 | INTEGER | PRIMARY KEY, AUTOINCREMENT                 |                       |         |
| tournament_id      | INTEGER | REFERENCES Event (id) ON DELETE CASCADE ON UPDATE CASCADE | Foreign key to Event. |         |
| name               | TEXT    |                                            |                       |         |
| startgg_entrant_id | INTEGER | UNIQUE                                     |                       |         |
| placement          | INTEGER |                                            |                       |         |

## Player
Player profile data. 

Raw DDL: ``CREATE TABLE Player (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    tag                   TEXT    NOT NULL,
    discord_id            INTEGER UNIQUE,
    discord_name          TEXT    UNIQUE,
    startgg_id            INTEGER UNIQUE,
    startgg_name          TEXT,
    startgg_discriminator TEXT    UNIQUE
);
``

| Column                  | Type    | Constraints                     | Notes                                                                                                                                                 | Default |
|-------------------------|--------|---------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|---------|
| id                      | INTEGER | PRIMARY KEY, AUTOINCREMENT      |                                                                                                                                                       |         |
| tag                     | TEXT    | NOT NULL                        | Start.gg name.                                                                                                                                        |         |
| discord_id              | INTEGER | UNIQUE                          |                                                                                                                                                       |         |
| discord_name            | TEXT    | UNIQUE                          |                                                                                                                                                       |         |
| startgg_id              | INTEGER | UNIQUE                          |                                                                                                                                                       |         |
| startgg_name            | TEXT    |                                 |                                                                                                                                                       |         |
| startgg_discriminator   | TEXT    | UNIQUE                          | Unique identifier string for a start.gg user. Used in the link to their profile. For example, [mine](https://www.start.gg/user/6b2ee198) is 6b2ee198. |         |

## PlayerEntrant
Junction table associating Player with EventEntrant. 

Raw DDL: ``CREATE TABLE PlayerEntrant ( player_id INTEGER REFERENCES Player (id) ON DELETE CASCADE ON UPDATE CASCADE NOT NULL, entrant_id INTEGER REFERENCES EventEntrant (id) ON DELETE CASCADE ON UPDATE CASCADE NOT NULL, PRIMARY KEY ( player_id, entrant_id ) );``

| Column      | Type    | Constraints                                              | Notes                              | Default |
|------------|--------|----------------------------------------------------------|------------------------------------|---------|
| player_id   | INTEGER | NOT NULL, REFERENCES Player(id) ON DELETE CASCADE ON UPDATE CASCADE | Foreign key to Player.       |         |
| entrant_id  | INTEGER | NOT NULL, REFERENCES EventEntrant(id) ON DELETE CASCADE ON UPDATE CASCADE | Foreign key to EventEntrant. |         |
| Primary Key |         | (player_id, entrant_id)                                   |               |         |

## Match
A match. Note that there are no EventEntrants directly referenced here other than the winner; this is so that MatchParticipant can used to support an arbitrary
number of teams (i.e. a battle royale match).

| Column             | Type    | Constraints                                             | Notes                        | Default |
|-------------------|--------|---------------------------------------------------------|------------------------------|---------|
| id                 | INTEGER | PRIMARY KEY                                             |                              |         |
| event_id           | INTEGER | REFERENCES Event(id) ON DELETE CASCADE ON UPDATE CASCADE | Foreign key to Event.        |         |
| winner_entrant_id  | INTEGER | REFERENCES EventEntrant(id) ON UPDATE CASCADE          | Foreign key to EventEntrant. |         |
| round              | TEXT    |                                                         |                              |         |
| startgg_id         | INTEGER | UNIQUE                                                  |                              |         |

## MatchParticipant
A junction table associating Match with EventEntrant.

Raw DDL: ``CREATE TABLE MatchParticipant (
    match_id   INTEGER REFERENCES Match (id) ON DELETE CASCADE
                                             ON UPDATE CASCADE,
    entrant_id INTEGER REFERENCES EventEntrant (id) ON UPDATE CASCADE,
    score      INTEGER,
    PRIMARY KEY (
        match_id,
        entrant_id
    )
);
``

| Column      | Type    | Constraints                                             | Notes                        | Default |
|------------|--------|---------------------------------------------------------|------------------------------|---------|
| match_id    | INTEGER | REFERENCES Match(id) ON DELETE CASCADE ON UPDATE CASCADE | Foreign key to Match.        |         |
| entrant_id  | INTEGER | REFERENCES EventEntrant(id) ON UPDATE CASCADE           | Foreign key to EventEntrant. |         |
| score       | INTEGER |                                                         | Currently unused.            |         |
| Primary Key |         | (match_id, entrant_id)                                  |        |         |

