import hashlib
import os

from sqlalchemy import select

from app.db import engine, session_scope
from app.models import Base, Build, Entitlement, Game, User
from app.security import hash_password


def main():
    Base.metadata.create_all(bind=engine)
    with session_scope() as s:
        u = s.execute(select(User).where(User.email == "test@example.com")).scalar_one_or_none()
        if not u:
            u = User(email="test@example.com", password_hash=hash_password("test"))
            s.add(u)
            s.flush()
        g = s.execute(select(Game).where(Game.slug == "space-ducks")).scalar_one_or_none()
        if not g:
            g = Game(name="Space Ducks", slug="space-ducks", description="Quack in space!")
            s.add(g)
            s.flush()
        build_dir = os.path.join(os.path.dirname(__file__), "..", "builds")
        os.makedirs(build_dir, exist_ok=True)
        dummy_path = os.path.abspath(os.path.join(build_dir, "space-ducks-1.0.zip"))
        if not os.path.exists(dummy_path):
            with open(dummy_path, "wb") as f:
                f.write(b"DEMO-BUILD\n")
        with open(dummy_path, "rb") as f:
            digest = hashlib.sha256(f.read()).hexdigest()
        b = s.execute(select(Build).where(Build.game_id == g.id, Build.version == "1.0")).scalar_one_or_none()
        if not b:
            b = Build(game_id=g.id, version="1.0", file_path=dummy_path, sha256=digest)
            s.add(b)
            s.flush()
        e = s.execute(
            select(Entitlement).where(Entitlement.user_id == u.id, Entitlement.game_id == g.id)
        ).scalar_one_or_none()
        if not e:
            s.add(Entitlement(user_id=u.id, game_id=g.id))
    print("Seed complete. User: test@example.com / test")


if __name__ == "__main__":
    main()
