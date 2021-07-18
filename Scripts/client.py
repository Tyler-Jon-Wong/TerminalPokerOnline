import socket
import sys
import threading
import cards
import pickle
import time


HEADER_LENGTH = 10

nickname = input("Choose your nickname: ")

client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # socket initialization
client.connect(('172.105.98.201', 7976))  # connecting client to server

nickname = nickname.encode('utf-8')
nickname_header = f"{len(nickname):<{HEADER_LENGTH}}".encode('utf-8')
client.send(nickname_header + nickname)

is_open = True
community = []
hand = []


def format_server_msg(text):
    box = "--                                                                                --"
    if len(text) > len(box)-4:
        return f"--{text}--"
    return box[:int((len(box)/2)-(len(text)/2))] + text + box[int((len(box)/2)+(len(text)/2)):] + '\n'


def format_prompt(text):
    return "~~~~~~~~\n" + text + "\n~~~~~~~~\n"


def receive():
    try:
        while True:
            # all sent messages will have a title and data
            global is_open
            if not is_open:
                break
            # Receive our "header" containing username length, it's size is defined and constant
            sender_header = client.recv(HEADER_LENGTH)
            # If we received no data, server gracefully closed a connection, for example using socket.close() or
            # socket.shutdown(socket.SHUT_RDWR)
            if not len(sender_header):
                print('Connection closed by the server')
                sys.exit()

            # Convert header to int value
            sender_length = int(sender_header[:HEADER_LENGTH])

            # Receive and decode sender's username
            sender = client.recv(sender_length)
            sender = pickle.loads(sender)

            # Now do the same for the message
            message_header = client.recv(HEADER_LENGTH)
            message_length = int(message_header[:HEADER_LENGTH])
            message = client.recv(message_length)
            message = pickle.loads(message)

            message_title = message['title']
            message_data = message['data']

            if message_title == "TEXT":
                # Print message
                print(f'{sender} > {message_data}')
            elif message_title == "SERVER-MSG":
                print(format_server_msg(message_data))
                time.sleep(0.75)
            elif message_title == "DEAL":
                print("Dealt Hand:")
                global hand
                hand = message_data
                cards.print_cards(hand)
            elif message_title == "COMMUNITY":
                global community
                if len(community) == 5:
                    community = []
                community += message_data
                print("Your hand:")
                cards.print_cards(hand)
                print("Community cards:")
                cards.print_cards(community)
            elif message_title == "ALERT":
                print('\a')
            elif message_title == "PROMPT":
                print(format_prompt(message_data))


    except Exception as e:
        print("An error occured!")
        e = sys.exc_info()[0]
        print("Error: %s" % e)
        client.close()


def write():
    while True:
        message = input()
        if message == "/quit":
            global is_open
            is_open = False
            client.close()
            break
        if message:
            # Encode message to bytes, prepare header and convert to bytes, like for username above, then send
            message = message.encode('utf-8')
            message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
            client.send(message_header + message)


receive_thread = threading.Thread(target=receive)  # thread to receive messages
receive_thread.start()
write_thread = threading.Thread(target=write)  # thread to send messages
write_thread.start()
