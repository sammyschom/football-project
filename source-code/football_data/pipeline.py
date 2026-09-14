import requests


COMPETITIONS_URL = (
    "https://raw.githubusercontent.com/hudl/open-data/master/"
    "data/competitions.json"
)

def main():
    response = requests.get(COMPETITIONS_URL)

    response.raise_for_status()

    with open("data/raw/competitions.json", "wb") as file:
        file.write(response.content)

    print("Downloaded competitions.json")


if __name__ == "__main__":
    main()