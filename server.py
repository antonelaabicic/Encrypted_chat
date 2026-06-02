import socket
import threading
from datetime import datetime
from config import HOST, PORT
from auth import register, login
from storage import load_users, save_users

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()

print(f"\n=== Server listening on {HOST}:{PORT} ===\n")

clients = []
sessions = {}
users = load_users()

lock = threading.Lock()

def now():
    return datetime.now().strftime("%H:%M:%S")

def broadcast(message, sender=None):
    with lock:
        for c in clients:
            try:
                if c in sessions and c != sender:
                    c.send((message + "\n").encode())
            except:
                pass

def handle_client(client, addr):
    authenticated = False
    username = None

    print(f"{now()} [CONNECT] {addr}")

    buffer = ""

    while True:
        try:
            data = client.recv(1024).decode()

            if not data:
                break

            buffer += data

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                line = line.strip()

                if not line:
                    continue

                parts = line.split(" ", 2)
                command = parts[0]

                if command == "REGISTER":
                    username_input = parts[1]
                    password_input = parts[2]

                    ok, res = register(users, username_input, password_input)

                    if ok:
                        save_users(users)

                        authenticated = True
                        username = username_input
                        sessions[client] = username

                        print(f"{now()} [REGISTER+LOGIN] {username}")

                        client.send("AUTH_SUCCESS\n".encode())
                    else:
                        client.send(f"ERROR {res}\n".encode())

                elif command == "LOGIN":
                    if len(parts) < 3:
                        client.send(
                            "ERROR Usage: LOGIN username password\n".encode()
                        )
                        continue

                    username_input = parts[1]
                    password_input = parts[2]

                    ok, res = login(users, username_input, password_input)

                    if ok:
                        authenticated = True
                        username = res.username
                        sessions[client] = username

                        print(f"{now()} [LOGIN] {username}")

                        client.send("AUTH_SUCCESS\n".encode())
                    else:
                        client.send(f"ERROR {res}\n".encode())

                elif command == "SEND":
                    if not authenticated:
                        client.send("ERROR Login first\n".encode())
                        continue

                    text = line[len("SEND "):]
                    full_msg = f"MESSAGE {username}: {text}"
                    print(f"{now()} [MSG] {username}: {text}")
                    broadcast(full_msg, sender=client)

                else:
                    client.send("ERROR Unknown command\n".encode())

        except Exception as e:
            print(f"{now()} [ERROR] {e}")
            break

    with lock:
        if client in clients:
            clients.remove(client)

        if client in sessions:
            print(f"{now()} [DISCONNECT] {sessions[client]}")
            del sessions[client]

    client.close()

def receive():
    while True:
        client, addr = server.accept()

        with lock:
            clients.append(client)

        threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()

receive()