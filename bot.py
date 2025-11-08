import discord
from discord import app_commands
from discord.ext import commands
from dotenv import load_dotenv

import json
import os

from src.veto import Veto
from src.utils import display_list, parse_users, get_veto_for_channel

from db.db import Database

if os.path.exists(".env"):
    load_dotenv()
discord_token = os.getenv("DISCORD_TOKEN")
startgg_token = os.getenv("STARTGG_TOKEN")
environment = os.getenv("ENV", "DEV")

guild_id = 1392628719935291442
description = '''Bot for Esports NL'''

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='?', description=description, intents=intents)
# Bot state
bot.active_vetoes = []

db = Database()

@bot.event
async def on_ready():
    print(f"Logged on as {bot.user}!")

    if environment.upper() == "DEV":
        guild = discord.Object(id=guild_id)
        synced = await bot.tree.sync(guild=guild)
        print(f"Synced {len(synced)} command(s) to test guild {guild_id}")
    else:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} global command(s)")

@bot.event
async def on_message(message):
    # Handles map veto (messages starting with -)
    veto = get_veto_for_channel(bot.active_vetoes, message.channel.id)
    if message.content.startswith("-") and veto is not None:
        try:
            map_to_ban = message.content[1:]
            if veto.can_user_ban(int(message.author.id)):
                veto.ban(map_to_ban, int(message.author.id))

                if veto.completed:
                    maps_text = display_list(veto.maps_remaining)
                    bot.active_vetoes.remove(veto)
                    await message.channel.send("Banned map " + map_to_ban.capitalize() +
                                               "\nMap(s) for the match: " + maps_text)
                else:
                    mentions = " ".join(f"<@{user_id}>" for user_id in veto.active_team)
                    await message.channel.send(f"Banned map {map_to_ban.capitalize()}"+
                                               f"\nTeam banning: {mentions}" +
                                               f"\nMaps remaining: {display_list(veto.maps_remaining)}")
        except ValueError as e:
            await message.channel.send(str(e))

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    if isinstance(error, app_commands.MissingAnyRole):
        if interaction.response.is_done():
            await interaction.followup.send("You don’t have the required role to use this command.", ephemeral=True)
        else:
            await interaction.response.send_message("You don’t have the required role to use this command.", ephemeral=True)
    else:
        print(f"Unhandled error: {error}")

@bot.tree.command(name="maplist", description="Lists the current map pool")
async def list_map_pool(interaction: discord.Interaction):
    with open("cfg/bot_config.json", "r") as f:
        data = json.load(f)
    await interaction.response.send_message("**Current map pool:** " + display_list(data["maps"]))

@bot.tree.command(name="mapreplace", description="Replace a map in the pool")
@app_commands.checks.has_any_role("Admin", "Tournament Organizer")
async def replace_map(interaction: discord.Interaction, map_to_replace:str, new_map:str):
    with open("cfg/bot_config.json", "r") as f:
        data = json.load(f)
    maps = data.get("maps", [])
    # Case-insensitive check
    try:
        index = next(i for i, m in enumerate(maps) if m.lower() == map_to_replace.lower())
    except StopIteration:
        await interaction.response.send_message(f"Map `{map_to_replace}` not found in the current pool.", ephemeral=True)
        return
    old_map = maps[index]
    maps[index] = new_map
    data["maps"] = maps
    with open("cfg/bot_config.json", "w") as f:
        json.dump(data, f, indent=4)

    await interaction.response.send_message(
        f"Replaced map `{old_map.capitalize()}` with `{new_map.capitalize()}`.\n**New map pool:** {display_list(maps)}"
    )

@bot.tree.command(name="startveto", description="Starts a veto for the specified number of maps (default 1)")
@app_commands.checks.has_any_role("Admin", "Tournament Organizer")
async def start_veto(interaction: discord.Interaction, team1: str, team2: str, num_maps: int = 1):
    if num_maps != 1 and num_maps != 3 and num_maps != 5:
        await interaction.response.send_message("Invalid veto. Supply 1, 3 or 5 maps.", ephemeral=True)
    with open("cfg/bot_config.json", "r") as f:
        data = json.load(f)
    maps = data["maps"]
    veto = get_veto_for_channel(bot.active_vetoes, interaction.channel.id)
    if veto is not None:
        await interaction.response.send_message("There is already an active veto.", ephemeral=True)
    veto = Veto(int(interaction.channel.id), maps, parse_users(team1), parse_users(team2), num_maps)
    bot.active_vetoes.append(veto)
    mentions_active = " ".join(f"<@{user_id}>" for user_id in veto.active_team)
    mentions_t1 = " ".join(f"<@{user_id}>" for user_id in veto.team1)
    mentions_t2 = " ".join(f"<@{user_id}>" for user_id in veto.team2)
    await interaction.response.send_message(f"**Starting Veto With:** {display_list(maps)}" +
                                            f"\nTeams: {mentions_t1} vs. {mentions_t2}" +
                                            f"\n Team banning: {mentions_active}" +
                                            "\n Type -<map> to ban a map.")

@bot.tree.command(name="cancelveto", description="Cancels the active veto")
@app_commands.checks.has_any_role("Admin", "Tournament Organizer")
async def cancel_veto(interaction: discord.Interaction):
    veto = get_veto_for_channel(bot.active_vetoes, interaction.channel.id)
    if veto is not None:
        bot.active_vetoes.remove(veto)
        await interaction.response.send_message("Cancelled active veto")
    else:
        await interaction.response.send_message("No active veto.")

@bot.tree.command(name="stats", description="Get stats for a player.")
async def get_stats(interaction: discord.Interaction, user: discord.Member = None):
    if user:
        discord_id = user.id
    else:
        discord_id = interaction.user.id

    player_info = db.get_player_info_from_discord_id(discord_id)

    if not player_info:
        await interaction.response.send_message(f"No stats found for <@{discord_id}>.")
        return

    tournaments_played = player_info.get("tournaments_played") or 0
    tournaments_won = player_info.get("tournaments_won") or 0
    wins = player_info.get("wins") or 0
    losses = player_info.get("losses") or 0
    total_matches = wins + losses

    # Fallback for display when user is not in database
    target_user = await bot.fetch_user(discord_id)

    display_name = player_info.get("tag") or str(target_user.name)

    embed = discord.Embed(
        title=f"Stats for {display_name}",
        color=discord.Color.blue()
    )

    embed.add_field(
        name="Tournaments Played",
        value=f"{tournaments_played} (won {tournaments_won})",
        inline=False
    )
    embed.add_field(
        name="Matches Played",
        value=f"{total_matches} ({wins}-{losses})",
        inline=False
    )

    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="leaderboard_matches_played", description="Top players by matches played.")
async def get_matches_played_leaderboard(interaction: discord.Interaction):
    res = db.get_matches_played_leaderboard()
    embed = discord.Embed(
        title="Most Matches Played",
        color=discord.Color.blue()
    )

    header = f"{'Player':<15} | {'Matches':>7}\n" + "-"*25
    rows = "\n".join(f"{player['tag']:<15} | {player['matches_played']:>7}" for player in res)
    table = f"```\n{header}\n{rows}\n```"

    embed.add_field(name="Leaderboard", value=table, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard_matches_won", description="Top players by matches won.")
async def get_matches_won_leaderboard(interaction: discord.Interaction):
    res = db.get_matches_won_leaderboard()
    embed = discord.Embed(
        title="Most Matches Won",
        color=discord.Color.blue()
    )

    header = f"{'Player':<15} | {'Wins':>7}\n" + "-"*25
    rows = "\n".join(f"{player['tag']:<15} | {player['matches_won']:>7}" for player in res)
    table = f"```\n{header}\n{rows}\n```"

    embed.add_field(name="Leaderboard", value=table, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard_tournaments_played", description="Top players by tournaments played.")
async def get_tournaments_played_leaderboard(interaction: discord.Interaction):
    res = db.get_tournaments_played_leaderboard()
    embed = discord.Embed(
        title="Most Tournaments Played",
        color=discord.Color.blue()
    )

    header = f"{'Player':<15} | {'Tournaments':>7}\n" + "-"*25
    rows = "\n".join(f"{player['tag']:<15} | {player['tournaments_played']:>7}" for player in res)
    table = f"```\n{header}\n{rows}\n```"

    embed.add_field(name="Leaderboard", value=table, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard_tournaments_won", description="Top players by tournaments won.")
async def get_tournaments_won_leaderboard(interaction: discord.Interaction):
    res = db.get_tournaments_won_leaderboard()
    embed = discord.Embed(
        title="Most Tournaments Won",
        color=discord.Color.blue()
    )

    header = f"{'Player':<15} | {'Wins':>7}\n" + "-"*25
    rows = "\n".join(f"{player['tag']:<15} | {player['tournaments_won']:>7}" for player in res)
    table = f"```\n{header}\n{rows}\n```"

    embed.add_field(name="Leaderboard", value=table, inline=False)
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="leaderboard_podium", description="Top players by podium finishes.")
async def get_top3_leaderboard(interaction: discord.Interaction):
    res = db.get_top3_finishes()
    embed = discord.Embed(
        title="Podium Finishes Leaderboard",
        color=discord.Color.blue()
    )

    header = f"{'Player':<12} | {'T':>2} | Medals\n" + "-"*25
    rows = "\n".join(
        f"{player['tag']:<12} | {player['total']:>2} | {player['golds']}🥇 {player['silvers']}🥈 {player['bronzes']}🥉"
        for player in res
    )
    table = f"```\n{header}\n{rows}\n```"

    embed.add_field(name="Leaderboard", value=table, inline=False)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="totals", description="Shows total events, players, and matches.")
async def tournament_overview(interaction: discord.Interaction):
    totals = db.get_totals()

    embed = discord.Embed(
        title="Esports NL Totals",
        color=discord.Color.blue(),
        description=(
            f"Esports NL has seen `{totals['total_events']}` events,"
            f" `{totals['total_players']}` unique competitors,"
            f" and `{totals['total_matches']}` matches played since January 2025."
        )
    )

    await interaction.response.send_message(embed=embed)

if __name__ == "__main__":
    bot.run(discord_token)