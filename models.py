import json
from datetime import datetime

class Card:
    def __init__(self, front, back, last_revised=None, level=0):
        self.front = front
        self.back = back
        self.last_revised = last_revised or datetime.now().isoformat()
        self.level = level

    def to_dict(self):
        return {
            "front": self.front,
            "back": self.back,
            "last_revised": self.last_revised,
            "level": self.level
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            front=data["front"],
            back=data["back"],
            last_revised=data["last_revised"],
            level=data["level"]
        )


class Deck:
    def __init__(self, name):
        self.name = name
        self.cards = []

    def add_card(self, card):
        self.cards.append(card)

    def remove_card(self, front, back):
        self.cards = [card for card in self.cards if (card.front != front and card.back != back)]

    def to_dict(self):
        return {
            "name": self.name,
            "cards": [card.to_dict() for card in self.cards]
        }

    @classmethod
    def from_dict(cls, data):
        deck = cls(data["name"])
        deck.cards = [Card.from_dict(card) for card in data["cards"]]
        return deck
