import socket
import threading
from config.settings import HOST, PORT

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

username = ""

def message_output(msg, cmd):
    print(msg[len(cmd):])
    
def get_credentials():
    username = input("Username: ")
    password = input("Password: ")
    return username, password

def receive():
    buffer = ""

    while True:
        try:
            data = client.recv(1024).decode()

            if not data:
                print("Server disconnected.")
                break

            buffer += data
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                msg = line.strip()

                if not msg:
                    continue

                if msg.startswith("MESSAGE"):
                    message_output(msg, "MESSAGE ")

                elif msg.startswith("ERROR"):
                    message_output(msg, "ERROR ")

                elif msg.startswith("EXIT"):
                    print()
                    message_output(msg, "EXIT ")

        except:
            break

def authenticate():
    global username

    print("Welcome to Chat!")
    print("Type 'r' to register or 'l' to login")

    while True:
        choice = input("> ").lower()

        if choice == "r":
            username, password = get_credentials()
            client.send(f"REGISTER {username} {password}\n".encode())

        elif choice == "l":
            username, password = get_credentials()
            client.send(f"LOGIN {username} {password}\n".encode())

        else:
            print("Invalid option. Please try again.")
            continue

        buffer = ""
        while True:
            data = client.recv(1024).decode()

            if not data:
                print("Server not available.")
                return

            buffer += data
            if "\n" in buffer:
                response, _ = buffer.split("\n", 1)
                break

        if response == "AUTH_SUCCESS":
            print("\n--- Chat ---\n")
            threading.Thread(target=receive, daemon=True).start()
            return
        else:
            print(response[6:])

def chat():
    exit_commands = ["q", "quit", "exit"]
    while True:
        try:
            msg = input()

            if not msg.strip():
                continue
                
            if msg.lower() in exit_commands:
                client.send("EXIT\n".encode())
                print("\nDisconnecting...")
                client.close()
                break
                
            client.send(f"SEND {msg}\n".encode())

        except KeyboardInterrupt:
            print("\nExiting...")
            client.close()
            break

authenticate()
chat()