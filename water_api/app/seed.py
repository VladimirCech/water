import hashlib
import os
import shutil
import tempfile
from decimal import Decimal
from pathlib import Path

from sqlalchemy import select

from app.db import engine, session_scope
from app.models import Base, Build, Entitlement, Game, User
from app.security import hash_password
from app.storage import ensure_bucket_exists, upload_game_build

# Path to game_skeleton (mounted in Docker)
GAME_SKELETON_PATH = Path("/app/game_skeleton")


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

        # Create Demo Game (uses game_skeleton)
        demo_game = s.execute(select(Game).where(Game.slug == "demo-game")).scalar_one_or_none()
        if not demo_game:
            demo_game = Game(
                name="Demo Game",
                slug="demo-game",
                description="A simple demo game showcasing Water DRM integration. "
                            "Use WASD to move the character around. "
                            "The game validates your license on startup and sends heartbeats to keep the session alive.",
                price=Decimal("9.99"),
            )
            s.add(demo_game)
            s.flush()
            print("✅ Created game: Demo Game")
        else:
            print("ℹ️  Game already exists: Demo Game")

        # Create ZIP from game_skeleton and upload to MinIO
        demo_build = s.execute(
            select(Build).where(Build.game_id == demo_game.id, Build.version == "1.0.0")
        ).scalar_one_or_none()
        
        if not demo_build:
            if GAME_SKELETON_PATH.exists():
                # Create ZIP archive from game_skeleton
                with tempfile.TemporaryDirectory() as tmpdir:
                    zip_base = os.path.join(tmpdir, "demo_game")
                    zip_path = shutil.make_archive(zip_base, "zip", GAME_SKELETON_PATH)
                    
                    # Calculate SHA256
                    with open(zip_path, "rb") as f:
                        digest = hashlib.sha256(f.read()).hexdigest()
                    
                    # Upload to MinIO
                    s3_key = upload_game_build(zip_path, demo_game.slug, "1.0.0")
                    demo_build = Build(
                        game_id=demo_game.id, 
                        version="1.0.0", 
                        s3_key=s3_key, 
                        sha256=digest
                    )
                    s.add(demo_build)
                    s.flush()
                    print(f"✅ Created Demo Game build v1.0.0 from game_skeleton")
                    print(f"   Uploaded to MinIO: {s3_key}")
                    print(f"   SHA256: {digest[:16]}...")
            else:
                print("⚠️  game_skeleton not found at /app/game_skeleton")
                print("   Make sure the volume is mounted in docker-compose.yml")
        else:
            print("ℹ️  Demo Game build already exists: v1.0.0")

        # Create Space Ducks (paid game example)
        space_ducks = s.execute(select(Game).where(Game.slug == "space-ducks")).scalar_one_or_none()
        if not space_ducks:
            space_ducks = Game(
                name="Space Ducks",
                slug="space-ducks",
                description="Quack in space! An epic adventure of ducks exploring the galaxy. "
                            "Guide your duck through asteroid fields and collect cosmic bread crumbs.",
                price=Decimal("9.99"),
            )
            s.add(space_ducks)
            s.flush()
            print("✅ Created game: Space Ducks ($9.99)")
        else:
            print("ℹ️  Game already exists: Space Ducks")

        # Create entitlements
        # Admin owns Demo Game
        admin_demo = s.execute(
            select(Entitlement).where(Entitlement.user_id == admin.id, Entitlement.game_id == demo_game.id)
        ).scalar_one_or_none()
        if not admin_demo:
            s.add(Entitlement(user_id=admin.id, game_id=demo_game.id))
            print("✅ Created entitlement: admin owns Demo Game")
        else:
            print("ℹ️  Entitlement already exists: admin → Demo Game")

        # Testuser owns Demo Game too
        user_demo = s.execute(
            select(Entitlement).where(Entitlement.user_id == u.id, Entitlement.game_id == demo_game.id)
        ).scalar_one_or_none()
        if not user_demo:
            s.add(Entitlement(user_id=u.id, game_id=demo_game.id))
            print("✅ Created entitlement: testuser owns Demo Game")
        else:
            print("ℹ️  Entitlement already exists: testuser → Demo Game")

    print("\n🎉 Seed complete!")
    print("   Users:")
    print("     - testuser / Test1234 (email: test@example.com)")
    print("     - admin / Admin1234 (email: admin@example.com)")
    print("   Games:")
    print("     - Demo Game (Free, slug: demo-game) ← with actual game!")
    print("     - Space Ducks ($9.99, slug: space-ducks)")
    print("   Entitlements:")
    print("     - admin owns Demo Game")
    print("     - testuser owns Demo Game")


if __name__ == "__main__":
    main()
