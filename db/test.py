from db import Database

db = Database()
res = db.get_all_players()
for row in res:
    print(row["tag"])