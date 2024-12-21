import json
import pg8000
from urllib.parse import urlparse
import glob
import os
import random
import time
import uuid


def generate_uuid4():
    rnd = (random.Random())
    rnd.seed(time.time() * 1000)
    return str(uuid.UUID(int=rnd.getrandbits(128), version=4))

def insert_data_from_json_files(database_url, json_files):
    # Parse database URL
    parsed_url = urlparse(database_url)
    conn = pg8000.connect(
        user=parsed_url.username,
        password=parsed_url.password,
        host=parsed_url.hostname,
        port=parsed_url.port or 5432,
        database=parsed_url.path.lstrip("/")
    )
    cursor = conn.cursor()

    for json_file in json_files:
        # Extract user_id from filename (filename without extension)
        user_id = json_file.split("/")[-1].split(".")[0]

        # Load JSON data
        with open(json_file, "r", encoding="utf-8") as f:
            decks = json.load(f)

        for deck in decks:
            # Insert into decks table
            deck_id = generate_uuid4();
            cursor.execute(
                "INSERT INTO decks (id, name, user_id) VALUES (%s, %s, %s)",
                (deck_id, deck["name"], user_id)
            )

            print("deck_saved")

            for card in deck.get("cards", []):
                # Insert into cards table
                card_id = generate_uuid4();
                cursor.execute(
                    """
                    INSERT INTO cards (id, deck_id, user_id, front, back, last_revised, level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        card_id,
                        deck_id,
                        user_id,
                        card["front"],
                        card["back"],
                        card["last_revised"],
                        card["level"],
                    )
                )
                print("card_saved")

    # Commit changes and close connection
    conn.commit()
    cursor.close()
    conn.close()


def truncate_db(database_url):
    parsed_url = urlparse(database_url)
    conn = pg8000.connect(
        user=parsed_url.username,
        password=parsed_url.password,
        host=parsed_url.hostname,
        port=parsed_url.port or 5432,
        database=parsed_url.path.lstrip("/")
    )
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM decks",
    )
    cursor.execute(
        "DELETE FROM cards",
    )

# Example usage
database_url = "db_url"

json_files = glob.glob("[id].json")
insert_data_from_json_files(database_url, json_files)
