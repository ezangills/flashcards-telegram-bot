import json
import pg8000
from urllib.parse import urlparse
import glob
import os


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
            cursor.execute(
                "INSERT INTO decks (id, name, user_id) VALUES (%s, %s, %s)",
                (deck["id"], deck["name"], user_id)
            )

            print("deck_saved")

            for card in deck.get("cards", []):
                # Insert into cards table
                cursor.execute(
                    """
                    INSERT INTO cards (id, deck_id, user_id, front, back, last_revised, level)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        card["id"],
                        deck["id"],
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


# Example usage
database_url = ""
json_files = glob.glob("34268343.json")
insert_data_from_json_files(database_url, json_files)

json_files = glob.glob("52882608.json")
insert_data_from_json_files(database_url, json_files)

json_files = glob.glob("190177690.json")
insert_data_from_json_files(database_url, json_files)

json_files = glob.glob("201428145.json")
insert_data_from_json_files(database_url, json_files)
