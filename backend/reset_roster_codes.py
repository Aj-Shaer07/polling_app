import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from app.database import SessionLocal
from app.services.roster import initialize_roster

def main():
    db = SessionLocal()
    try:
        roster = initialize_roster(db, force_reset=True)
        print(f"\n=======================================================")
        print(f"  BELIEF STRESS TEST — ELIGIBLE ROSTER INITIALIZED (45)")
        print(f"=======================================================")
        print(f"{'Student ID':<15} | {'Activation Status':<25}")
        print("-" * 45)
        for c in sorted(roster, key=lambda x: x["student_id"]):
            print(f"{c['student_id']:<15} | {'Ready for password setup':<25}")
        print(f"=======================================================\n")
    finally:
        db.close()

if __name__ == "__main__":
    main()
