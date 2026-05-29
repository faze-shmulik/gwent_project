__author__ = "Liam Gornshtein"

import socket
import threading
import json
from tcp_by_size import send_with_size, recv_by_size
from game_board import GameBoard
from usersManager import UsersManager
from cards import CARDS
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

HOST = '0.0.0.0'
PORT = 12312

send_lock = threading.Lock()
game_lock = threading.Lock()
clients = {}
client_keys = {}
game = GameBoard()
decks_received = 0
user_manager = UsersManager("gwent_users.pkl")

print("[SERVER] Generating RSA keys")
SERVER_RSA_KEY = RSA.generate(2048)
SERVER_PUBLIC_KEY = SERVER_RSA_KEY.publickey().export_key()
cipher_rsa = PKCS1_OAEP.new(SERVER_RSA_KEY)
print("[SERVER] RSA keys generated")

def encrypt_msg(plaintext, key):
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(pad(plaintext.encode(), AES.block_size))

def decrypt_msg(ciphertext_with_iv, key):
    iv = ciphertext_with_iv[:16]
    actual_ciphertext = ciphertext_with_iv[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(actual_ciphertext), AES.block_size).decode()

def secure_send(conn, plaintext, key):
    """Encrypts and sends a message."""
    try:
        enc_data = encrypt_msg(plaintext, key)
        with send_lock:
            send_with_size(conn, enc_data)
    except:
        pass

def broadcast(message_string):
    """Encrypts and sends to all connected players."""
    for player_id, conn in list(clients.items()):
        if player_id in client_keys:
            secure_send(conn, message_string, client_keys[player_id])

def send_update():
    state_json = json.dumps(game.get_state_dict())
    broadcast(f"UPDATE|{state_json}")


def handle_client(conn, player_id):
    global game, decks_received
    aes_key = None

    try:
        req = recv_by_size(conn)
        if req == "RSA|REQPUB":
            send_with_size(conn, SERVER_PUBLIC_KEY)
            encrypted_aes_key = recv_by_size(conn, return_type="bytes")
            aes_key = cipher_rsa.decrypt(encrypted_aes_key)
            client_keys[player_id] = aes_key
            print(f"[SERVER] Secure AES connection established with Player {player_id}.")
        else:
            print(f"[SERVER] Player {player_id} failed handshake.")
            return

        while True:
            logged_in = False

            while not logged_in:
                enc_data = recv_by_size(conn, return_type="bytes")
                if not enc_data: return
                data = decrypt_msg(enc_data, aes_key)

                if data.startswith("REQ_AUTH|"):
                    parts = data.split('|', 3)
                    action, username, password = parts[1], parts[2], parts[3]
                    if action == "LOGIN":
                        if user_manager.IsUserExist(username) and user_manager.IsPasswordOK(username, password):
                            secure_send(conn, "RES_AUTH|SUCCESS", aes_key)
                            logged_in = True
                            print(f"[SERVER] Player {player_id} logged in as {username}.")
                        else:
                            secure_send(conn, "RES_AUTH|FAIL|Invalid Username or Password.", aes_key)

                    elif action == "SIGNUP":
                        if user_manager.IsUserExist(username):
                            secure_send(conn, "RES_AUTH|FAIL|Username already taken.", aes_key)
                        else:
                            user_manager.SaveUser(username, password)
                            secure_send(conn, "RES_AUTH|SUCCESS", aes_key)
                            logged_in = True
                            print(f"[SERVER] Player {player_id} created account {username}.")

            secure_send(conn, f"SYS|P{player_id}", aes_key)

            while logged_in:
                enc_data = recv_by_size(conn, return_type="bytes")
                if not enc_data:
                    print(f"[SERVER] Player {player_id} dropped connection.")
                    return

                data = decrypt_msg(enc_data, aes_key)
                parts = data.split('|', 1)
                opcode = parts[0]
                payload = parts[1] if len(parts) > 1 else ""

                if opcode == "REQ_LOGOUT":
                    print(f"[SERVER] Player {player_id} requested logout.")
                    if len(game.players[player_id]["deck"]) > 0 or len(game.players[player_id]["hand"]) > 0:
                        decks_received -= 1
                    game.reset_player(player_id)
                    broadcast(f"MSG|Player {player_id} returned to the login screen.")
                    logged_in = False
                    break

                if opcode == "DECK":
                    with game_lock:
                        if len(game.players[player_id]["deck"]) > 0:
                            secure_send(conn, "ERR|You already readied up", aes_key)
                            continue
                        deck_list = payload.split(',')
                        game.load_deck(player_id, deck_list)
                        decks_received += 1

                        hand_str = ",".join(game.players[player_id]["hand"])
                        secure_send(conn, f"HAND|{hand_str}", aes_key)
                        broadcast(f"MSG|Player {player_id} is ready.")

                        if decks_received == 2:
                            broadcast("MSG|Both players are ready. The game begins!")
                            send_update()

                elif opcode == "REQ_REDRAW":
                    card_name = payload.strip()
                    with game_lock:
                        if game.redraw_card(player_id, card_name):
                            hand_str = ",".join(game.players[player_id]["hand"])
                            secure_send(conn, f"HAND|{hand_str}", aes_key)

                elif opcode == "PLAY":
                    try:
                        play_args = payload.split('|')
                        card_name = play_args[0].strip()
                        row = play_args[1].strip()
                        target_card = play_args[2].strip() if len(play_args) > 2 else None
                        with game_lock:
                            success, msg = game.play_card(player_id, card_name, row, target_card)
                            if success:
                                # Special check for the Medic card. If the logic returns REQ_CHAIN,
                                # we pause the update and ask the client to pick a card from the graveyard.
                                if msg.startswith("REQ_CHAIN|"):
                                    chained_card = msg.split('|')[1]
                                    secure_send(conn, f"REQ_CHAIN|{chained_card}", aes_key)
                                else:
                                    broadcast(f"MSG|{msg}")

                                hand_str = ",".join(game.players[player_id]["hand"])
                                secure_send(conn, f"HAND|{hand_str}", aes_key)
                                send_update()
                            else:
                                secure_send(conn, f"ERR|{msg}", aes_key)


                    except (ValueError, IndexError):
                        secure_send(conn, "ERR|Invalid PLAY format.", aes_key)

                elif opcode == "PASS":
                    with game_lock:
                        success, msg, round_winner = game.pass_turn(player_id)

                        if success:
                            broadcast(f"MSG|{msg}")
                            if round_winner is not None:
                                broadcast(f"RES|{round_winner}")
                            send_update()
                            if game.game_over:
                                import time
                                time.sleep(2)
                                broadcast("SYS|SHUTDOWN")
                        else:
                            secure_send(conn, f"ERR|{msg}", aes_key)

                elif opcode == "EXEC_CHAIN":
                    try:
                        play_args = payload.split('|')
                        medic_card = play_args[0].strip()
                        target_card = play_args[1].strip()
                        row = CARDS[medic_card]["row"]
                        with game_lock:
                            success, msg = game.play_card(player_id, medic_card, row, target_card)
                            if success:
                                if msg.startswith("REQ_CHAIN|"):
                                    chained_card = msg.split('|')[1]
                                    secure_send(conn, f"REQ_CHAIN|{chained_card}", aes_key)
                                else:
                                    broadcast(f"MSG|{msg}")
                                hand_str = ",".join(game.players[player_id]["hand"])
                                secure_send(conn, f"HAND|{hand_str}", aes_key)
                                send_update()
                            else:
                                secure_send(conn, f"ERR|{msg}", aes_key)
                    except (ValueError, IndexError):
                        secure_send(conn, "ERR|Invalid EXEC_CHAIN format.", aes_key)

                elif opcode == "CHAT":
                    other_player = 2 if player_id == 1 else 1
                    if other_player in clients and other_player in client_keys:
                        secure_send(clients[other_player], f"CHAT|{payload}", client_keys[other_player])

    except Exception as e:
        if not game.game_over:
            print(f"[SERVER] Error with Player {player_id}: {e}")
    finally:
        if not game.game_over:
            game.game_over = True
            other_player = 2 if player_id == 1 else 1

            if other_player in clients and other_player in client_keys:
                try:
                    if decks_received == 2:
                        # If a player disconnects mid game, we instantly award
                        # 2 round wins to the remaining player so they get the victory screen
                        secure_send(clients[other_player], "MSG|Opponent disconnected! You win by forfeit.",
                                    client_keys[other_player])
                        secure_send(clients[other_player], f"RES|p{other_player}", client_keys[other_player])
                        secure_send(clients[other_player], f"RES|p{other_player}", client_keys[other_player])

                    else:
                        secure_send(clients[other_player], "MSG|Opponent left the server. Shutting down.",
                                    client_keys[other_player])

                    import time
                    time.sleep(3)
                    secure_send(clients[other_player], "SYS|SHUTDOWN", client_keys[other_player])
                except Exception:
                    pass

        if player_id in clients:
            del clients[player_id]
        if player_id in client_keys:
            del client_keys[player_id]
        try:
            conn.shutdown(socket.SHUT_RDWR)
        except Exception:
            pass
        conn.close()
        if len(clients) == 0:
            print("[SERVER] Lobby is empty. Resetting game board for new match.")
            with game_lock:
                game = GameBoard()
                decks_received = 0


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(2)

    print(f"[SERVER] Secure Gwent Server listening on {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()

        if 1 not in clients:
            p_id = 1
        elif 2 not in clients:
            p_id = 2
        else:
            print(f"[SERVER] Rejected connection from {addr[0]}")
            try:
                conn.close()
            except:
                pass
            continue

        clients[p_id] = conn
        print(f"[SERVER] Connection received from {addr[0]}. Assigning Player {p_id}")

        thread = threading.Thread(target=handle_client, args=(conn, p_id))
        # If we shut down the main server, this thread will automatically die with it instead of turning into a zombie.
        thread.daemon = True
        thread.start()


if __name__ == "__main__":
    main()