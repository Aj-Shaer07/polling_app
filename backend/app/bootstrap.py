import argparse
import sys
import os

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.database import SessionLocal, Base, engine
from app.models.user import User, UserRole
from app.services.auth import hash_password
from app.services.roster import initialize_roster, get_standard_eligible_student_ids
from app.services.audit import log_audit_event


def bootstrap_admin_and_roster(username: str, email: str, password: str, init_roster: bool = True):
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if len(password) < 4:
            print("[!] Error: Password must be at least 4 characters.")
            return

        # Check if admin already exists
        existing_admin = db.query(User).filter((User.username == username) | (User.email == email)).first()
        if existing_admin:
            existing_admin.username = username
            existing_admin.email = email
            existing_admin.hashed_password = hash_password(password)
            existing_admin.role = UserRole.ADMIN
            existing_admin.is_active = True
            db.commit()
            print(f"[+] Existing Admin '{username}' credentials synchronized.")
        else:
            admin = User(
                username=username,
                email=email,
                hashed_password=hash_password(password),
                role=UserRole.ADMIN,
                is_active=True,
            )
            db.add(admin)
            db.commit()
            db.refresh(admin)
            log_audit_event(
                db=db,
                action="ADMIN_BOOTSTRAPPED",
                resource_type="users",
                resource_id=admin.id,
                details={"username": username, "email": email},
            )
            print(f"[+] Initial Admin '{username}' successfully created.")

        if init_roster:
            print("[*] Initializing eligible roster (exactly 45 students)...")
            codes = initialize_roster(db=db, force_reset=False)
            if codes:
                print(f"[+] Initialized {len(codes)} eligible students.")
                print(f"[+] Generated one-time activation credentials for all 45 students.")
            else:
                print("[*] Eligible roster already initialized.")

    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Bootstrap initial admin and eligible student roster.")
    parser.add_argument("--username", default="admin", help="Admin username")
    parser.add_argument("--email", default="admin@classroom.edu", help="Admin email")
    parser.add_argument("--password", required=True, help="Secure password for initial admin")
    parser.add_argument("--skip-roster", action="store_true", help="Skip initializing student roster")

    args = parser.parse_args()
    bootstrap_admin_and_roster(
        username=args.username,
        email=args.email,
        password=args.password,
        init_roster=not args.skip_roster,
    )
