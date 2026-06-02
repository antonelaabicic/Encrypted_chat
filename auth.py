import bcrypt
from user import User

def register(users, username, password):
    if username in users:
        return False, "User already exists."

    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    users[username] = User(username, password_hash)

    return True, f"{username} has registered."


def login(users, username, password):
    user = users.get(username)

    if not user:
        return False, f"User {username} not found."

    if bcrypt.checkpw(password.encode(), user.password_hash.encode()):
        return True, user

    return False, "Wrong credentials."