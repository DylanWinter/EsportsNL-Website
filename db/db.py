import sqlite3
import os
from dotenv import load_dotenv


class Database:
    def __init__(self):
        # establish connection
        load_dotenv()
        self.db_path = os.path.join(os.getcwd(), os.getenv("DB_PATH"))

    def get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def clear_all_event_data(self):
        """
        Deletes all data from Event, Player, EventEntrant, and PlayerEntrant tables
        and resets AUTOINCREMENT counters for Event, Player, and EventEntrant.
        """
        conn = self.get_conn()
        with conn:
            conn = self.get_conn()
            # Delete all data from dependent tables first to avoid foreign key issues
            conn.execute("DELETE FROM PlayerEntrant")
            conn.execute("DELETE FROM EventEntrant")
            conn.execute("DELETE FROM Player")
            conn.execute("DELETE FROM Event")
            conn.execute("DELETE FROM Match")
            conn.execute("DELETE FROM MatchParticipant")

            # Reset AUTOINCREMENT counters
            conn.execute("DELETE FROM sqlite_sequence WHERE name='Event'")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='Player'")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='EventEntrant'")
            conn.execute("DELETE FROM sqlite_sequence WHERE name='Match'")

            conn.commit()
        print("All event-related data cleared and AUTOINCREMENT counters reset.")

    def write_event_data(self, events: list[dict]):
        """
        Writes event data to the SQLite database.
        :param events: A list of dictionaries containing events to insert. A single tournament can have multiple events,
        hence the list.
        """
        conn = self.get_conn()
        # A single tournament can have multiple events, hence the loop
        for event in events:
            with conn:
                cur = conn.execute("INSERT OR IGNORE INTO "
                                  "Event (name, startgg_slug, start_date, end_date, location, game, startgg_event_id) "
                                  "VALUES (?, ?, ?, ?, ?, ?, ?)",
                                  (event["name"], event["startgg_slug"], event["start_time"], event["end_time"],
                                  event["location"], event["game"], event["startgg_event_id"]))
                if cur.lastrowid:
                    event_id = cur.lastrowid
                else:
                    cur = conn.execute(
                        "SELECT id FROM Event WHERE startgg_slug = ?",
                        (event["startgg_slug"],)
                    )
                    event_id = cur.fetchone()[0]

                # Entrants
                for entrant in event["teams"]:
                    conn.execute(
                        "INSERT OR IGNORE INTO EventEntrant (tournament_id, name, startgg_entrant_id, placement) "
                        "VALUES (?, ?, ?, ?)",
                        (
                            event_id,
                            entrant["name"],
                            entrant["startgg_entrant_id"],
                            entrant["placement"]
                        )
                    )

                    cur = conn.execute(
                        "SELECT id FROM EventEntrant WHERE startgg_entrant_id = ? AND tournament_id = ?",
                        (entrant["startgg_entrant_id"], event_id)
                    )
                    entrant_id = cur.fetchone()[0]

                    for player in entrant["participants"]:
                        # First, try to find an existing player by Discord ID
                        player_id = None
                        if player.get("discord_id") is not None:
                            fetch = conn.execute(
                                "SELECT id, startgg_id, startgg_name FROM Player WHERE discord_id = ?",
                                (player["discord_id"],)
                            ).fetchone()
                            if fetch:
                                player_id = fetch[0]
                                # Optional: update startgg info if missing or changed
                                if player.get("startgg_id") and fetch[1] != player["startgg_id"]:
                                    conn.execute(
                                        "UPDATE Player SET startgg_id = ?, startgg_name = ? WHERE id = ?",
                                        (player["startgg_id"], player["startgg_name"], player_id)
                                    )

                        # If not found by Discord, try start.gg ID
                        if player_id is None and player.get("startgg_id") is not None:
                            fetch = conn.execute(
                                "SELECT id FROM Player WHERE startgg_id = ?",
                                (player["startgg_id"],)
                            ).fetchone()
                            if fetch:
                                player_id = fetch[0]

                        # If still not found, insert a new player (anonymous or first occurrence)
                        if player_id is None:
                            conn.execute(
                                "INSERT OR IGNORE INTO Player (tag, discord_id, discord_name, startgg_name, startgg_discriminator, startgg_id) "
                                "VALUES (?, ?, ?, ?, ?, ?)",
                                (
                                    player["startgg_name"],
                                    player.get("discord_id"),
                                    player.get("discord_name"),
                                    player["startgg_name"],
                                    player.get("discriminator"),
                                    player.get("startgg_id")
                                )
                            )
                            player_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

                        conn.execute(
                            "INSERT OR IGNORE INTO PlayerEntrant (player_id, entrant_id) VALUES (?, ?)",
                            (player_id, entrant_id)
                        )

                # Matches
                for match in event["matches"]:
                    # Map winner_startgg_entrant_id to local EventEntrant.id
                    winner_startgg_id = match.get("winner_startgg_entrant_id")
                    winner_entrant_id = None
                    if winner_startgg_id is not None:
                        winner_row = conn.execute(
                            "SELECT id FROM EventEntrant WHERE startgg_entrant_id = ? AND tournament_id = ?",
                            (winner_startgg_id, event_id)
                        ).fetchone()
                        if winner_row:
                            winner_entrant_id = winner_row[0]

                    conn.execute(
                        "INSERT OR IGNORE INTO Match (event_id, winner_entrant_id, round, startgg_id) "
                        "VALUES (?, ?, ?, ?)",
                        (event_id, winner_entrant_id, match.get("round"), match.get("startgg_id"))
                    )

                    match_id = conn.execute(
                        "SELECT id FROM Match WHERE startgg_id = ?",
                        (match.get("startgg_id"),)
                    ).fetchone()[0]

                    for entrant_startgg_id in match["participants"]:
                        entrant_row = conn.execute(
                            "SELECT id FROM EventEntrant WHERE startgg_entrant_id = ? AND tournament_id = ?",
                            (entrant_startgg_id, event_id)
                        ).fetchone()

                        if entrant_row is None:
                            print(f"Entrant not found for match {match.get('startgg_id')}: {entrant_startgg_id}")
                            continue

                        entrant_id = entrant_row[0]

                        conn.execute(
                            "INSERT OR IGNORE INTO MatchParticipant (match_id, entrant_id) VALUES (?, ?)",
                            (match_id, entrant_id)
                        )

    def get_all_events(self):
        conn = self.get_conn()
        with conn:
            res = conn.execute("SELECT * FROM Event")
            return [dict(row) for row in res.fetchall()]

    def get_all_players(self):
        conn = self.get_conn()
        with conn:
            res = conn.execute("""
                SELECT 
                    Player.*, 
                    COUNT(PlayerEntrant.player_id) AS total_events_played,
                    MIN(Event.start_date) AS first_event_date
                FROM Player
                LEFT JOIN PlayerEntrant ON Player.id = PlayerEntrant.player_id
                LEFT JOIN EventEntrant ON PlayerEntrant.entrant_id = EventEntrant.id
                LEFT JOIN Event ON EventEntrant.tournament_id = Event.id
                GROUP BY Player.id
                ORDER BY total_events_played DESC
            """)
            return [dict(row) for row in res.fetchall()]

    def get_detailed_player_info(self, player_id: int):
        cur = self.get_conn().cursor()

        # --- Overall stats + match record + games ---
        cur.execute("""
            WITH player_entrants AS (
                SELECT ee.id AS entrant_id,
                       ee.tournament_id,
                       ee.placement,
                       ee.name AS team_name,
                       ev.game AS game,
                       p.tag,
                       p.discord_name,
                       p.startgg_discriminator
                FROM Player p
                JOIN PlayerEntrant pe ON p.id = pe.player_id
                JOIN EventEntrant ee ON pe.entrant_id = ee.id
                JOIN Event ev ON ee.tournament_id = ev.id
                WHERE p.id = ?
            ),
            matches AS (
                SELECT m.id AS match_id,
                       m.winner_entrant_id,
                       mp.entrant_id
                FROM Match m
                JOIN MatchParticipant mp ON m.id = mp.match_id
                WHERE mp.entrant_id IN (SELECT entrant_id FROM player_entrants)
            )
            SELECT
                pe.tag AS tag,
                pe.discord_name AS discord_name,
                pe.startgg_discriminator AS startgg_discriminator,
                COUNT(DISTINCT pe.tournament_id) AS tournaments_played,
                COUNT(DISTINCT CASE WHEN pe.placement = 1 THEN pe.tournament_id END) AS tournaments_won,
                SUM(CASE WHEN m.entrant_id = m.winner_entrant_id THEN 1 ELSE 0 END) AS match_wins,
                SUM(CASE WHEN m.entrant_id != m.winner_entrant_id THEN 1 ELSE 0 END) AS match_losses,
                GROUP_CONCAT(DISTINCT pe.game) AS games_played
            FROM player_entrants pe
            LEFT JOIN matches m ON pe.entrant_id = m.entrant_id;
        """, (player_id,))

        stats_row = cur.fetchone()
        if not stats_row:
            return None

        player_info = dict(stats_row)
        # Convert games_played to a list
        player_info["games_played"] = stats_row["games_played"].split(",") if stats_row["games_played"] else []
        player_info["teams"] = []

        # Team history
        cur.execute("""
            WITH player_entrants AS (
                SELECT ee.id AS entrant_id,
                       ee.tournament_id,
                       ee.placement,
                       ee.name AS team_name,
                       ev.name AS event_name,
                       ev.start_date,
                       ev.id AS tournament_id,
                       ev.game AS game,
                       p.tag
                FROM Player p
                JOIN PlayerEntrant pe ON p.id = pe.player_id
                JOIN EventEntrant ee ON pe.entrant_id = ee.id
                JOIN Event ev ON ee.tournament_id = ev.id
                WHERE p.id = ?
            ),
            roster AS (
                SELECT pe.entrant_id,
                       GROUP_CONCAT(p.id || ':' || p.tag, ',') AS roster
                FROM PlayerEntrant pe
                JOIN Player p ON pe.player_id = p.id
                GROUP BY pe.entrant_id
            ),
            tournament_counts AS (
                SELECT tournament_id, COUNT(*) AS total_entrants
                FROM EventEntrant
                GROUP BY tournament_id
            )
            SELECT 
                ee.id AS team_id,
                ee.name AS team_name,
                ee.placement AS team_placement,
                pe.event_name,
                pe.start_date,
                pe.tournament_id,
                pe.game,
                r.roster AS team_roster,
                tc.total_entrants
            FROM player_entrants pe
            LEFT JOIN EventEntrant ee ON pe.entrant_id = ee.id
            LEFT JOIN roster r ON r.entrant_id = ee.id
            LEFT JOIN tournament_counts tc ON tc.tournament_id = pe.tournament_id
            GROUP BY ee.id
            ORDER BY pe.start_date DESC;
        """, (player_id,))

        team_rows = cur.fetchall()
        for row in team_rows:
            if row["team_id"] is not None:
                roster_list = []
                if row["team_roster"]:
                    for entry in row["team_roster"].split(","):
                        pid, tag = entry.split(":", 1)
                        roster_list.append({"id": int(pid), "tag": tag})

                player_info["teams"].append({
                    "name": row["team_name"],
                    "placement": row["team_placement"],
                    "event_name": row["event_name"],
                    "tournament_id": row["tournament_id"],
                    "start_date": row["start_date"],
                    "total_entrants": row["total_entrants"],
                    "game": row["game"],
                    "roster": roster_list
                })

        return player_info

    def get_player_info_from_discord_id(self, discord_id: int):
        cur = self.get_conn().cursor()
        cur.execute("""
        WITH player_entrants AS (
            SELECT ee.id AS entrant_id,
                   ee.tournament_id,
                   ee.placement,
                   p.tag
            FROM Player p
            JOIN PlayerEntrant pe ON p.id = pe.player_id
            JOIN EventEntrant ee ON pe.entrant_id = ee.id
            WHERE p.discord_id = ?
        ),
        matches AS (
            SELECT m.id AS match_id,
                   m.winner_entrant_id,
                   mp.entrant_id
            FROM Match m
            JOIN MatchParticipant mp ON m.id = mp.match_id
            WHERE mp.entrant_id IN (SELECT entrant_id FROM player_entrants)
        )
        SELECT 
            player_entrants.tag,
            COUNT(DISTINCT tournament_id) AS tournaments_played,
            COUNT(DISTINCT CASE WHEN placement = 1 THEN tournament_id END) AS tournaments_won,
            SUM(CASE WHEN matches.entrant_id = matches.winner_entrant_id THEN 1 ELSE 0 END) AS wins,
            SUM(CASE WHEN matches.entrant_id != matches.winner_entrant_id THEN 1 ELSE 0 END) AS losses
        FROM player_entrants
        LEFT JOIN matches ON player_entrants.entrant_id = matches.entrant_id;
        """, (discord_id,))

        row =  cur.fetchone()
        return dict(row) if row else None

    def get_matches_played_leaderboard(self):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT 
                p.tag,
                COUNT(mp.match_id) AS matches_played
            FROM Player p
            JOIN PlayerEntrant pe ON p.id = pe.player_id
            JOIN EventEntrant ee ON pe.entrant_id = ee.id
            JOIN MatchParticipant mp ON ee.id = mp.entrant_id
            GROUP BY p.id
            ORDER BY matches_played DESC
            LIMIT 10;
        """)
        rows = cur.fetchall()
        return [{"tag": r[0], "matches_played": r[1]} for r in rows]

    def get_matches_won_leaderboard(self):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT 
                p.tag,
                SUM(CASE WHEN mp.entrant_id = m.winner_entrant_id THEN 1 ELSE 0 END) AS matches_won
            FROM Player p
            JOIN PlayerEntrant pe ON p.id = pe.player_id
            JOIN EventEntrant ee ON pe.entrant_id = ee.id
            JOIN MatchParticipant mp ON ee.id = mp.entrant_id
            JOIN "Match" m ON mp.match_id = m.id
            GROUP BY p.id
            ORDER BY matches_won DESC
            LIMIT 10;
        """)
        rows = cur.fetchall()
        return [{"tag": r[0], "matches_won": r[1]} for r in rows]

    def get_tournaments_played_leaderboard(self):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT 
                p.tag,
                COUNT(DISTINCT ee.tournament_id) AS tournaments_played
            FROM Player p
            JOIN PlayerEntrant pe ON p.id = pe.player_id
            JOIN EventEntrant ee ON pe.entrant_id = ee.id
            GROUP BY p.id
            ORDER BY tournaments_played DESC
            LIMIT 10;
        """)
        rows = cur.fetchall()
        return [{"tag": r[0], "tournaments_played": r[1]} for r in rows]

    def get_tournaments_won_leaderboard(self):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT 
                p.tag,
                COUNT(DISTINCT ee.tournament_id) AS tournaments_won
            FROM Player p
            JOIN PlayerEntrant pe ON p.id = pe.player_id
            JOIN EventEntrant ee ON pe.entrant_id = ee.id
            WHERE ee.placement = 1
            GROUP BY p.id
            ORDER BY tournaments_won DESC
            LIMIT 10;
        """)
        rows = cur.fetchall()
        return [{"tag": r[0], "tournaments_won": r[1]} for r in rows]

    def get_top3_finishes(self):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT 
                p.tag,
                SUM(CASE WHEN ee.placement = 1 THEN 1 ELSE 0 END) AS golds,
                SUM(CASE WHEN ee.placement = 2 THEN 1 ELSE 0 END) AS silvers,
                SUM(CASE WHEN ee.placement = 3 THEN 1 ELSE 0 END) AS bronzes,
                COUNT(CASE WHEN ee.placement IN (1,2,3) THEN 1 END) AS total
            FROM Player p
            JOIN PlayerEntrant pe ON p.id = pe.player_id
            JOIN EventEntrant ee ON pe.entrant_id = ee.id
            GROUP BY p.id
            ORDER BY total DESC
            LIMIT 10;
        """)
        rows = cur.fetchall()
        return [{"tag": r[0], "golds": r[1], "silvers": r[2], "bronzes": r[3], "total": r[4]} for r in rows]

    def get_totals(self):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT
                (SELECT COUNT(*) FROM Event) AS total_events,
                (SELECT COUNT(*) FROM Player) AS total_players,
                (SELECT COUNT(*) FROM "Match") AS total_matches;
        """)
        row = cur.fetchone()
        return {
            "total_events": row[0],
            "total_players": row[1],
            "total_matches": row[2]
        } if row else None

    def get_detailed_event_info(self, event_id: int):
        cur = self.get_conn().cursor()
        cur.execute("""
            SELECT
                e.id AS event_id,
                e.name AS event_name,
                e.start_date,
                e.end_date,
                e.game,
                e.startgg_slug,
                e.location,
                ee.id AS team_id,
                ee.name AS name,
                ee.placement AS team_placement,
                GROUP_CONCAT(p.id || ':' || p.tag, ',') AS roster
            FROM Event e
            LEFT JOIN EventEntrant ee ON ee.tournament_id = e.id
            LEFT JOIN PlayerEntrant pe ON pe.entrant_id = ee.id
            LEFT JOIN Player p ON p.id = pe.player_id
            WHERE e.id = ?
            GROUP BY ee.id
            ORDER BY ee.placement ASC
        """, (event_id,))

        rows = cur.fetchall()
        if not rows:
            return None

        # Build the nested structure
        event_info = {
            "event_id": rows[0]["event_id"],
            "name": rows[0]["event_name"],
            "start_date": rows[0]["start_date"],
            "end_date": rows[0]["end_date"],
            "game": rows[0]["game"],
            "startgg_slug": rows[0]["startgg_slug"],
            "location": rows[0]["location"],
            "teams": []
        }

        for row in rows:
            # Parse the roster into a list of dicts {id, tag}
            roster_list = []
            if row["roster"]:
                for entry in row["roster"].split(","):
                    pid, tag = entry.split(":", 1)
                    roster_list.append({"id": int(pid), "tag": tag})

            event_info["teams"].append({
                "team_id": row["team_id"],
                "name": row["name"],
                "placement": row["team_placement"],
                "roster": roster_list
            })

        return event_info





