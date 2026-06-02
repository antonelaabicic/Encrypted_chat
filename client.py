import socket
import threading
from config import HOST, PORT

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

username = ""


def receive():
    buffer = ""

    while True:
        try:
            data = client.recv(1024).decode()

            if not data:
                break

            buffer += data

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)

                msg = line.strip()

                if not msg:
                    continue

                if msg.startswith("MESSAGE"):
                    content = msg[len("MESSAGE "):]
                    print(content)

                elif msg.startswith("ERROR"):
                    print(f"[ERROR] {msg[6:]}")

        except:
            print("[Disconnected]")
            break


def authenticate():
    global username

    print("Welcome to Chat!")
    print("Type 'r' to register or 'l' to login")

    while True:
        choice = input("> ").lower()

        if choice == "r":
            username = input("Username: ")
            password = input("Password: ")

            client.send(
                f"REGISTER {username} {password}\n".encode()
            )

        elif choice == "l":
            username = input("Username: ")
            password = input("Password: ")

            client.send(
                f"LOGIN {username} {password}\n".encode()
            )

        else:
            print("[ERROR] Invalid option")
            continue

        buffer = ""

        while True:
            data = client.recv(1024).decode()

            if not data:
                print("[Disconnected]")
                return

            buffer += data

            if "\n" in buffer:
                response, _ = buffer.split("\n", 1)
                break

        if response == "AUTH_SUCCESS":
            print("\n--- Chat ---\n")

            threading.Thread(target=receive, daemon=True ).start()

            return

        else:
            print(f"[ERROR] {response[6:]}")


def chat():
    while True:
        try:
            msg = input()

            if not msg.strip():
                continue

            client.send(f"SEND {msg}\n".encode())

        except KeyboardInterrupt:
            print("\nExiting...")
            client.close()
            break


authenticate()
chat()