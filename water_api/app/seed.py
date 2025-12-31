import hashlib
import os
import tempfile
from decimal import Decimal

from sqlalchemy import select

from app.db import engine, session_scope
from app.models import Base, Build, Entitlement, Game, User
from app.security import hash_password
from app.storage import ensure_bucket_exists, upload_game_build


def main():
    """Seed database with demo data and upload demo build to MinIO."""
    Base.metadata.create_all(bind=engine)

    ensure_bucket_exists()

    with session_scope() as s:
        # Create demo user
        u = s.execute(select(User).where(User.email == "test@example.com")).scalar_one_or_none()
        if not u:
            u = User(
                username="testuser",
                email="test@example.com",
                password_hash=hash_password("Test1234"),
            )
            s.add(u)
            s.flush()
            print("✅ Created user: testuser (test@example.com)")
        else:
            print("ℹ️  User already exists: test@example.com")

        # Create admin user
        admin = s.execute(select(User).where(User.email == "admin@example.com")).scalar_one_or_none()
        if not admin:
            admin = User(
                username="admin",
                email="admin@example.com",
                password_hash=hash_password("Admin1234"),
                role="admin",
            )
            s.add(admin)
            s.flush()
            print("✅ Created admin: admin (admin@example.com)")
        else:
            print("ℹ️  Admin already exists: admin@example.com")

        # Create demo game
        g = s.execute(select(Game).where(Game.slug == "space-ducks")).scalar_one_or_none()
        if not g:
            g = Game(
                name="Space Ducks",
                slug="space-ducks",
                description="Quack in space! An epic adventure of ducks exploring the galaxy.",
                price=Decimal("9.99"),
            )
            s.add(g)
            s.flush()
            print("✅ Created game: Space Ducks ($9.99)")
        else:
            print("ℹ️  Game already exists: Space Ducks")

        # Create dummy build file
        dummy_content = b"DEMO-BUILD: Space Ducks v1.0\nThis is a demo game build.\n"
        digest = hashlib.sha256(dummy_content).hexdigest()

        # Check if build already exists
        b = s.execute(select(Build).where(Build.game_id == g.id, Build.version == "1.0")).scalar_one_or_none()
        if not b:
            # Upload to MinIO using temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix=".zip") as tmp:
                tmp.write(dummy_content)
                tmp_path = tmp.name

            try:
                s3_key = upload_game_build(tmp_path, g.slug, "1.0")
                b = Build(game_id=g.id, version="1.0", s3_key=s3_key, sha256=digest)
                s.add(b)
                s.flush()
                print(f"✅ Created build v1.0 and uploaded to MinIO: {s3_key}")
            finally:
                os.unlink(tmp_path)
        else:
            print("ℹ️  Build already exists: v1.0")

        # Create entitlement
        e = s.execute(
            select(Entitlement).where(Entitlement.user_id == u.id, Entitlement.game_id == g.id)
        ).scalar_one_or_none()
        if not e:
            s.add(Entitlement(user_id=u.id, game_id=g.id))
            print("✅ Created entitlement: test@example.com owns Space Ducks")
        else:
            print("ℹ️  Entitlement already exists")

    print("\n🎉 Seed complete!")
    print("   User:  testuser / Test1234 (email: test@example.com)")
    print("   Admin: admin / Admin1234 (email: admin@example.com)")
    print("   Game:  Space Ducks ($9.99, slug: space-ducks)")
    print("   Build: v1.0 available for download")


if __name__ == "__main__":
    main()
