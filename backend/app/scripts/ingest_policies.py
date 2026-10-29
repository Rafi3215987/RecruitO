from pathlib import Path

from app.services.policy_ingestion import ingest_policy_directory


POLICY_DIRECTORY = Path(__file__).resolve().parents[2] / "policies"


def main() -> None:
    count = ingest_policy_directory(POLICY_DIRECTORY)
    print(f"Stored {count} policy chunks.")


if __name__ == "__main__":
    main()