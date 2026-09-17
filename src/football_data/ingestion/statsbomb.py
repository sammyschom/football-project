# code for ingesting the statsbomb open data
# DO NOT NEED TO RUN IF DATA ALREADY EXISTS IN THE DATA FOLDER




import json
from pathlib import Path

import requests


BASE_URL = "https://raw.githubusercontent.com/hudl/open-data/master/data"

PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data" / "raw" / "statsbomb"


def download_file(session, url, output_path, optional=False):
    # Skip files that already exist.
    if output_path.exists():
        print(f"Already exists: {output_path}")
        return True

    output_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        response = session.get(url, timeout=30)

        if response.status_code == 404 and optional:
            print(f"Not available: {url}")
            return False

        response.raise_for_status()

        output_path.write_bytes(response.content)
        print(f"Downloaded: {output_path}")
        return True

    except requests.RequestException as exc:
        print(f"FAILED: {url}")
        print(f"       {exc}")
        return False


def download_competitions(session):
    output_path = DATA_DIR / "competitions.json"
    url = f"{BASE_URL}/competitions.json"

    return download_file(session, url, output_path)


def download_matches_and_related_data(session):
    competitions_path = DATA_DIR / "competitions.json"

    with competitions_path.open("r", encoding="utf-8") as file:
        competitions = json.load(file)

    total_matches = 0
    downloaded_events = 0
    downloaded_lineups = 0
    downloaded_360 = 0
    failed = 0

    for competition in competitions:
        competition_id = competition["competition_id"]
        season_id = competition["season_id"]

        print(
            f"\n=== Competition {competition_id}, "
            f"Season {season_id} ==="
        )

        matches_url = (
            f"{BASE_URL}/matches/"
            f"{competition_id}/{season_id}.json"
        )

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

            # 360 data is optional and only exists for some matches.
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
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    with requests.Session() as session:
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
