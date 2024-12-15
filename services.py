import json
from models import Deck, Card

class DatabaseManager:
    def __init__(self, userId):
        self.decks = self.load_decks(userId)

    def load_decks(self, userId):
        try:
            with open(str(userId) + ".json", "r", encoding="utf-8") as f:
                data = json.load(f)
                return [Deck.from_dict(deck) for deck in data]
        except FileNotFoundError:
            return []

    def save_decks(self, userId):
        with open(str(userId) + ".json", "w", encoding="utf-8") as f:
            json.dump([deck.to_dict() for deck in self.decks], f, ensure_ascii=False, indent=4)

    def get_deck(self, name):
        for deck in self.decks:
            if deck.name == name:
                return deck
        return None

    def add_deck(self, name, userId):
        if self.get_deck(name):
            return False
        self.decks.append(Deck(name))
        self.save_decks(userId)
        return True

    def delete_deck(self, name, userId):
        self.decks = [deck for deck in self.decks if deck.name != name]
        self.save_decks(userId)

    # Card Management
    def add_card(self, deck_name, front, back, userId):
        deck = self.get_deck(deck_name)
        if deck:
            deck.add_card(Card(front, back))
            self.save_decks(userId)
            return True
        return False

    def delete_card(self, deck_name, id, userId):
        deck = self.get_deck(deck_name)
        if deck:
            deck.remove_card(id)
            self.save_decks(userId)
            return True
        return False

    def edit_card(self, deck_name, old_front, old_back, level, userId):
        deck = self.get_deck(deck_name)
        if deck:
            for card in deck.cards:
                if card.front == old_front and card.back == old_back:
                    card.level = level
                    self.save_decks(userId)
                    return True
        return False

    # Learning Logic
    def select_cards_for_learning(self, deck_name):
        deck = self.get_deck(deck_name)
        if deck:
            # Sort cards by level (ascending) and last revised (oldest first)
            cards = sorted(
                deck.cards,
                key=lambda c: (c.level, c.last_revised)
            )
            # Select up to six cards
            return cards[:6]
        return []

    def select_cards(self, deck_name):
        deck = self.get_deck(deck_name)
        if deck:
            # Sort cards by level (ascending) and last revised (oldest first)
            cards = sorted(
                deck.cards,
                key=lambda c: (c.level, c.last_revised)
            )
            # Select up to six cards
            return cards
        return []
