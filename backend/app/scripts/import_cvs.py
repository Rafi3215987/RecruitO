"""Import a folder of CVs for one job, screen them, and report the timing (N1).

Usage inside the API container (``test-data`` is mounted read-only at /data/test-data):

    docker compose exec api python -m app.scripts.import_cvs --job-id 1 /data/test-data/sample-cvs

The folder stays on the host and is git-ignored (N14). The CVs become
non-login imported candidates; see ``app.services.cv_import``.
"""
import argparse
import time
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import select

load_dotenv()

from app.db.session import SessionLocal
from app.graphs.application_ranking_graph import application_ranking_graph
from app.models.screening_score import ScreeningScore
from app.services.cv_import import import_resume_file
from app.services.screening_queue import dispatch_pending_screenings


def _score_states(application_ids: list[int]) -> dict[int, str]:
    with SessionLocal() as session:
        rows = session.execute(
            select(ScreeningScore.application_id, ScreeningScore.status)
            .where(ScreeningScore.application_id.in_(application_ids))
            .order_by(ScreeningScore.created_at, ScreeningScore.id)
        ).all()
    return {application_id: status for application_id, status in rows}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("folder", type=Path)
    parser.add_argument("--job-id", type=int, required=True)
    parser.add_argument("--timeout", type=int, default=900, help="seconds to wait for screening")
    args = parser.parse_args()

    files = sorted(path for path in args.folder.iterdir() if path.suffix.lower() in {".pdf", ".docx"})
    if not files:
        raise SystemExit(f"No PDF or DOCX files found in {args.folder}")

    started = time.monotonic()
    results = [import_resume_file(args.job_id, path.name, path.read_bytes(), actor_user_id=None) for path in files]
    imported_at = time.monotonic()
    for item in results:
        print(f"{item['status']:>9}  {item['file_name']}" + (f"  ({item['error']})" if item.get("error") else ""))

    application_ids = [item["application_id"] for item in results if item.get("application_id")]
    if not application_ids:
        raise SystemExit("Nothing was imported")

    deadline = started + args.timeout
    states = _score_states(application_ids)
    while any(state in {"pending", "processing"} for state in states.values()) and time.monotonic() < deadline:
        if not dispatch_pending_screenings():
            time.sleep(2)
        states = _score_states(application_ids)
    finished = time.monotonic()

    counts: dict[str, int] = {}
    for state in states.values():
        counts[state] = counts.get(state, 0) + 1
    print()
    outcomes = {status: sum(1 for item in results if item["status"] == status)
                for status in ("queued", "duplicate", "rejected")}
    print(f"CVs: {len(files)}  {outcomes}  score states: {counts}")
    print(f"Import time: {imported_at - started:.1f} s")
    print(f"Parse, screen, score and rank time: {finished - started:.1f} s total, "
          f"{(finished - started) / len(application_ids):.1f} s per CV")

    ranking = application_ranking_graph.invoke({"job_id": args.job_id})
    print()
    print("Rank  Score   Candidate")
    for applicant in ranking.get("applications", []):
        if applicant["application_id"] in application_ids:
            score = f"{applicant['total_score']:.2f}" if applicant["total_score"] is not None else applicant["status"]
            print(f"{applicant['rank'] or '-':>4}  {score:>6}  {applicant['candidate_name']}")


if __name__ == "__main__":
    main()
