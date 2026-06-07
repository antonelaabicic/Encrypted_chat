import socket
import threading
from datetime import datetime

from config.settings import HOST, PORT
from services.auth import register, login
from services.storage import load_users, save_users
from utils.colors import *

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

def send_to_peer(sender, message):
    with lock:
        for client in sessions:
            if client != sender:
                try:
                    client.send((message + "\n").encode())
                except Exception as e:
                    print(f"{RED}{now()} [ERROR] Failed to send to client: {e}{RESET}")

def handle_register(client, username, password):
    ok, res = register(users, username, password)

    if not ok:
        print(f"{RED}{now()} [REGISTER FAIL] {res}{RESET}")
        client.send(f"ERROR {res}\n".encode())
        return False, None

    save_users(users)

    sessions[client] = { "username": username, "pubkey": None, "nonce": None }
    print(f"{GREEN}{now()} [REGISTER] {username}{RESET}")
    client.send("AUTH_SUCCESS\n".encode())

    return True, username

def handle_login(client, username, password):
    ok, res = login(users, username, password)

    if not ok:
        print(f"{RED}{now()} [LOGIN FAIL] {res}{RESET}")
        client.send(f"ERROR {res}\n".encode())
        return False, None

    sessions[client] = { "username": res.username, "pubkey": None, "nonce": None }
    print(f"{GREEN}{now()} [LOGIN] {res.username}{RESET}")
    client.send("AUTH_SUCCESS\n".encode())

    return True, res.username

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
                    
                    if authenticated:
                        for other_client, data in sessions.items():
                            if other_client == client:
                                continue

                            if data["pubkey"] is not None:
                                client.send(f"PEERKEY {data['pubkey']}\n".encode())

                            if data["nonce"] is not None:
                                client.send(f"NONCE {data['nonce']}\n".encode())

                elif command == "LOGIN":
                    if len(parts) < 3:
                        print(f"{RED}{now()} [AUTH ERROR] Malformed LOGIN command.{RESET}")
                        client.send("ERROR Please provide a username and password.\n".encode())
                        continue

                    authenticated, username = handle_login(client, parts[1], parts[2])
                    
                    if authenticated:
                        for other_client, data in sessions.items():
                            if other_client == client:
                                continue

                            if data["pubkey"] is not None:
                                client.send(f"PEERKEY {data['pubkey']}\n".encode())

                            if data["nonce"] is not None:
                                client.send(f"NONCE {data['nonce']}\n".encode())

                elif command == "PUBKEY":
                    if not authenticated:
                        client.send("ERROR Login first.\n".encode())
                        continue

                    sessions[client]["pubkey"] = parts[1]
                    send_to_peer(client, f"PEERKEY {parts[1]}")

                elif command == "NONCE":
                    if not authenticated:
                        client.send("ERROR Login first.\n".encode())
                        continue

                    sessions[client]["nonce"] = parts[1]    
                    send_to_peer(client, f"NONCE {parts[1]}")

                elif command == "SEND":
                    if not authenticated:
                        print(f"{RED}{now()} [UNAUTH SEND]{RESET}")
                        client.send("ERROR Login first.\n".encode())
                        continue

                    payload = line[len("SEND "):]

                    print(f"{now()} [CIPHERTEXT] {payload}")

                    send_to_peer(client, f"MESSAGE {username} {payload}")
                    # send_to_peer(client, f"MESSAGE {username} {payload}") # for testing replay attack

                elif command == "EXIT":
                    print(f"{GRAY}{now()} [DISCONNECT] {username} has left the conversation.{RESET}")
                    send_to_peer(client, f"EXIT {username} has disconnected.")
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

            if len(clients) >= 2:
                client.send("ERROR Chat already full\n".encode())
                client.close()
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