__author__ = "Liam Gornshtein"

import socket
import threading
import time
import json
import pygame
from tcp_by_size import send_with_size, recv_by_size
from cards import CARDS
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import sys

HOST = '127.0.0.1'
PORT = 12312
# if IP entered from cmd then it's the target server
if len(sys.argv) > 1:
    HOST = sys.argv[1]
print(f"[CLIENT] Targeting server at {HOST}:{PORT}")

is_running = True
is_muted = False
current_track_index = 0
playlist = ["assets/gwent_music1.mp3", "assets/gwent_music2.mp3", "assets/gwent_music3.mp3", "assets/gwent_music4.mp3"]
# Creates a custom pygame event ID. We tell pygame to fire this event when a song ends so we know to play the next one.
MUSIC_END = pygame.USEREVENT + 1
my_rounds_won = 0
opp_rounds_won = 0
game_over_text = ""
app_state = "LOGIN"
aes_key = None
login_user_text = ""
login_pass_text = ""
active_input = "USER"
login_status_msg = "Enter credentials to connect."

my_player_id = None

my_deck_selection = ["Geralt", "Ciri", "Vesemir", "Triss", "Yennefer", "Catapult", "Trebuchet", "Zoltan", "Keira",
                     "Ballista", "Vernon Roche", "John Natalis"]
my_hand = []

current_board_state = None
sys_message = "Waiting for server..."
WIDTH, HEIGHT = 1000, 800

in_redraw_phase = False
redraws_done = 0
WIDTH, HEIGHT = 1000, 800
CARD_WIDTH, CARD_HEIGHT = 80, 120
card_images = {}

show_chat = False
i_am_ready = False
selected_horn = False
deck_scroll_y = 0
pool_scroll_y = 0
chat_history = []
chat_input_text = ""
chat_active = False

def encrypt_msg(plaintext, key):
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return iv + cipher.encrypt(pad(plaintext.encode(), AES.block_size))


def decrypt_msg(ciphertext_with_iv, key):
    iv = ciphertext_with_iv[:16]
    actual_ciphertext = ciphertext_with_iv[16:]
    cipher = AES.new(key, AES.MODE_CBC, iv)
    return unpad(cipher.decrypt(actual_ciphertext), AES.block_size).decode()


def secure_send(sock, plaintext):
    """Encrypts and sends a message."""
    try:
        enc_data = encrypt_msg(plaintext, aes_key)
        send_with_size(sock, enc_data)
    except:
        pass

def get_card_image(name, font):
    # don't load the image if we already loaded it before.
    if name not in card_images:
        try:
            img = pygame.image.load(f"assets/{name}.png").convert_alpha()
            img = pygame.transform.scale(img, (CARD_WIDTH, CARD_HEIGHT))
            card_images[name] = img
        except FileNotFoundError:
            try:
                img = pygame.image.load(f"assets/{name}.jpg").convert_alpha()
                img = pygame.transform.scale(img, (CARD_WIDTH, CARD_HEIGHT))
                card_images[name] = img
            except FileNotFoundError:
                # draw a grey box with the card's name if the file is missing
                surf = pygame.Surface((CARD_WIDTH, CARD_HEIGHT))
                surf.fill((180, 180, 180))
                pygame.draw.rect(surf, (0, 0, 0), surf.get_rect(), 3)
                text = font.render(name[:7], True, (0, 0, 0))
                surf.blit(text, (5, CARD_HEIGHT // 2))
                card_images[name] = surf
    return card_images[name]


def draw_login_screen(screen, fonts):
    # Background
    screen.fill((40, 40, 40))

    # Title and Status Text
    title = fonts['title'].render("GWENT: SECURE LOGIN", True, (255, 215, 0))
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 150))

    status = fonts['main'].render(login_status_msg, True, (200, 200, 200))
    screen.blit(status, (WIDTH // 2 - status.get_width() // 2, 220))

    # Username Input Box
    user_rect = pygame.Rect(WIDTH // 2 - 150, 300, 300, 40)
    user_color = (100, 100, 100) if active_input == "USER" else (50, 50, 50)
    pygame.draw.rect(screen, user_color, user_rect, border_radius=5)

    # Blinking cursor
    user_display = login_user_text + ("|" if active_input == "USER" and time.time() % 1 > 0.5 else "")
    u_surf = fonts['main'].render("User: " + user_display, True, (255, 255, 255))
    screen.blit(u_surf, (user_rect.x + 10, user_rect.y + 5))

    # Password Input Box
    pass_rect = pygame.Rect(WIDTH // 2 - 150, 360, 300, 40)
    pass_color = (100, 100, 100) if active_input == "PASS" else (50, 50, 50)
    pygame.draw.rect(screen, pass_color, pass_rect, border_radius=5)

    # Asterisks for password hiding
    pass_display = ("*" * len(login_pass_text)) + ("|" if active_input == "PASS" and time.time() % 1 > 0.5 else "")
    p_surf = fonts['main'].render("Pass: " + pass_display, True, (255, 255, 255))
    screen.blit(p_surf, (pass_rect.x + 10, pass_rect.y + 5))

    can_submit = len(login_user_text.strip()) > 0 and len(login_pass_text.strip()) > 0

    # Login Button
    login_btn = pygame.Rect(WIDTH // 2 - 150, 430, 140, 45)
    log_color = (50, 150, 255) if can_submit else (100, 100, 100)
    pygame.draw.rect(screen, log_color, login_btn, border_radius=5)
    l_txt = fonts['main'].render("Login", True, (255, 255, 255))
    screen.blit(l_txt, (login_btn.x + 40, login_btn.y + 8))

    # Signup Button
    signup_btn = pygame.Rect(WIDTH // 2 + 10, 430, 140, 45)
    sig_color = (50, 200, 100) if can_submit else (100, 100, 100)
    pygame.draw.rect(screen, sig_color, signup_btn, border_radius=5)
    s_txt = fonts['main'].render("Sign Up", True, (255, 255, 255))
    screen.blit(s_txt, (signup_btn.x + 30, signup_btn.y + 8))

    return user_rect, pass_rect, login_btn, signup_btn


def draw_chat_ui(screen, fonts):
    # Main chat background box
    chat_bg = pygame.Rect(WIDTH - 350, 70, 330, 400)
    pygame.draw.rect(screen, (30, 30, 30), chat_bg, border_radius=10)
    pygame.draw.rect(screen, (200, 200, 200), chat_bg, 3, border_radius=10)

    # Text Input Box at the bottom
    input_rect = pygame.Rect(chat_bg.x + 10, chat_bg.bottom - 40, chat_bg.width - 20, 30)
    input_color = (100, 100, 100) if chat_active else (50, 50, 50)
    pygame.draw.rect(screen, input_color, input_rect, border_radius=5)

    # Blinking cursor
    chat_font = pygame.font.SysFont('Arial', 16)
    display_text = chat_input_text + ("|" if chat_active and time.time() % 1 > 0.5 else "")
    input_surface = chat_font.render(display_text, True, (255, 255, 255))
    screen.blit(input_surface, (input_rect.x + 5, input_rect.y + 5))

    y_offset = input_rect.y - 25

    # Grab only the last 12 messages, and reverse them so we draw from bottom to top.
    for msg in reversed(chat_history[-12:]):
        color = (150, 200, 255) if msg.startswith("You") else (200, 200, 200)
        txt = chat_font.render(msg, True, color)
        screen.blit(txt, (chat_bg.x + 10, y_offset))
        y_offset -= 25  # Move up 25 pixels for the next older message

    return input_rect


def draw_board(screen, fonts):
    screen.fill((101, 67, 33))

    # Chat Button
    chat_btn_rect = pygame.Rect(WIDTH - 120, 20, 100, 40)
    pygame.draw.rect(screen, (50, 50, 50), chat_btn_rect, border_radius=5)
    chat_lbl = fonts['main'].render("CHAT", True, (255, 255, 255))
    screen.blit(chat_lbl, (chat_btn_rect.x + 20, chat_btn_rect.y + 5))

    # Mute Button
    global is_muted
    mute_btn_rect = pygame.Rect(WIDTH - 120, 70, 100, 40)
    btn_color = (100, 100, 100) if is_muted else (50, 150, 50)
    pygame.draw.rect(screen, btn_color, mute_btn_rect, border_radius=5)
    mute_text = "UNMUTE" if is_muted else "MUTE"
    mute_lbl = fonts['main'].render(mute_text, True, (255, 255, 255))
    text_x = mute_btn_rect.centerx - mute_lbl.get_width() // 2
    text_y = mute_btn_rect.centery - mute_lbl.get_height() // 2
    screen.blit(mute_lbl, (text_x, text_y))

    # Deck Builder
    if not current_board_state:
        # Logout Button
        logout_btn_rect = pygame.Rect(WIDTH - 240, 20, 100, 40)
        pygame.draw.rect(screen, (180, 50, 50), logout_btn_rect, border_radius=5)
        logout_lbl = fonts['main'].render("LOGOUT", True, (255, 255, 255))
        screen.blit(logout_lbl, (logout_btn_rect.x + 10, logout_btn_rect.y + 5))

        id_text = fonts['main'].render(sys_message, True, (200, 200, 200))
        screen.blit(id_text, (20, 20))

        # Center Divider Line
        pygame.draw.line(screen, (150, 100, 50), (WIDTH // 2, 80), (WIDTH // 2, HEIGHT - 100), 4)

        deck_title = fonts['title'].render(f"Your Deck ({len(my_deck_selection)} | Min: 12)", True, (255, 215, 0))
        screen.blit(deck_title, (WIDTH // 4 - deck_title.get_width() // 2, 80))

        pool_title = fonts['title'].render("Card Pool", True, (200, 200, 200))
        screen.blit(pool_title, (3 * WIDTH // 4 - pool_title.get_width() // 2, 80))

        available_cards = []
        for card_name, card_data in CARDS.items():
            limit = card_data.get("limit", 1)
            count_in_deck = my_deck_selection.count(card_name)

            for _ in range(limit - count_in_deck):
                available_cards.append(card_name)

        # Clipping window for scrolling menus
        screen.set_clip(pygame.Rect(0, 140, WIDTH, HEIGHT - 240))

        deck_rects = []
        for i, card in enumerate(my_deck_selection):
            x = 30 + (i % 5) * 90
            y = 150 + (i // 5) * 130 - deck_scroll_y
            screen.blit(get_card_image(card, fonts['main']), (x, y))
            deck_rects.append((pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT), card))

        pool_rects = []
        for i, card in enumerate(available_cards):
            x = 530 + (i % 5) * 90
            y = 150 + (i // 5) * 130 - pool_scroll_y
            screen.blit(get_card_image(card, fonts['main']), (x, y))
            pool_rects.append((pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT), card))

        screen.set_clip(None)

        # Ready Button
        ready_rect = None
        if not i_am_ready:
            if len(my_deck_selection) >= 12:
                ready_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT - 80, 200, 50)
                pygame.draw.rect(screen, (255, 215, 0), ready_rect, border_radius=10)
                btn_text = fonts['main'].render("Ready Up!", True, (0, 0, 0))
                screen.blit(btn_text, (ready_rect.x + 45, ready_rect.y + 10))
            else:
                warn_text = fonts['main'].render("You need at least 12 cards!", True, (255, 100, 100))
                screen.blit(warn_text, (WIDTH // 2 - warn_text.get_width() // 2, HEIGHT - 70))
        else:
            wait_text = fonts['title'].render("Waiting for opponent...", True, (200, 200, 200))
            screen.blit(wait_text, (WIDTH // 2 - wait_text.get_width() // 2, HEIGHT - 70))

        chat_input_rect = draw_chat_ui(screen, fonts) if show_chat else None
        return ready_rect, None, [], chat_btn_rect, chat_input_rect, deck_rects, pool_rects, None, [], [], None

    if my_player_id == "p2":
        my_board = current_board_state['p2_board']
        opp_board = current_board_state['p1_board']
        my_score = current_board_state['p2_score']
        opp_score = current_board_state['p1_score']
        weather_zone = current_board_state.get('weather_zone', [])
        my_horns = current_board_state.get('p2_horns', [])
        opp_horns = current_board_state.get('p1_horns', [])
    else:
        my_board = current_board_state['p1_board']
        opp_board = current_board_state['p2_board']
        my_score = current_board_state['p1_score']
        opp_score = current_board_state['p2_score']
        weather_zone = current_board_state.get('weather_zone', [])
        my_horns = current_board_state.get('p1_horns', [])
        opp_horns = current_board_state.get('p2_horns', [])

    row_width, row_height = 600, 80
    start_x = 200
    brown = (139, 69, 19)

    # Draw Game Board Rows
    pygame.draw.rect(screen, brown, (start_x, 50, row_width, row_height), border_radius=5)
    pygame.draw.rect(screen, brown, (start_x, 140, row_width, row_height), border_radius=5)
    pygame.draw.rect(screen, brown, (start_x, 230, row_width, row_height), border_radius=5)
    pygame.draw.rect(screen, brown, (start_x, 350, row_width, row_height), border_radius=5)
    pygame.draw.rect(screen, brown, (start_x, 440, row_width, row_height), border_radius=5)
    pygame.draw.rect(screen, brown, (start_x, 530, row_width, row_height), border_radius=5)

    if selected_horn:
        gold = (255, 215, 0)
        pygame.draw.rect(screen, gold, (start_x, 350, row_width, row_height), 4, border_radius=5)
        pygame.draw.rect(screen, gold, (start_x, 440, row_width, row_height), 4, border_radius=5)
        pygame.draw.rect(screen, gold, (start_x, 530, row_width, row_height), 4, border_radius=5)

    boost_color = (180, 140, 0)

    # Draw Boost Lines
    if check_boost(opp_board, 'siege'): pygame.draw.line(screen, boost_color, (start_x + 5, 50 + row_height - 3),
                                                         (start_x + row_width - 5, 50 + row_height - 3), 4)
    if check_boost(opp_board, 'ranged'): pygame.draw.line(screen, boost_color, (start_x + 5, 140 + row_height - 3),
                                                          (start_x + row_width - 5, 140 + row_height - 3), 4)
    if check_boost(opp_board, 'melee'): pygame.draw.line(screen, boost_color, (start_x + 5, 230 + row_height - 3),
                                                         (start_x + row_width - 5, 230 + row_height - 3), 4)
    if check_boost(my_board, 'melee'): pygame.draw.line(screen, boost_color, (start_x + 5, 350 + row_height - 3),
                                                        (start_x + row_width - 5, 350 + row_height - 3), 4)
    if check_boost(my_board, 'ranged'): pygame.draw.line(screen, boost_color, (start_x + 5, 440 + row_height - 3),
                                                         (start_x + row_width - 5, 440 + row_height - 3), 4)
    if check_boost(my_board, 'siege'): pygame.draw.line(screen, boost_color, (start_x + 5, 530 + row_height - 3),
                                                        (start_x + row_width - 5, 530 + row_height - 3), 4)

    row_font = pygame.font.SysFont('Arial', 18, bold=True)

    frost_active = "Biting Frost" in weather_zone
    fog_active = "Impenetrable Fog" in weather_zone
    rain_active = "Torrential Rain" in weather_zone

    # Draw Row Labels
    draw_row_label(screen, row_font, start_x, "Siege", 50, rain_active,
                   "siege" in opp_horns or "Dandelion" in opp_board['siege'])
    draw_row_label(screen, row_font, start_x, "Ranged", 140, fog_active,
                   "ranged" in opp_horns or "Dandelion" in opp_board['ranged'])
    draw_row_label(screen, row_font, start_x, "Melee", 230, frost_active,
                   "melee" in opp_horns or "Dandelion" in opp_board['melee'])

    draw_row_label(screen, row_font, start_x, "Melee", 350, frost_active,
                   "melee" in my_horns or "Dandelion" in my_board['melee'])
    draw_row_label(screen, row_font, start_x, "Ranged", 440, fog_active,
                   "ranged" in my_horns or "Dandelion" in my_board['ranged'])
    draw_row_label(screen, row_font, start_x, "Siege", 530, rain_active,
                   "siege" in my_horns or "Dandelion" in my_board['siege'])

    # Draw Weather Cards
    for i, w_card in enumerate(weather_zone):
        img = get_card_image(w_card, fonts['main'])
        mini_img = pygame.transform.scale(img, (60, 90))
        screen.blit(mini_img, (20, 200 + (i * 100)))

    right_center_x = 900

    # Draw Scores
    opp_title = fonts['main'].render("Opponent", True, (255, 50, 50))
    screen.blit(opp_title, (right_center_x - opp_title.get_width() // 2, 160))

    p2_score_txt = fonts['title'].render(str(opp_score), True, (255, 50, 50))
    screen.blit(p2_score_txt, (right_center_x - p2_score_txt.get_width() // 2, 190))

    you_title = fonts['main'].render("You", True, (50, 150, 255))
    screen.blit(you_title, (right_center_x - you_title.get_width() // 2, 440))

    p1_score_txt = fonts['title'].render(str(my_score), True, (50, 150, 255))
    screen.blit(p1_score_txt, (right_center_x - p1_score_txt.get_width() // 2, 470))

    # Draw Crown Gems
    draw_gems(screen, 887, 135, opp_rounds_won)
    draw_gems(screen, 887, 520, my_rounds_won)

    sys_text = fonts['main'].render(sys_message, True, (255, 215, 0))
    screen.blit(sys_text, (20, 20))

    # Draw Cards on the Board
    my_active_cards = []
    global selected_decoy
    draw_row_cards(screen, fonts, start_x, my_active_cards, selected_decoy, opp_board['siege'], 50, 'siege', False)
    draw_row_cards(screen, fonts, start_x, my_active_cards, selected_decoy, opp_board['ranged'], 140, 'ranged', False)
    draw_row_cards(screen, fonts, start_x, my_active_cards, selected_decoy, opp_board['melee'], 230, 'melee', False)
    draw_row_cards(screen, fonts, start_x, my_active_cards, selected_decoy, my_board['melee'], 350, 'melee', True)
    draw_row_cards(screen, fonts, start_x, my_active_cards, selected_decoy, my_board['ranged'], 440, 'ranged', True)
    draw_row_cards(screen, fonts, start_x, my_active_cards, selected_decoy, my_board['siege'], 530, 'siege', True)

    # Pass Button
    pass_rect = pygame.Rect(850, 350, 100, 50)
    pygame.draw.rect(screen, (200, 50, 50), pass_rect, border_radius=10)
    pass_txt = fonts['main'].render("PASS", True, (255, 255, 255))
    screen.blit(pass_txt, (pass_rect.x + 20, pass_rect.y + 10))

    # Turn Indicator
    current_turn_num = current_board_state.get('turn', 1)
    is_my_turn = (current_turn_num == 1 and my_player_id == "p1") or (current_turn_num == 2 and my_player_id == "p2")
    if is_my_turn:
        turn_color = (50, 150, 255)
        turn_msg = "YOUR TURN"
    else:
        turn_color = (255, 50, 50)
        turn_msg = "OPPONENT'S TURN"
    turn_txt = fonts['main'].render(turn_msg, True, turn_color)
    screen.blit(turn_txt, (pass_rect.centerx - turn_txt.get_width() // 2, pass_rect.y - 30))

    # Keep Hand Button
    keep_hand_rect = None
    if in_redraw_phase:
        dim_surf = pygame.Surface((WIDTH, HEIGHT))
        dim_surf.set_alpha(200)
        dim_surf.fill((0, 0, 0))
        screen.blit(dim_surf, (0, 0))

        title = fonts['title'].render(f"REDRAW PHASE ({2 - redraws_done} Swaps Left)", True, (255, 215, 0))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, HEIGHT // 2 - 50))

        keep_hand_rect = pygame.Rect(WIDTH // 2 - 100, HEIGHT // 2 + 20, 200, 50)
        pygame.draw.rect(screen, (50, 150, 255), keep_hand_rect, border_radius=10)
        btn_txt = fonts['main'].render("KEEP HAND", True, (255, 255, 255))
        screen.blit(btn_txt, (keep_hand_rect.x + 35, keep_hand_rect.y + 10))

    # Draw Player Hand
    hand_rects = []
    hand_y = 650

    if len(my_hand) > 0:
        spacing = 10
        max_hand_width = WIDTH - 100
        ideal_total_width = (len(my_hand) * CARD_WIDTH) + ((len(my_hand) - 1) * spacing)

        if ideal_total_width > max_hand_width and len(my_hand) > 1:
            card_step = (max_hand_width - CARD_WIDTH) / (len(my_hand) - 1)
            total_width = max_hand_width
        else:
            card_step = CARD_WIDTH + spacing
            total_width = ideal_total_width

        start_x_hand = (WIDTH // 2) - (total_width // 2)

        for index, card_name in enumerate(my_hand):
            img = get_card_image(card_name, fonts['main'])
            card_x = start_x_hand + (index * card_step)
            screen.blit(img, (card_x, hand_y))
            rect = pygame.Rect(card_x, hand_y, CARD_WIDTH, CARD_HEIGHT)
            hand_rects.append((rect, card_name))

    chat_input_rect = draw_chat_ui(screen, fonts) if show_chat else None

    # Game Over Overlay
    global game_over_text
    if game_over_text != "":
        overlay_font = pygame.font.SysFont('Arial', 120, bold=True)

        if game_over_text == "WINNER":
            color = (50, 255, 50)
        elif game_over_text == "LOSER":
            color = (255, 50, 50)
        else:
            color = (200, 200, 200)

        dim_surf = pygame.Surface((WIDTH, HEIGHT))
        dim_surf.set_alpha(150)
        dim_surf.fill((0, 0, 0))
        screen.blit(dim_surf, (0, 0))

        txt_surf = overlay_font.render(game_over_text, True, color)
        shadow_surf = overlay_font.render(game_over_text, True, (0, 0, 0))

        screen.blit(shadow_surf,
                    (WIDTH // 2 - txt_surf.get_width() // 2 + 5, HEIGHT // 2 - txt_surf.get_height() // 2 + 5))
        screen.blit(txt_surf, (WIDTH // 2 - txt_surf.get_width() // 2, HEIGHT // 2 - txt_surf.get_height() // 2))

    my_row_rects = {
        "melee": pygame.Rect(start_x, 350, row_width, row_height),
        "ranged": pygame.Rect(start_x, 440, row_width, row_height),
        "siege": pygame.Rect(start_x, 530, row_width, row_height)
    }

    # Medic Graveyard Overlay
    medic_grave_rects = []
    if selected_medic_card:
        dim_surf = pygame.Surface((WIDTH, HEIGHT))
        dim_surf.set_alpha(220)
        dim_surf.fill((0, 0, 0))
        screen.blit(dim_surf, (0, 0))

        title = fonts['title'].render("Select a card to revive:", True, (255, 255, 0))
        screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 100))

        grave_key = "p1_graveyard" if my_player_id == "p1" else "p2_graveyard"
        my_grave = current_board_state.get(grave_key, [])
        valid_grave = [c for c in my_grave if
                       not CARDS.get(c, {}).get("hero", False) and CARDS.get(c, {}).get("row") not in ["weather",
                                                                                                       "special",
                                                                                                       "any"]]

        for i, g_card in enumerate(valid_grave):
            x = 100 + (i % 8) * 100
            y = 200 + (i // 8) * 150
            img = get_card_image(g_card, fonts['main'])
            screen.blit(img, (x, y))
            pygame.draw.rect(screen, (255, 255, 0), (x - 2, y - 2, CARD_WIDTH + 4, CARD_HEIGHT + 4), 3)
            medic_grave_rects.append((pygame.Rect(x, y, CARD_WIDTH, CARD_HEIGHT), g_card))

    return None, pass_rect, hand_rects, chat_btn_rect, chat_input_rect, [], [], my_row_rects, my_active_cards,\
        medic_grave_rects, keep_hand_rect

def check_boost(board_dict, row_name):
    return any(CARDS.get(c, {}).get("ability") == "boost" for c in board_dict.get(row_name, []))

def draw_row_label(screen, row_font, start_x, text, y_pos, is_weathered=False, has_horn=False):
    color = (255, 50, 50) if is_weathered else (200, 200, 200)
    lbl = row_font.render(text, True, color)
    screen.blit(lbl, (start_x - 65, y_pos + 30))
    if has_horn:
        pygame.draw.circle(screen, (50, 255, 50), (start_x - 80, y_pos + 40), 6)

def draw_gems(screen, x, y, wins):
    for i in range(2):
        color = (255, 215, 0) if i < wins else (100, 100, 100)
        pygame.draw.circle(screen, color, (x + (i * 25), y), 10)
        pygame.draw.circle(screen, (0, 0, 0), (x + (i * 25), y), 10, 2)

def draw_row_cards(screen, fonts, start_x, my_active_cards, selected_decoy, card_list, y_pos, row_name, is_mine):
    spacing = 55
    if len(card_list) > 10:
        spacing = 500 / len(card_list)

    for i, card_name in enumerate(card_list):
        img = get_card_image(card_name, fonts['main'])
        mini_img = pygame.transform.scale(img, (50, 75))
        x_pos = start_x + 10 + (i * spacing)

        card_data = CARDS.get(card_name, {})

        if card_data.get("ability") == "tight_bond" and card_list.count(card_name) > 1:
            cyan_glow = (0, 255, 255)
            pygame.draw.rect(screen, cyan_glow, (x_pos - 2, y_pos, 54, 79), 2, border_radius=3)

        rect = pygame.Rect(x_pos, y_pos + 2, 50, 75)
        if is_mine:
            my_active_cards.append((rect, card_name, row_name))
            if selected_decoy and not card_data.get("hero", False) and card_name != "Decoy":
                yellow_glow = (255, 255, 0)
                pygame.draw.rect(screen, yellow_glow, (x_pos - 2, y_pos, 54, 79), 3, border_radius=3)

        screen.blit(mini_img, (x_pos, y_pos + 2))

def listen_to_server(sock):
    global is_running, my_hand, current_board_state, sys_message, my_player_id, app_state, login_status_msg
    try:
        while is_running:
            enc_data = recv_by_size(sock, return_type="bytes")
            if not enc_data:
                sys_message = "Server closed connection."
                break

            data = decrypt_msg(enc_data, aes_key)
            parts = data.split('|', 1)
            opcode = parts[0]
            payload = parts[1] if len(parts) > 1 else ""

            if opcode == "RES_AUTH":
                if payload == "SUCCESS":
                    app_state = "GAME"
                    sys_message = "Connected! Waiting for server to assign Player ID..."
                elif payload.startswith("FAIL"):
                    err_msg = payload.split('|')[1]
                    login_status_msg = err_msg


            elif opcode == "MSG" or opcode == "ERR":
                sys_message = payload
                print(f"[{opcode}] {payload}")

            elif opcode == "RES":
                global my_rounds_won, opp_rounds_won, game_over_text
                if payload == "draw":
                    my_rounds_won += 1
                    opp_rounds_won += 1
                elif payload == my_player_id:
                    my_rounds_won += 1
                else:
                    opp_rounds_won += 1
                if my_rounds_won >= 2 and opp_rounds_won >= 2:
                    game_over_text = "DRAW"
                elif my_rounds_won >= 2:
                    game_over_text = "WINNER"
                elif opp_rounds_won >= 2:
                    game_over_text = "LOSER"

            elif opcode == "SYS":
                sys_message = payload
                if payload == "SHUTDOWN":
                    sys_message = "Game Over! Disconnecting..."
                    is_running = False
                    break
                elif payload == "P1":
                    my_player_id = "p1"
                    sys_message = "Player 1"
                elif payload.startswith("P2"):
                    my_player_id = "p2"
                    sys_message = "Player 2"

            elif opcode == "CHAT":
                chat_history.append(f"Opponent: {payload}")

            elif opcode == "REQ_CHAIN":
                global selected_medic_card, is_chaining_medic
                selected_medic_card = payload
                is_chaining_medic = True
                sys_message = f"Medic Chain! Pick a target for {payload}!"

            elif opcode == "HAND":
                if payload == "":
                    my_hand = []
                else:
                    my_hand = payload.split(',')

            elif opcode == "UPDATE":
                global in_redraw_phase, redraws_done
                if current_board_state is None:
                    in_redraw_phase = True
                    redraws_done = 0
                current_board_state = json.loads(payload)

    except Exception as e:
        if is_running:
            sys_message = f"Connection error: {e}"
            login_status_msg = f"Connection error: {e}"


def main():
    global is_running, show_chat, chat_active, chat_input_text, i_am_ready
    global aes_key, active_input, login_user_text, login_pass_text, login_status_msg, app_state
    global deck_scroll_y, pool_scroll_y, selected_horn, selected_decoy, selected_medic_card, is_chaining_medic
    global my_deck_selection, current_board_state, sys_message
    global is_muted, current_track_index
    global in_redraw_phase, redraws_done
    selected_decoy = False
    selected_medic_card = None
    is_chaining_medic = False

    # Initialize Pygame and Audio Engine
    pygame.init()
    pygame.mixer.init()
    pygame.mixer.music.set_endevent(MUSIC_END)
    try:
        pygame.mixer.music.load(playlist[current_track_index])
        pygame.mixer.music.set_volume(0.5)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Could not load music: {e}")

    # Window Setup
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Gwent Project (Secure Client)")
    clock = pygame.time.Clock()
    fonts = {
        'main': pygame.font.SysFont('Arial', 24),
        'title': pygame.font.SysFont('Arial', 36, bold=True)
    }

    client_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        client_sock.connect((HOST, PORT))

        print("[CLIENT] Starting RSA Handshake...")
        send_with_size(client_sock, "RSA|REQPUB")
        server_pub_pem = recv_by_size(client_sock, return_type="bytes")

        server_pub_key = RSA.import_key(server_pub_pem)
        aes_key = get_random_bytes(32)
        cipher_rsa = PKCS1_OAEP.new(server_pub_key)
        enc_aes_key = cipher_rsa.encrypt(aes_key)

        send_with_size(client_sock, enc_aes_key)
        print("[CLIENT] Secure AES connection established!")

        listen_thread = threading.Thread(target=listen_to_server, args=(client_sock,))
        listen_thread.start()

    except ConnectionRefusedError:
        print("Could not connect to server.")
        pygame.quit()
        return

    while is_running:
        # Draw Current Screen State
        if app_state == "LOGIN":
            u_rect, p_rect, log_btn, sig_btn = draw_login_screen(screen, fonts)
        else:
            ready_btn, pass_btn, hand_rects, chat_btn_rect, chat_input_rect, deck_rects, pool_rects, my_row_rects,\
                my_active_cards, medic_grave_rects, keep_hand_rect = draw_board(screen, fonts)

        # Process OS Events
        for event in pygame.event.get():
            # Handle Window Close
            if event.type == pygame.QUIT:
                is_running = False

            # Handle Music Looping
            if event.type == MUSIC_END:
                current_track_index = (current_track_index + 1) % len(playlist)
                try:
                    pygame.mixer.music.load(playlist[current_track_index])
                    pygame.mixer.music.play()
                except:
                    pass

            # Handle Left Mouse Click
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                mouse_pos = event.pos

                # Login Screen Clicks
                if app_state == "LOGIN":
                    if u_rect.collidepoint(mouse_pos):
                        active_input = "USER"
                    elif p_rect.collidepoint(mouse_pos):
                        active_input = "PASS"

                    if log_btn.collidepoint(mouse_pos):
                        if login_user_text.strip() == "" or login_pass_text.strip() == "":
                            login_status_msg = "Fields cannot be empty!"
                        else:
                            login_status_msg = "Authenticating..."
                            secure_send(client_sock, f"REQ_AUTH|LOGIN|{login_user_text}|{login_pass_text}")

                    elif sig_btn.collidepoint(mouse_pos):
                        if login_user_text.strip() == "" or login_pass_text.strip() == "":
                            login_status_msg = "Fields cannot be empty!"
                        else:
                            login_status_msg = "Creating account..."
                            secure_send(client_sock, f"REQ_AUTH|SIGNUP|{login_user_text}|{login_pass_text}")

                # In-Game Clicks
                elif app_state == "GAME":
                    mute_btn_rect = pygame.Rect(WIDTH - 120, 70, 100, 40)
                    if mute_btn_rect.collidepoint(mouse_pos):
                        is_muted = not is_muted
                        if is_muted:
                            pygame.mixer.music.set_volume(0.0)
                        else:
                            pygame.mixer.music.set_volume(0.5)
                        continue

                    # Handle Logout Button
                    if not current_board_state:
                        logout_btn_rect = pygame.Rect(WIDTH - 240, 20, 100, 40)
                        if logout_btn_rect.collidepoint(mouse_pos):
                            secure_send(client_sock, "REQ_LOGOUT|")
                            app_state = "LOGIN"
                            i_am_ready = False
                            my_deck_selection = ["Geralt", "Ciri", "Vesemir", "Triss", "Yennefer", "Catapult",
                                                "Trebuchet",
                                                "Zoltan", "Keira", "Ballista"]
                            current_board_state = None
                            global my_rounds_won, opp_rounds_won, game_over_text, chat_history, show_chat
                            my_rounds_won = 0
                            opp_rounds_won = 0
                            game_over_text = ""
                            chat_history = []
                            show_chat = False
                            login_status_msg = "Logged out successfully."
                            sys_message = "Waiting for server..."
                            continue

                    # Handle Redraw Clicks
                    if in_redraw_phase:
                        if keep_hand_rect and keep_hand_rect.collidepoint(mouse_pos):
                            in_redraw_phase = False
                            continue
                        elif hand_rects:
                            for rect, card_name in hand_rects:
                                if rect.collidepoint(mouse_pos):
                                    secure_send(client_sock, f"REQ_REDRAW|{card_name}")
                                    redraws_done += 1
                                    if redraws_done >= 2:
                                        in_redraw_phase = False
                                    break
                        continue

                    # Handle Chat Activation
                    if chat_btn_rect.collidepoint(mouse_pos):
                        show_chat = not show_chat
                    if chat_input_rect and chat_input_rect.collidepoint(mouse_pos):
                        chat_active = True
                    else:
                        chat_active = False

                    if not show_chat or (chat_input_rect and not chat_input_rect.collidepoint(mouse_pos)):
                        # Deck Builder Selection Clicks
                        if 140 < mouse_pos[1] < HEIGHT - 100:
                            if pool_rects and not i_am_ready:
                                for rect, card_name in pool_rects:
                                    if rect.collidepoint(mouse_pos):
                                        my_deck_selection.append(card_name)
                                        break
                            if deck_rects and not i_am_ready:
                                for rect, card_name in deck_rects:
                                    if rect.collidepoint(mouse_pos):
                                        my_deck_selection.remove(card_name)
                                        break

                        # Ready & Pass Buttons
                        if ready_btn and ready_btn.collidepoint(mouse_pos):
                            i_am_ready = True
                            deck_str = ",".join(my_deck_selection)
                            secure_send(client_sock, f"DECK|{deck_str}")
                        if pass_btn and pass_btn.collidepoint(mouse_pos):
                            secure_send(client_sock, "PASS|")

                        # Handle Playing Commander's Horn
                        if selected_horn and my_row_rects:
                            clicked_row = False
                            for row_name, rect in my_row_rects.items():
                                if rect.collidepoint(mouse_pos):
                                    secure_send(client_sock, f"PLAY|Commander's Horn|{row_name}")
                                    selected_horn = False
                                    clicked_row = True
                                    break

                            if not clicked_row:
                                selected_horn = False

                        # Handle Playing Decoy
                        elif selected_decoy and my_active_cards:
                            clicked_card = False
                            for rect, target_name, row_name in my_active_cards:
                                if rect.collidepoint(mouse_pos):
                                    if not CARDS.get(target_name, {}).get("hero", False) and target_name != "Decoy":
                                        secure_send(client_sock, f"PLAY|Decoy|{row_name}|{target_name}")
                                        selected_decoy = False
                                        clicked_card = True
                                        break
                            if not clicked_card:
                                selected_decoy = False

                        # Handle Playing Medic
                        elif selected_medic_card and medic_grave_rects:
                            clicked = False
                            for rect, target_name in medic_grave_rects:
                                if rect.collidepoint(mouse_pos):
                                    if is_chaining_medic:
                                        secure_send(client_sock, f"EXEC_CHAIN|{selected_medic_card}|{target_name}")
                                        is_chaining_medic = False
                                    else:
                                        row = CARDS[selected_medic_card]["row"]
                                        secure_send(client_sock, f"PLAY|{selected_medic_card}|{row}|{target_name}")
                                    selected_medic_card = None
                                    clicked = True
                                    break

                        # Playing Standard Cards from Hand
                        elif hand_rects:
                            for rect, card_name in hand_rects:
                                if rect.collidepoint(mouse_pos):
                                    if card_name == "Commander's Horn":
                                        selected_horn = True
                                        selected_decoy = False
                                        selected_medic_card = None

                                    elif CARDS.get(card_name, {}).get("ability") == "decoy":
                                        selected_decoy = True
                                        selected_horn = False
                                        selected_medic_card = None

                                    elif CARDS.get(card_name, {}).get("ability") == "medic":
                                        grave_key = "p1_graveyard" if my_player_id == "p1" else "p2_graveyard"
                                        my_grave = current_board_state.get(grave_key, [])
                                        valid = [c for c in my_grave if
                                                 not CARDS.get(c, {}).get("hero", False) and CARDS.get(c, {}).get(
                                                     "row") not in ["weather", "special", "any"]]
                                        if len(valid) == 0:
                                            row = CARDS[card_name]["row"]
                                            secure_send(client_sock, f"PLAY|{card_name}|{row}")
                                        else:
                                            selected_medic_card = card_name
                                            selected_horn = False
                                            selected_decoy = False

                                    else:
                                        row = CARDS[card_name]["row"]
                                        secure_send(client_sock, f"PLAY|{card_name}|{row}")

            # Handle Keyboard Typing
            if event.type == pygame.KEYDOWN:
                if app_state == "LOGIN":
                    if event.key == pygame.K_TAB:
                        active_input = "PASS" if active_input == "USER" else "USER"
                    elif event.key == pygame.K_BACKSPACE:
                        if active_input == "USER":
                            login_user_text = login_user_text[:-1]
                        else:
                            login_pass_text = login_pass_text[:-1]
                    elif event.key == pygame.K_RETURN:
                        if login_user_text.strip() == "" or login_pass_text.strip() == "":
                            login_status_msg = "Fields cannot be empty!"
                        else:
                            login_status_msg = "Authenticating..."
                            secure_send(client_sock, f"REQ_AUTH|LOGIN|{login_user_text}|{login_pass_text}")
                    else:
                        if active_input == "USER" and len(login_user_text) < 15:
                            login_user_text += event.unicode
                        elif active_input == "PASS" and len(login_pass_text) < 15:
                            login_pass_text += event.unicode

                elif app_state == "GAME" and chat_active:
                    if event.key == pygame.K_RETURN:
                        if chat_input_text.strip() != "":
                            secure_send(client_sock, f"CHAT|{chat_input_text}")
                            chat_history.append(f"You: {chat_input_text}")
                        chat_input_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        chat_input_text = chat_input_text[:-1]
                    else:
                        if len(chat_input_text) < 35:
                            chat_input_text += event.unicode

            # Handle Mouse Scroll Wheel
            elif event.type == pygame.MOUSEWHEEL:
                if app_state == "GAME" and not current_board_state and not i_am_ready:
                    mouse_x, mouse_y = pygame.mouse.get_pos()

                    if mouse_x < WIDTH // 2:
                        deck_scroll_y -= event.y * 30
                        deck_scroll_y = max(0, deck_scroll_y)

                    else:
                        pool_scroll_y -= event.y * 30
                        pool_scroll_y = max(0, pool_scroll_y)

        # Update display and cap at 60 FPS
        pygame.display.flip()
        clock.tick(60)

    print("\n[CLIENT] Shutting down...")
    try:
        client_sock.shutdown(socket.SHUT_RDWR)
    except:
        pass
    client_sock.close()
    if 'listen_thread' in locals():
        listen_thread.join()
    pygame.quit()
    print("[CLIENT] Closed successfully.")


if __name__ == "__main__":
    main()