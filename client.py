import socket
import threading
import os

from config.settings import HOST, PORT
from utils.colors import *

from encryption.diffie import generate_keypair, compute_shared
from encryption.hkdf import derive_key
from encryption.aes import encrypt, decrypt

from Crypto.PublicKey import ECC
from Crypto.Random import get_random_bytes

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client.connect((HOST, PORT))

username = ""

private_key = None
shared_secret = None
shared_key = None

my_nonce = None
peer_nonce = None

send_counter = 0
recv_counter = 0

def get_credentials():
    username = input("Username: ")
    password = input("Password: ")
    return username, password

def try_derive_key():
    global shared_key

    if shared_secret is None or my_nonce is None or peer_nonce is None:
        return

    if shared_key is not None:
        return

    salt = min(my_nonce, peer_nonce) + max(my_nonce, peer_nonce)
    shared_key = derive_key(shared_secret, salt)

    print(f"AES Key: {shared_key.hex()}\n")

def receive():
    global shared_secret
    global peer_nonce
    global recv_counter

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

                if msg.startswith("PEERKEY"):
                    peer = ECC.import_key(bytes.fromhex(msg.split(" ", 1)[1]))
                    shared_secret = compute_shared(private_key, peer)
                    print("Shared Secret:", shared_secret.hex())
                    try_derive_key()

                elif msg.startswith("NONCE"):
                    peer_nonce = bytes.fromhex(msg.split(" ", 1)[1])
                    try_derive_key()

                elif msg.startswith("MESSAGE"):
                    if shared_key is None:
                        print("Received message before secure channel established.")
                        continue

                    _, sender, payload_hex = msg.split(" ", 2)
                    payload = bytes.fromhex(payload_hex)
                    
                    try:
                        plaintext, recv_counter = decrypt(shared_key, payload, recv_counter)
                        
                        print(f"{BLUE}{sender}:{RESET} {plaintext}")
                        print(f"{BLUE}Counter:{RESET} {recv_counter}\n")

                    except Exception as e:
                        print(f"[DECRYPT ERROR] {e}")

                elif msg.startswith("ERROR"):
                    print(msg[6:])

                elif msg.startswith("EXIT"):
                    print(f"{msg[5:]}\n")

        except (ConnectionResetError, ConnectionAbortedError):
            print("Server is shutting down...")
            client.close()
            os._exit(0)
        
        except Exception as e:
            print(f"[RECEIVE ERROR] {e}")
            client.close()
            os._exit(0)

def authenticate():
    global username
    global private_key
    global my_nonce

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
            print("Invalid option.")
            continue

        buffer = ""

        while True:
            data = client.recv(1024).decode()

            if not data:
                print("Server unavailable.")
                return

            buffer += data
            if "\n" in buffer:
                response, _ = buffer.split("\n", 1)
                break

        if response == "AUTH_SUCCESS":
            print(f"\n=== CHAT ===\n")
            private_key, public_key = generate_keypair()
            my_nonce = get_random_bytes(16)

            threading.Thread(target=receive, daemon=True).start()
            
            client.send(f"PUBKEY {public_key.export_key(format='DER').hex()}\n".encode())
            client.send(f"NONCE {my_nonce.hex()}\n".encode())

            return

        else:
            print(response[6:])

def chat():
    global send_counter
    exit_commands = ["q", "quit"]
    
    while True:

        try:
            msg = input()

            if not msg.strip():
                continue

            if msg.lower() in exit_commands:
                client.send("EXIT\n".encode())
                print("\nDisconnecting...")
                client.close()
                os._exit(0)

            if shared_key is None:
                print("Waiting for secure channel...")
                continue

            send_counter += 1
            payload = encrypt(shared_key, msg, send_counter)

            print(f"{PINK}Counter:{RESET} {send_counter}")
            print(f"{PINK}Encrypted:{RESET} {payload.hex()}")
            print()

            client.send(f"SEND {payload.hex()}\n".encode())

        except KeyboardInterrupt:
            print("\nExiting...")
            client.close()
            os._exit(0)

authenticate()
chat()