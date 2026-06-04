import socket
import threading
from datetime import datetime
from config import HOST, PORT
from auth import register, login
from storage import load_users, save_users
from colors import *

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen()
server.settimeout(1)

print(f"{GRAY}\n=== Server listening on {HOST}:{PORT} ===\n{RESET}")

clients = []
sessions = {}
users = load_users()

lock = threading.Lock()

def now():
    return datetime.now().strftime("%H:%M:%S")

def broadcast(message, sender=None):
    with lock:
        for c in clients[:]:
            try:
                if c in sessions and c != sender:
                    c.send((message + "\n").encode())
            except:
                clients.remove(c)

def handle_register(client, username, password):
    ok, res = register(users, username, password)

    if not ok:
        print(f"{RED}{now()} [REGISTER FAIL] {res}{RESET}")
        client.send(f"ERROR {res}\n".encode())
        return False, None

    save_users(users)
    sessions[client] = username
    print(f"{GREEN}{now()} [REGISTER] {username}{RESET}")
    client.send("AUTH_SUCCESS\n".encode())

    return True, username


def handle_login(client, username, password):
    ok, res = login(users, username, password)

    if not ok:
        print(f"{RED}{now()} [LOGIN FAIL] {res}{RESET}")
        client.send(f"ERROR {res}\n".encode())
        return False, None

    sessions[client] = res.username
    print(f"{GREEN}{now()} [LOGIN] {res.username}{RESET}")
    client.send("AUTH_SUCCESS\n".encode())
    
    return True, res.username


def handle_send(client, username, authenticated, line):
    if not authenticated:
        print(f"{RED}{now()} [UNAUTH SEND]{RESET}")
        client.send("ERROR Login first\n".encode())
        return

    text = line[len("SEND "):]
    full_msg = f"MESSAGE {username}: {text}"
    print(f"{now()} [MSG] {username}: {text}")
    broadcast(full_msg, sender=client)


def handle_client(client, addr):
    authenticated = False
    username = None

    print(f"{GRAY}{now()} [CONNECT] {addr}{RESET}")

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
                    if len(parts) < 3:
                        print(f"{RED}{now()} [AUTH ERROR] Malformed REGISTER command.{RESET}")
                        client.send("ERROR Please provide a username and password.\n".encode())
                        continue
                    authenticated, username = handle_register(client, parts[1], parts[2])

                elif command == "LOGIN":
                    if len(parts) < 3:
                        print(f"{RED}{now()} [AUTH ERROR] Malformed LOGIN command.{RESET}")
                        client.send("ERROR Please provide a username and password.\n".encode())
                        continue
                    authenticated, username = handle_login(client, parts[1], parts[2])

                elif command == "SEND":
                    handle_send(client, username, authenticated, line)
                    
                elif command == "EXIT":
                    print(f"{GRAY}{now()} [DISCONNECT] {username} has left the conversation.{RESET}")
                    broadcast(f"MESSAGE {username} has disconnected.", sender=client)
                    break

                else:
                    print(f"{RED}{now()} [INVALID CMD] Invalid command: {line}{RESET}")
                    client.send("ERROR Unknown command.\n".encode())

        except Exception:
            break

    with lock:
        if client in sessions:
            del sessions[client]
            
        if client in clients:
            clients.remove(client)

    client.close()

def receive():
    try:
        while True:
            try:
                client, addr = server.accept()
            except socket.timeout:
                continue  

            with lock:
                clients.append(client)

            threading.Thread(target=handle_client, args=(client, addr), daemon=True).start()

    except KeyboardInterrupt:
        print(f"\n{GRAY}{now()} [SHUTDOWN] Server stopping...{RESET}")

        server.close()

        with lock:
            for c in clients:
                try:
                    c.close()
                except:
                    pass

receive()