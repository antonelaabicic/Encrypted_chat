import json

from psutil import users
from models.user import User

def load_users():
    try:
        with open("data/users.json", "r") as f:
            data = json.load(f)
            users = {}

            for username, password_hash in data.items():
                users[username] = User(username, password_hash)

            return users
    except:
        return {}

def save_users(users):
    data = {}

    for username, user in users.items():
        data[username] = user.password_hash

    with open("data/users.json", "w") as f:
        json.dump(data, f, indent=4)