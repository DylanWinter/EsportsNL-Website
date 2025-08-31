import re
from src.veto import Veto

def display_list(data: list[str]):
    """ Correctly formats a list of maps """
    return ", ".join(item.capitalize() for item in data)

def parse_users(user_str: str) -> list[int]:
    """Parses a string of Discord mentions and returns a list of user IDs as integers."""
    if not user_str:
        return []

    # Regex to match both <@123> and <@!123>
    pattern = r"<@!?(?P<id>\d+)>"

    # Find all matches and convert to integers
    return [int(match.group("id")) for match in re.finditer(pattern, user_str)]

def get_veto_for_channel(vetoes: list[Veto], channel_id: int):
    for veto in vetoes:
        if veto.channel == channel_id:
            return veto
    return None