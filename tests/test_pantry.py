#from backend.db.pantry_repository import save_pantry, get_pantry

#save_pantry("demo_user", ["rice", "salt", "oil"])

#print("Pantry:", get_pantry("demo_user"))

from backend.db.pantry_repository import get_pantry

print(get_pantry("demo_user"))