import requests
import os
from datetime import datetime
from zoneinfo import ZoneInfo
from dotenv import load_dotenv

from db.db import Database

def get_data_from_tournament(token: str, slug: str):
    URL = "https://api.start.gg/gql/alpha"

    query = """
    query GetFullTournamentWithUsers($slug: String!) {
      tournament(slug: $slug) {
        id
        name
        venueAddress
        startAt
        endAt
        events {
          id
          name
          videogame {
            id
            name
          }
          entrants {
            nodes {
              id
              name
              participants {
                id
                gamerTag
                user {
                  id
                  discriminator
                  name
                  authorizations {
                    type
                    externalUsername
                    externalId
                  }
                }
              }
            }
          }
          sets {
            nodes {
              id
              round
              winnerId
              slots {
                entrant {
                  id
                }
              }
            }
          }
          standings(query: { perPage: 512, page: 1 }) {
            nodes {
              placement
              entrant {
                id
              }
            }
          }
        }
      }
    }
    """

    response = requests.post(
        URL,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        },
        json={"query": query,
              "variables": {
                  "slug": slug
              }
              }
    )

    events = []

    data = response.json()["data"]
    is_multi_event_tournament = len(data["tournament"]["events"]) > 1
    for event in data["tournament"]["events"]:
        teams = []
        matches = []
        event_dict = {"name": data["tournament"]["name"]}
        # distinguish events
        if is_multi_event_tournament:
            event_dict["name"] += " - " + event["name"]
        start_time = data["tournament"]["startAt"]
        end_time = data["tournament"]["endAt"]
        start_iso = datetime.fromtimestamp(start_time, tz=ZoneInfo("America/St_Johns")).isoformat()
        end_iso = datetime.fromtimestamp(end_time, tz=ZoneInfo("America/St_Johns")).isoformat()
        event_dict["start_time"] = start_iso
        event_dict["end_time"] = end_iso
        event_dict["location"] = data["tournament"]["venueAddress"] if data["tournament"]["venueAddress"] else "Online"
        event_dict["startgg_slug"] = slug.removeprefix("tournament/").strip()

        event_dict["startgg_event_id"] = event["id"]
        event_dict["game"] = event["videogame"]["name"]

        for entrant in event["entrants"]["nodes"]:
            team = {"name": entrant["name"],
                    "startgg_entrant_id": entrant["id"]}
            participants = []

            for participant in entrant["participants"]:
                player = {"startgg_name": participant["gamerTag"],
                          "team_startgg_entrant_id": entrant["id"]}
                # Start.gg allows players without accounts.
                user = participant.get("user")
                if not user:
                    player["discriminator"] = None
                    player["startgg_id"] = None
                    player["discord_name"] = None
                    player["discord_id"] = None
                else:
                    player["discriminator"] = user["discriminator"]
                    player["startgg_id"] = user["id"]
                    if user and user["authorizations"] is not None:
                        for auth in user["authorizations"]:
                            if auth["type"] == "DISCORD":
                                player["discord_name"] = auth.get("externalUsername")
                                player["discord_id"] = auth.get("externalId")

                participants.append(player)

            team["participants"] = participants
            teams.append(team)

        if event["sets"]["nodes"] is not None:
            for s in event["sets"]["nodes"]:
                match_dict = {"startgg_id": s["id"],
                              "round": s["round"],
                              "winner_startgg_entrant_id": s["winnerId"],
                              "participants": []}
                for slot in s["slots"]:
                    entrant = slot.get("entrant")
                    if entrant is not None:
                        match_dict["participants"].append(entrant["id"])
                    else:
                        continue

                matches.append(match_dict)

        # Standings are separate from entrants
        placements = {}
        if "standings" in event and event["standings"].get("nodes"):
            for s in event["standings"]["nodes"]:
                startgg_entrant_id = s["entrant"]["id"]
                placement = s["placement"]
                placements[startgg_entrant_id] = placement
        for team in teams:
            startgg_id = team["startgg_entrant_id"]
            team["placement"] = placements.get(startgg_id)

        event_dict["teams"] = teams
        event_dict["matches"] = matches
        events.append(event_dict)

    return events

if __name__ == "__main__":
    load_dotenv()
    startgg_token = os.getenv("STARTGG_TOKEN")

    db = Database()
    db.clear_all_event_data()

    with open("testslugs.txt") as f:
        line = f.readline().strip()
        while line != "":
            print("Querying tournament: ", line.strip())

            event = get_data_from_tournament(startgg_token, line.strip())
            db.write_event_data(event)

            line = f.readline()