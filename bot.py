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
intents.members = True
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
    pass

@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error):
    roles = [role.name for role in interaction.user.roles]
    print(roles, interaction.user.name)
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
    embed = discord.Embed(
        title="Current Map Pool",
        description=display_list(data["maps"]),
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

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
    embed = discord.Embed(
        title="Map Replacement",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="Replacement",
        value=f"`{old_map.capitalize()}` → `{new_map.capitalize()}`",
        inline=False
    )
    embed.add_field(
        name="New Map Pool",
        value=display_list(maps),
        inline=False
    )
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="cancelveto", description="Cancels the active veto")
@app_commands.checks.has_any_role("Admin", "Tournament Organizer")
async def cancel_veto(interaction: discord.Interaction):
    veto = get_veto_for_channel(bot.active_vetoes, interaction.channel.id)
    if veto is not None:
        bot.active_vetoes.remove(veto)
        embed = discord.Embed(
            title="Veto Cancelled",
            description="Cancelled active veto",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message("No active veto.", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a map")
async def ban_map(interaction: discord.Interaction, map_name: str):
    veto = get_veto_for_channel(bot.active_vetoes, interaction.channel.id)
    if veto is not None:
        try:
            if veto.can_user_ban(int(interaction.user.id)):
                veto.ban(map_name, int(interaction.user.id))

                if veto.is_completed():
                    bot.active_vetoes.remove(veto)
                    embed = discord.Embed(
                        title=f"{interaction.user.name} banned **{map_name.capitalize()}**",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Map(s) for the Match",
                        value=display_list(veto.picked_maps),
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed)
                else:
                    mentions = " ".join(f"<@{user_id}>" for user_id in veto.active_team)
                    embed = discord.Embed(
                        title=f"**{interaction.user.name}** banned **{map_name.capitalize()}**",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Team Banning" if veto.is_ban() else "Team Picking",
                        value=mentions,
                        inline=False
                    )
                    embed.add_field(
                        name="Maps for the match",
                        value=display_list(veto.maps_remaining),
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)

@bot.tree.command(name="pick", description="Pick a map")
async def pick_map(interaction: discord.Interaction, map_name: str):
    veto = get_veto_for_channel(bot.active_vetoes, interaction.channel.id)
    if veto is not None:
        try:
            if veto.can_user_ban(int(interaction.user.id)):
                veto.pick(map_name, int(interaction.user.id))

                if veto.is_completed():
                    bot.active_vetoes.remove(veto)
                    embed = discord.Embed(
                        title=f"{interaction.user.name} picked **{map_name.capitalize()}**",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Map(s) for the Match",
                        value=display_list(veto.picked_maps),
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed)
                else:
                    mentions = " ".join(f"<@{user_id}>" for user_id in veto.active_team)
                    embed = discord.Embed(
                        title=f"**{interaction.user.name}** picked **{map_name.capitalize()}**",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="Team Banning" if veto.is_ban() else "Team Picking",
                        value=mentions,
                        inline=False
                    )
                    embed.add_field(
                        name="Maps Remaining",
                        value=display_list(veto.maps_remaining),
                        inline=False
                    )
                    await interaction.response.send_message(embed=embed)
        except ValueError as e:
            await interaction.response.send_message(str(e), ephemeral=True)

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
    embed = discord.Embed(
        title="Veto Started",
        color=discord.Color.green()
    )
    embed.add_field(
        name="Format",
        value=veto.get_format_string(),
        inline = False
    )
    embed.add_field(
        name="Map Pool",
        value=display_list(maps),
        inline=False
    )
    embed.add_field(
        name="Teams",
        value=f"{mentions_t1} vs. {mentions_t2}",
        inline=False
    )
    embed.add_field(
        name= "Team Banning" if veto.is_ban() else "Team Picking",
        value=mentions_active,
        inline=False
    )
    embed.set_footer(text="Use /ban and /pick to select.")
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="stats", description="Get stats for a player.")
async def get_stats(interaction: discord.Interaction, user: discord.Member = None):
    if user:
        discord_id = user.id
    else:
        discord_id = interaction.user.id

    player_info = db.get_player_info_from_discord_id(discord_id)

    if not player_info:
        embed = discord.Embed(
            title="Not Found",
            description=f"No stats found for <@{discord_id}>.",
            color=discord.Color.red()
        )
        await interaction.response.send_message(embed=embed)

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