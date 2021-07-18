import random


class Deck:

    def __init__(self):
        suits = ["♠", "♥", "♦", "♣"]
        values = [i for i in range(2, 15)]
        self.cards = [Card(value, suit, False) for value in values for suit in suits]

    def __str__(self):
        to_print = ""
        for card in self.cards:
            to_print += card.printStr()
        return to_print

    def add_card(self, value, suit):
        self.cards.append(Card(value, suit, True))

    def remove_card(self, card):
        self.cards.pop(self.cards.index(card))

    def deal(self, count):
        dealt_cards = []
        for i in range(count):
            card = self.cards[0]
            self.remove_card(card)
            dealt_cards.append(card)
        return dealt_cards

    def shuffle_cards(self):
        random.shuffle(self.cards)


class Card:
    def __init__(self, value, suit, hidden):
        self.value = value
        self.suit = suit
        self.hidden = hidden

    def printStr(self):
        symb = self.symbol()
        to_print = ""
        to_print += '┌─────────┐\n'
        if self.hidden:
            to_print += '│░░░░░░░░░│\n'
            to_print += '│░░░░░░░░░│\n'
            to_print += '│░░░░$░░░░│\n'
            to_print += '│░░░░░░░░░│\n'
            to_print += '│░░░░░░░░░│\n'
        else:
            if self.value == 10:
                to_print += ('│{}       │\n'.format(symb))
            else:
                to_print += ('│{}        │\n'.format(symb))
            to_print += '│         │\n'
            to_print += ('│    {}    │\n'.format(self.suit))
            to_print += '│         │\n'
            if self.value == 10:
                to_print += ('│       {}│\n'.format(symb))
            else:
                to_print += ('│        {}│\n'.format(symb))

        to_print += '└─────────┘\n'
        return to_print

    def show_back(self):
        self.hidden = True

    def show_front(self):
        self.hidden = False

    def __str__(self):
        return self.printStr()

    def symbol(self):
        if self.value == 14:
            return "A"
        elif self.value == 13:
            return "K"
        elif self.value == 12:
            return "Q"
        elif self.value == 11:
            return "J"
        else:
            return str(self.value)

    def suit_value(self):
        if self.suit == "♠":
            return 4
        elif self.suit == "♥":
            return 3
        elif self.suit == "♦":
            return 2
        return 1


def check_royal_flush(cards_comb):
    values = [10, 11, 12, 13, 14]
    suit = cards_comb[0].suit
    for card in cards_comb:
        if card.suit != suit:
            return 0
        if card.value not in values:
            return 0
    return 10


def check_straight(cards_comb):
    for i, card in enumerate(cards_comb, 1):
        if i == len(cards_comb):
            break
        if cards_comb[i].value - card.value != 1:
            return 0
    return 5


def check_flush(cards_comb):
    suit = cards_comb[0].suit
    for card in cards_comb:
        if card.suit != suit:
            return 0
    return 6


def check_straight_flush(cards_comb):
    if check_straight(cards_comb) and check_flush(cards_comb):
        return 9
    return 0


def check_four_kind(cards_comb):
    for card in cards_comb:
        if sum(1 for c in cards_comb if c.value == card.value) == 4:
            return 8
    return 0


def check_three_kind(cards_comb):
    for card in cards_comb:
        if sum(1 for c in cards_comb if c.value == card.value) == 3:
            return 4
    return 0


def check_two_pair(cards_comb):
    one_pair = 0
    for card in cards_comb:
        if sum(1 for c in cards_comb if c.value == card.value) == 2 and card.value != one_pair:
            if one_pair:
                return 3
            else:
                one_pair = card.value
    return 0


def check_full_house(cards_comb):
    if check_three_kind(cards_comb) and check_two_pair(cards_comb):
        return 7
    return 0


def check_one_pair(cards_comb):
    for card in cards_comb:
        if sum(1 for c in cards_comb if c.value == card.value) == 2:
            return 2
    return 0


def check_high_card(cards_comb):
    return 1


def print_cards(cards_list):
    print_str = ""
    print_str_list = []
    for card in cards_list:
        print_str_list.append(card.printStr().split('\n'))
    for col in range(len(print_str_list[0])):
        for row in range(len(print_str_list)):
            print_str += print_str_list[row][col] + ' '
        print_str += '\n'
    print(print_str)

