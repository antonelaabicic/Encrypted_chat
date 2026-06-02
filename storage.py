import json
from user import User

def load_users():
    try:
        with open("users.json", "r") as f:
            data = json.load(f)
            users = {}

            for username, u in data.items():
                users[username] = User(username, u["password_hash"])

            return users
    except:
        return {}


def save_users(users):
    data = {}

    for username, user in users.items():
        data[username] = { "password_hash": user.password_hash }

    with open("users.json", "w") as f:
        json.dump(data, f, indent=4)