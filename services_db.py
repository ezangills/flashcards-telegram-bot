import pg8000
from urllib.parse import urlparse
from datetime import datetime
from models import Deck, Card
import uuid
import random
import time
import os


class DatabaseManager:
    def __init__(self):
        """
        Initialize the DatabaseManager with a database URL.
        :param database_url: A PostgreSQL database URL in the format:
                             postgresql://username:password@host:port/database
        """
        # Parse the database URL
        database_url = os.getenv("DATABASE_URL")
        parsed_url = urlparse(database_url)
        self.connection = pg8000.connect(
            user=parsed_url.username,
            password=parsed_url.password,
            host=parsed_url.hostname,
            port=parsed_url.port or 5432,  # Default PostgreSQL port
            database=parsed_url.path.lstrip("/")
        )
        self.cursor = self.connection.cursor()
        self.create_tables()

    def create_tables(self):
        # Create decks table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS decks (
                id UUID PRIMARY KEY,
                name TEXT NOT NULL,
                user_id TEXT NOT NULL
            )
        """)

        # Create cards table
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS cards (
                id UUID PRIMARY KEY,
                deck_id UUID NOT NULL,
                user_id TEXT NOT NULL,
                front TEXT NOT NULL,
                back TEXT NOT NULL,
                last_revised TIMESTAMP NOT NULL,
                level INTEGER NOT NULL,
                FOREIGN KEY(deck_id) REFERENCES decks(id) ON DELETE CASCADE
            )
        """)
        self.connection.commit()

    def generate_uuid4(self):
        rnd = (random.Random())
        rnd.seed(time.time() * 1000)
        return str(uuid.UUID(int=rnd.getrandbits(128), version=4))

    # Deck Management
    def add_deck(self, name, user_id):
        if self.get_deck(name, user_id):
            return False
        deck_id = self.generate_uuid4()
        self.cursor.execute(
            "INSERT INTO decks (id, name, user_id) VALUES (%s, %s, %s)",
            (deck_id, name, user_id)
        )
        self.connection.commit()
        return True

    def get_deck(self, name, user_id):
        self.cursor.execute(
            "SELECT id, name FROM decks WHERE name = %s AND user_id = %s",
            (name, user_id)
        )
        result = self.cursor.fetchone()
        return Deck(result[1], str(result[0])) if result else None

    def delete_deck(self, name, user_id):
        self.cursor.execute(
            "DELETE FROM decks WHERE name = %s AND user_id = %s",
            (name, user_id)
        )
        self.connection.commit()

    def get_all_decks(self, user_id):
        """
        Retrieve all decks for a specific user.
        :param user_id: The ID of the user.
        :return: A list of Deck objects for the user.
        """
        self.cursor.execute(
            "SELECT id, name FROM decks WHERE user_id = %s",
            (user_id,)
        )
        rows = self.cursor.fetchall()
        return [Deck(name=row[1], id=str(row[0])) for row in rows]

    # Card Management
    def add_card(self, deck_name, front, back, user_id):
        deck = self.get_deck(deck_name, user_id)
        if deck:
            card_id = self.generate_uuid4()
            last_revised = datetime.now().isoformat()
            self.cursor.execute(
                """
                INSERT INTO cards (id, deck_id, user_id, front, back, last_revised, level)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (card_id, deck.id, user_id, front, back, last_revised, 0)
            )
            self.connection.commit()
            return True
        return False

    def delete_card(self, deck_name, card_id, user_id):
        deck = self.get_deck(deck_name, user_id)
        if deck:
            self.cursor.execute(
                "DELETE FROM cards WHERE id = %s AND user_id = %s",
                (card_id, user_id)
            )
            self.connection.commit()
            return True
        return False

    def edit_card(self, deck_name, old_front, old_back, level, user_id):
        deck = self.get_deck(deck_name, user_id)
        if deck:
            last_revised = datetime.now().isoformat()
            self.cursor.execute(
                """
                UPDATE cards
                SET level = %s, last_revised = %s
                WHERE front = %s AND back = %s AND deck_id = %s AND user_id = %s
                """,
                (level, last_revised, old_front, old_back, deck.id, user_id)
            )
            self.connection.commit()
            return True
        return False

    # Learning Logic
    def select_cards_for_learning(self, deck_name, user_id):
        deck = self.get_deck(deck_name, user_id)
        if deck:
            self.cursor.execute(
                """
                SELECT id, front, back, last_revised, level
                FROM cards
                WHERE deck_id = %s AND user_id = %s
                ORDER BY level ASC, last_revised ASC
                LIMIT 6
                """,
                (deck.id, user_id)
            )
            rows = self.cursor.fetchall()
            return [Card(row[1], row[2], str(row[0]), row[3], row[4]) for row in rows]
        return []

    def select_cards(self, deck_name, user_id):
        deck = self.get_deck(deck_name, user_id)
        if deck:
            self.cursor.execute(
                """
                SELECT id, front, back, last_revised, level
                FROM cards
                WHERE deck_id = %s AND user_id = %s
                ORDER BY level ASC, last_revised ASC
                """,
                (deck.id, user_id)
            )
            rows = self.cursor.fetchall()
            return [Card(row[1], row[2], str(row[0]), row[3], row[4]) for row in rows]
        return []

    def close_connection(self):
        self.cursor.close()
        self.connection.close()
