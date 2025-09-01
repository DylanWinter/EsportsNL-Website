import re
from src.veto import Veto
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

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

def format_date(dt: datetime, include_year=True):
    """
    Cross-platform strftime for month + day (no leading zero).
    Uses %-d on Unix, %#d on Windows.
    """
    day_fmt = "%-d"  # Unix (Linux/Mac)
    try:
        return dt.strftime(f"%B {day_fmt}, %Y" if include_year else f"%B {day_fmt}")
    except ValueError:
        day_fmt = "%#d"  # Windows
        return dt.strftime(f"%B {day_fmt}, %Y" if include_year else f"%B {day_fmt}")

def build_date_string(start_time: str, end_time: str):
    nst = ZoneInfo("America/St_Johns")  # NST timezone
    start = datetime.fromisoformat(start_time).astimezone(nst)
    end = datetime.fromisoformat(end_time).astimezone(nst)

    if start.date() == end.date():
        # Same calendar day
        return format_date(start)

    else:
        duration = end - start
        if duration < timedelta(hours=12):
            # Less than 12h → count as one day
            return format_date(start)
        else:
            start_str = format_date(start, include_year=False)
            end_str = format_date(end)
            return f"{start_str} - {end_str}"