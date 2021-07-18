import socket
import sys
import threading
import pickle

import cards

from itertools import combinations

host = ''  # IPv4 Address
port = 7976  # port

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket initialization
server.bind((host, port))  # binding host and port to socket
server.listen()

clients = {}

game_started = False
game_state = {
    "pot": 0,
    "current_bet": 0,
    "players": [],
    "rounds": 0,
    "end_count": 0
}

msg_event = threading.Event()

HEADER_LENGTH = 10


def broadcast_targeted(data, client, sender, title):
    data = {'title': title, 'data': data}

    msg = pickle.dumps(data)
    msg = bytes(f"{len(msg):<{HEADER_LENGTH}}", 'utf-8') + msg

    if sender is None:
        sender_info = pickle.dumps("Server")
        sender_info = bytes(f"{len(sender_info):<{HEADER_LENGTH}}", 'utf-8') + sender_info
    else:
        sender_info = pickle.dumps(clients[sender]['name'])
        sender_info = bytes(f"{len(sender_info):<{HEADER_LENGTH}}", 'utf-8') + sender_info

    client.send(sender_info + msg)


def broadcast(message, sender, title):
    # currently only works with strings
    for client in clients:
        if client is not sender:
            broadcast_targeted(message, client, sender, title)


def remove_client(client):
    print(f'{clients[client]["name"]} disconnected!')
    broadcast(f'{clients[client]["name"]} was removed!', client, 'TEXT')
    del clients[client]


def process_message(client):
    try:
        # Receive our "header" containing message length, it's size is defined and constant
        message_header = client.recv(HEADER_LENGTH)
        # If we received no data, client gracefully closed a connection, for example using socket.close() or
        # socket.shutdown(socket.SHUT_RDWR)
        if not len(message_header):
            return True

        # Convert header to int value
        message_length = int(message_header.decode('utf-8').strip())

        # Return an object of message header and message data
        return {'header': message_header.decode('utf-8'), 'data': client.recv(message_length).decode('utf-8')}

    except Exception as e:
        print(f'Error in processing message: {e}')
        return False


def handle(client):
    while True:
        try:
            # Receive message
            message = process_message(client)
            if message is False:
                remove_client(client)
                break

            print(f'Received message from {clients[client]["name"]}: {message["data"]}')

            # store past 1000 client messages
            if len(clients[client]["msgs"]) > 1000:
                clients[client]["msgs"].pop(0)

            clients[client]["msgs"].append(message['data'])

            if not game_started:
                # Chat room
                if message['data'][0] == "/":
                    # Chat room commands
                    continue
                else:
                    broadcast(message["data"], client, 'TEXT')
            else:
                if clients[client]['options'] and not msg_event.is_set():
                    msg_event.set()

        except Exception as e:
            print(f'Error in handling message: {e}')
            remove_client(client)
            break


def receive():
    while True:
        try:
            client, address = server.accept()
            print("Connected with {}".format(str(address)))

            # Client should send name right away, receive it
            username = process_message(client)
            if username is False:
                remove_client(client)
                continue
            for c in clients:
                if clients[c]["name"] == username['data']:
                    username['data'] = username['data'] + "'"

            # Make new player/client
            user = {
                'name': username['data'],
                'chips': 100,
                'hand': [],
                'role': "N",
                'options': [],
                "msgs": [],
                "in_for": 0
            }
            clients[client] = user
            print('Accepted new connection from {}:{}, username: {}'.format(*address,
                                                                            user['name']))

            # Send "..." has joined the server
            broadcast("{} joined!".format(user['name']), client, 'TEXT')
            thread = threading.Thread(target=handle, args=(client,))  # make new thread for each client
            thread.start()
        except Exception as e:
            print("Error running the server!")
            e = sys.exc_info()[0]
            print("Error: %s" % e)
            break


def add_to_pot(client, amount):
    clients[client]['chips'] -= amount
    clients[client]["in_for"] += amount
    game_state["pot"] += amount


def cmd_call(client):
    add_to_pot(client, game_state["current_bet"]-clients[client]["in_for"])
    game_state["end_count"] += 1
    broadcast(f"{clients[client]['name']} calls", None, "SERVER-MSG")


def cmd_raise(client):
    game_state["end_count"] = 1
    while True:
        msg_event.clear()
        broadcast_targeted("Enter amount to raise by (the call is already included)('#'):", client, None, "SERVER-MSG")
        msg_event.wait()
        raise_amount = clients[client]['msgs'][-1]
        try:
            raise_amount = int(raise_amount)
            total_amount = raise_amount + game_state["current_bet"]-clients[client]["in_for"]
        except ValueError:
            broadcast_targeted("Please enter a number", client, None, "SERVER-MSG")
            continue
        if clients[client]["chips"] < total_amount:
            broadcast_targeted("Insufficient chips", client, None, "SERVER-MSG")
            continue
        else:
            game_state["current_bet"] = total_amount + clients[client]["in_for"]
            add_to_pot(client, total_amount)
            break
    broadcast(f"{clients[client]['name']} raises by {raise_amount}", None, "SERVER-MSG")
    return


def cmd_fold(client):
    game_state["players"].remove(client)
    broadcast(f"{clients[client]['name']} folds", None, "SERVER-MSG")


def cmd_all_in(client):
    broadcast(f"{clients[client]['name']} is all in ({clients[client]['chips']} chips)", None, "SERVER-MSG")
    if clients[client]["chips"] > game_state["current_bet"]:
        game_state["current_bet"] = clients[client]["chips"] + clients[client]["in_for"]
        game_state["end_count"] = 1
    elif clients[client]["chips"] <= game_state["current_bet"]:
        game_state["end_count"] += 1
    add_to_pot(client, clients[client]["chips"])


def cmd_check(client):
    game_state["end_count"] += 1
    broadcast(f"{clients[client]['name']} checks", None, "SERVER-MSG")


def cmd_bet(client):
    game_state["end_count"] = 1
    while True:
        msg_event.clear()
        broadcast_targeted("Enter amount to bet('#'):", client, None, "SERVER-MSG")
        msg_event.wait()
        bet_amount = clients[client]['msgs'][-1]
        try:
            bet_amount = int(bet_amount)
        except ValueError:
            broadcast_targeted("Please enter a number", client, None, "SERVER-MSG")
            continue
        if clients[client]["chips"] < bet_amount:
            broadcast_targeted("Insufficient chips", client, None, "SERVER-MSG")
            continue
        else:
            add_to_pot(client, bet_amount)
            game_state["current_bet"] = bet_amount
            break
    broadcast(f"{clients[client]['name']} bets {bet_amount}", None, "SERVER-MSG")
    return


def start_betting():
    # Check to see if all players (or all but one) are all in
    all_ins = sum(1 for client in game_state["players"] if clients[client]["chips"] == 0)
    if all_ins >= len(game_state["players"]) - 1:
        return

    cmds = {
        "call": cmd_call,
        "raise": cmd_raise,
        "fold": cmd_fold,
        "all_in": cmd_all_in,
        "check": cmd_check,
        "bet": cmd_bet
    }

    while True:
        if game_state["end_count"] == len(game_state["players"]):
            break

        for client in list(game_state["players"]):
            # Only 1 player left
            if len(game_state["players"]) == 1 or game_state["end_count"] == len(game_state["players"]):
                break
            to_call = game_state["current_bet"] - clients[client]["in_for"]
            # Provide available options
            # First check if the client is all in or not (no chips left)
            if clients[client]["chips"] != 0:

                clients[client]['options'].append("fold")

                if clients[client]["chips"] > to_call:
                    if to_call != 0:
                        clients[client]['options'].append("call")
                    if game_state["current_bet"] != 0:
                        clients[client]['options'].append("raise")
                    else:
                        clients[client]['options'].append("bet")

                if clients[client]["chips"] != 0:
                    clients[client]['options'].append("all_in")

                if to_call == 0:
                    clients[client]['options'].append("check")
            else:
                # If player is already all in, skip their turn
                game_state["end_count"] += 1
                continue

            broadcast(f"It is {clients[client]['name']}'s turn", None, "SERVER-MSG")

            while True:
                # Give some data
                broadcast_targeted(f"To call is {to_call}", client, None, "SERVER-MSG")
                broadcast_targeted(f"You have {clients[client]['chips']} chips", client, None, "SERVER-MSG")

                # Present options
                options_string = 'OPTIONS:\n/' + '\n/'.join(clients[client]['options'])
                broadcast_targeted(options_string, client, None, "PROMPT")

                # Sound alert for the player's turn
                broadcast_targeted("", client, None, "ALERT")

                # Wait for response
                msg_event.wait()
                message = clients[client]['msgs'][-1]
                # Process response
                if message[0] == "/":
                    cmd = message[1:]
                    if cmd in clients[client]['options']:
                        cmds[cmd](client)
                        clients[client]['options'] = []
                        msg_event.clear()

                        broadcast(f"The pot is {game_state['pot']}", None, "SERVER-MSG")
                        break

                broadcast_targeted("Please input one of the following:", client, None, "SERVER-MSG")
                msg_event.clear()
        # Break out of nested loop
        else:
            continue
        break
    game_state["current_bet"] = 0
    game_state["end_count"] = 0
    for client in game_state["players"]:
        clients[client]["in_for"] = 0

    broadcast("Betting round over", None, "SERVER-MSG")


def evaluate_hand(hand, community):
    # Each hand will be associated with a numeric code to determine its worth
    # Template: (hand) (card 1) (card 2) (card 3) (card 4) (card 5) (suit)
    # Ex code: 10 14 13 12 11 10 4 (Royal Flush)

    cards_total = hand + community
    cards_combs = combinations(cards_total, 5)
    value = 0

    # Evaluate hand
    hands = {
        "royal flush": cards.check_royal_flush,
        "straight flush": cards.check_straight_flush,
        "4 pair": cards.check_four_kind,
        "full house": cards.check_full_house,
        "flush": cards.check_flush,
        "straight": cards.check_straight,
        "3 pair": cards.check_three_kind,
        "2 pair": cards.check_two_pair,
        "1 pair": cards.check_one_pair,
        "high card": cards.check_high_card
    }
    hand_value = 0
    best_hand = None
    for cards_comb in cards_combs:
        cards_comb = sorted(cards_comb, key=lambda crd: crd.value)
        for hand in hands:
            test_hand_value = hands[hand](cards_comb)
            if test_hand_value > hand_value:
                hand_value = test_hand_value
                best_hand = cards_comb.copy()
    value += hand_value

    # Evaluate each card's value in hand
    best_hand = sorted(best_hand, key=lambda e: sum(c.value == e.value for c in best_hand), reverse=True)
    for crd in best_hand:
        value *= 100
        value += crd.value

    # Evaluate suit's worth (of the best card in the hand)
    value *= 10
    value += best_hand[-1].suit_value()

    return value


def start_game():
    global game_started
    game_started = True
    order = []
    game_state["rounds"] = 0
    for client in clients:
        order.append(client)
    while game_started:

        game_state["rounds"] += 1
        game_state["pot"] = 0

        # Set player positions and order, place big and small blinds (big and small blinds)
        for client in clients:
            if clients[client]["chips"] == 0 and client in order:
                broadcast_targeted("You have no more chips ;( Don't worry! Just spend more money to win it back!",
                                   client, None, "SERVER-MSG")
                order.remove(client)

        if len(order) <= 1:
            print("Not enough players to start a game")
            game_started = False
            continue

        order.append(order.pop(0))
        game_state["players"] = order.copy()

        for count, client in enumerate(order):

            if count == len(order)-2:
                clients[client]['role'] = "S"
                broadcast_targeted("You are the Small Blind (-1 chips)", client, None, "SERVER-MSG")
                add_to_pot(client, 1)
            elif count == len(order) - 1:
                clients[client]['role'] = "B"
                broadcast_targeted("You are the Big Blind (-2 chips)", client, None, "SERVER-MSG")
                add_to_pot(client, 2)
                game_state["current_bet"] = 2
            else:
                clients[client]['role'] = "N"
                broadcast_targeted("Yay, you aren't the big or small blind!", client, None, "SERVER-MSG")

        # Deal cards
        deck = cards.Deck()
        broadcast("Shuffling deck...", None, "SERVER-MSG")
        deck.shuffle_cards()
        for client in game_state["players"]:
            clients[client]["hand"] = deck.deal(2)
            broadcast_targeted(clients[client]["hand"], client, None, "DEAL")

        # First round of betting
        start_betting()
        # Declare flop
        deck.deal(1)
        flop = deck.deal(3)
        broadcast("Flop Incoming!", None, "SERVER-MSG")
        broadcast(flop, None, "COMMUNITY")
        # Second round of betting
        start_betting()
        # Declare turn
        deck.deal(1)
        turn = deck.deal(1)
        broadcast("Turn Incoming!", None, "SERVER-MSG")
        broadcast(turn, None, "COMMUNITY")
        # Third round of betting
        start_betting()
        # Declare river
        deck.deal(1)
        river = deck.deal(1)
        broadcast("River Incoming!", None, "SERVER-MSG")
        broadcast(river, None, "COMMUNITY")
        # Final round of betting
        start_betting()
        # Determine winner and distribute chips
        community = flop + turn + river
        best_hand = 0
        winner = game_state["players"][0]
        for client in game_state["players"]:
            worth = evaluate_hand(clients[client]["hand"], community)
            if worth > best_hand:
                best_hand = worth
                winner = client
        broadcast(f"Winner is {clients[winner]['name']}!", None, "SERVER-MSG")
        clients[winner]["chips"] += game_state["pot"]
        # Another round?
        print("Type /end to end game, otherwise begin another round!")
        if input() == "/end":
            game_started = False


def command():
    while True:
        cmd = input()
        if cmd == "/test":
            print("Hello World!")
        elif cmd == "/start":
            broadcast("Starting the round...", None, "SERVER-MSG")
            start_game()
        elif cmd == "/add_chips":
            print("To who?")
            name = input()
            print("How much? (#)")
            for client in clients:
                if clients[client]["name"] == name:
                    clients[client]["chips"] += int(input())


print("Starting Server...")
server_thread = threading.Thread(target=receive)
server_thread.start()
command_thread = threading.Thread(target=command)
command_thread.start()
