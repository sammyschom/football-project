# code for ingesting the statsbomb open data
# DO NOT NEED TO RUN IF DATA ALREADY EXISTS IN THE LOCAL DATA FOLDER!

import json
from pathlib import Path

import requests

# Where the StatsBomb open data is hosted on GitHub.
BASE_URL = "https://raw.githubusercontent.com/hudl/open-data/master/data"

# football-project root directory 
PROJECT_ROOT = Path(__file__).resolve().parents[3]

# where the RAW StatsBomb data will be stored locally
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "statsbomb"


def download_file(session, url, output_path, optional=False):
    """
    session: the HTTP session to use for downloading the file
    url: the URL of the file to download
    output_path: the LOCAL path where the file should be saved
    optional: whether missing file should be treated as optional (default: False)

    Returns True if the file was downloaded successfully or already exists, 
    False if the file was not found (404) and is optional, 
    and raises an exception for any other HTTP error.
    """

    # Skip files that already exist.
    if output_path.exists():
        print(f"Already exists: {output_path}")
        return True # end function early if file exists already
    
    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = session.get(url, timeout=30) # ask the server for the file

        if response.status_code == 404 and optional: # particularly for the 360 data, which is not available for all matches 
            print(f"Not available: {url}")
            return False

        # Raise an exception for any other HTTP error status codes. i.e. 500, 403, etc.
        response.raise_for_status()

        # Write the content of the response to the output file.
        output_path.write_bytes(response.content)
        print(f"Downloaded: {output_path}")
        return True

    # Handle any request exceptions that may occur during the download process.
    except requests.RequestException as exc:
        print(f"FAILED: {url}")
        print(f"       {exc}")
        return False

# competitions metadata
def download_competitions(session):
    # my bit
    output_path = DATA_DIR / "competitions.json"
    # statsbomb bit
    url = f"{BASE_URL}/competitions.json"

    return download_file(session, url, output_path)


def download_matches_and_related_data(session):
    """
    Download all matches and their related data for each competition.
    """

    competitions_path = DATA_DIR / "competitions.json"

    with competitions_path.open("r", encoding="utf-8") as file: 
        competitions = json.load(file) # load the competitions metadata from the local file -- into DICTIONARY

    # init counters
    total_matches = 0
    downloaded_events = 0
    downloaded_lineups = 0
    downloaded_360 = 0
    failed = 0

    
    for competition in competitions:
        # Loop through each competition and season to download matches and related data
        competition_id = competition["competition_id"]
        season_id = competition["season_id"]

        print(
            f"\n=== Competition {competition_id}, "
            f"Season {season_id} ==="
        )

        # creating the URLs as would find in statsbomb data 
        matches_url = (
            f"{BASE_URL}/matches/"
            f"{competition_id}/{season_id}.json"
        )

        # creating the local path to save the matches data
        matches_path = (
            DATA_DIR
            / "matches"
            / str(competition_id)
            / f"{season_id}.json"
        )

        if not download_file(session, matches_url, matches_path):
            failed += 1
            continue

        with matches_path.open("r", encoding="utf-8") as file:
            matches = json.load(file)

        print(f"Matches found: {len(matches)}")

        # another for loop, a lot of ingestion!
        for match in matches:
            match_id = match["match_id"]
            total_matches += 1

            # Events
            events_path = DATA_DIR / "events" / f"{match_id}.json"

            if events_path.exists():
                print(f"Already exists: {events_path}")
            else:
                success = download_file(
                    session,
                    f"{BASE_URL}/events/{match_id}.json",
                    events_path,
                )

                if success:
                    downloaded_events += 1
                else:
                    failed += 1

            # Lineups
            lineups_path = DATA_DIR / "lineups" / f"{match_id}.json"

            if lineups_path.exists():
                print(f"Already exists: {lineups_path}")
            else:
                success = download_file(
                    session,
                    f"{BASE_URL}/lineups/{match_id}.json",
                    lineups_path,
                )

                if success:
                    downloaded_lineups += 1
                else:
                    failed += 1

            # 360 data only exists for some matches.
            three_sixty_path = (
                DATA_DIR / "three-sixty" / f"{match_id}.json"
            )

            if three_sixty_path.exists():
                print(f"Already exists: {three_sixty_path}")
            else:
                success = download_file(
                    session,
                    f"{BASE_URL}/three-sixty/{match_id}.json",
                    three_sixty_path,
                    optional=True,
                )

                if success:
                    downloaded_360 += 1


    # Print summary of the download process
    print("\n========================================")
    print("DOWNLOAD COMPLETE")
    print("========================================")
    print(f"Matches processed:     {total_matches}")
    print(f"Events downloaded:     {downloaded_events}")
    print(f"Lineups downloaded:    {downloaded_lineups}")
    print(f"360 files downloaded:  {downloaded_360}")
    print(f"Failures:              {failed}")
    print("========================================")


def main():
    # Ensure the data directory exists
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
        # Set a custom User-Agent header to identify the downloader (needed?)
        session.headers.update(
            {
                "User-Agent": "football-project-statsbomb-downloader"
            }
        )

        if not download_competitions(session):
            raise RuntimeError("Could not download competitions.json")

        download_matches_and_related_data(session)


if __name__ == "__main__":
    main()
