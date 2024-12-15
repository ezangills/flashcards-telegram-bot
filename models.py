import json
from datetime import datetime
from uuid import uuid4


class Card:
    def __init__(self, front, back, id=uuid4(), last_revised=None, level=0):
        self.front = front
        self.back = back
        self.id = id
        self.last_revised = last_revised or datetime.now().isoformat()
        self.level = level

    def to_dict(self):
        return {
            "front": self.front,
            "back": self.back,
            "id": self.id,
            "last_revised": self.last_revised,
            "level": self.level
        }

    @classmethod
    def from_dict(cls, data):
        return cls(
            front=data["front"],
            back=data["back"],
            id=data["id"],
            last_revised=data["last_revised"],
            level=data["level"]
        )


class Deck:
    def __init__(self, name):
        self.name = name
        self.cards = []

    def add_card(self, card):
        self.cards.append(card)

    def remove_card(self, id):
        self.cards = [card for card in self.cards if card.id != id]

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
