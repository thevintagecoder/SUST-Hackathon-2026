import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from app.main import app


ROOT_DIRECTORY = Path(__file__).resolve().parents[1]

SAMPLE_CASES_FILE = (
    ROOT_DIRECTORY
    / "tests"
    / "fixtures"
    / "SUST_Preli_Sample_Cases.json"
)

OUTPUT_FILE = (
    ROOT_DIRECTORY
    / "samples"
    / "sample_output.json"
)

SAMPLE_CASE_ID = "SAMPLE-01"


def load_public_cases() -> list[dict[str, Any]]:
    """
    Load the official public sample-case pack.
    """

    if not SAMPLE_CASES_FILE.exists():
        raise FileNotFoundError(
            f"Could not find the sample-case file at "
            f"{SAMPLE_CASES_FILE}"
        )

    with SAMPLE_CASES_FILE.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return data["cases"]


def find_sample_case(
    cases: list[dict[str, Any]],
    case_id: str,
) -> dict[str, Any]:
    """
    Find one public sample case by its official ID.
    """

    for case in cases:
        if case["id"] == case_id:
            return case

    raise ValueError(
        f"Could not find public sample case {case_id}"
    )


def generate_sample_output() -> None:
    """
    Send an official public sample input through the real API and save
    the response as samples/sample_output.json.
    """

    cases = load_public_cases()

    selected_case = find_sample_case(
        cases=cases,
        case_id=SAMPLE_CASE_ID,
    )

    client = TestClient(app)

    response = client.post(
        "/analyze-ticket",
        json=selected_case["input"],
    )

    if response.status_code != 200:
        raise RuntimeError(
            f"The API returned HTTP {response.status_code}: "
            f"{response.text}"
        )

    output = response.json()

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT_FILE.open(
        mode="w",
        encoding="utf-8",
    ) as file:
        json.dump(
            output,
            file,
            ensure_ascii=False,
            indent=2,
        )

        # Add a final newline for clean formatting.
        file.write("\n")

    print(
        f"Generated sample output from {SAMPLE_CASE_ID}"
    )
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    generate_sample_output()