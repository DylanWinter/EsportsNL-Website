from enum import Enum

class State:
    Ban = 1
    Pick = 2

BO1 = []
BO3 = [State.Ban, State.Ban, State.Pick, State.Pick, State.Ban, State.Ban]
BO5 = [State.Ban, State.Ban, State.Pick, State.Pick, State.Pick, State.Pick]

class Veto:
    def __init__(self, channel:int, maps: list[str], team1: list[int], team2: list[int], num_to_select = 1):
        self.maps_remaining = maps.copy()
        self.banned_maps = []
        self.picked_maps = []
        self.channel = channel

        # Num to select must be restricted to 1, 3 or 5
        self.num_to_select = num_to_select
        self.completed = False
        self.selections_made = 0
        if num_to_select == 1:
            self.order = BO1
        elif num_to_select == 3:
            self.order = BO3
        elif num_to_select == 5:
            self.order = BO5

        self.team1 = [int(p) for p in team1]
        self.team2 = [int(p) for p in team2]
        self.active_team = self.team1

    def ban(self, map_to_ban: str, user_id: int):
        """ Bans a map, updates the active team """
        if self.get_current_state() != State.Ban:
            raise ValueError("You must pick a map")

        if map_to_ban.lower() in self.maps_remaining:
            self.maps_remaining.remove(map_to_ban.lower())
            self.banned_maps.append(map_to_ban.lower())
            self.advance_state()

        elif map_to_ban.lower() in self.banned_maps:
            raise ValueError("Map already banned: "+ map_to_ban)
        elif map_to_ban.lower() in self.picked_maps:
            raise ValueError("Map already picked: " + map_to_ban)
        else:
            raise ValueError("Map not in maps list: " + map_to_ban)

    def pick(self, map_to_pick: str, user_id: int):
        """ Picks a map, updates the active team """
        if self.get_current_state() != State.Pick:
            raise ValueError("You must ban a map")

        if map_to_pick.lower() in self.maps_remaining:
            self.maps_remaining.remove(map_to_pick.lower())
            self.picked_maps.append(map_to_pick.lower())
            self.advance_state()

        elif map_to_pick.lower() in self.picked_maps:
            raise ValueError("Map already picked: " + map_to_pick)
        elif map_to_pick.lower() in self.banned_maps:
            raise ValueError("Map is banned: " + map_to_pick)
        else:
            raise ValueError("Map not in maps list: " + map_to_pick)

    def can_user_ban(self, user_id: int):
        """ Returns true if a user is in the active team"""
        return int(user_id) in self.active_team

    def is_completed(self):
        """ Returns whether the veto has ended """
        return self.completed

    def get_current_state(self):
        """ Gets the current state (Ban, Pick or Completed). Defaults to ban. """
        if self.selections_made >= len(self.order):
            return State.Ban
        return self.order[self.selections_made]

    def advance_state(self):
        """ Checks whether the veto has ended, swaps the team and increases the selection index """
        if len(self.maps_remaining) == 1:
            self.picked_maps.append(self.maps_remaining[0])
            self.completed = True
        self.selections_made += 1
        # Swap team
        if self.active_team == self.team2:
            self.active_team = self.team1
        else:
            self.active_team = self.team2

    def is_ban(self):
        return self.get_current_state() == State.Ban

    def is_pick(self):
        return self.get_current_state() == State.Pick

    def get_format_string(self):
        if self.num_to_select == 1:
            return "Best-of-1 | Teams alternate bans until one map remains."
        elif self.num_to_select == 3:
            return "Best-of-3 | Ban, Ban, Pick, Pick, Ban, Ban, Decider."
        elif self.num_to_select == 5:
            return "Best-of-5 | Ban, Ban, Pick, Pick, Pick, Pick, Decider."
        else:
            return "Something went wrong."
