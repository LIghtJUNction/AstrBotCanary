import pytest
from pathlib import Path
from sqlalchemy import Integer, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from astrbot_canary.core.db import AstrbotDatabase

class Base(DeclarativeBase):
    ...


class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String, unique=True, index=True)
    email: Mapped[str] = mapped_column(String, unique=True)

@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    db_file = tmp_path / "test_db.sqlite3"
    return db_file

@pytest.fixture
def db(db_path: Path):
    db = AstrbotDatabase.init_db(db_path, Base)
    yield db
    db.close()

@pytest.mark.asyncio
async def test_astrbot_database_sync_and_async(db: AstrbotDatabase):
    # 1. ORM 插入
    with db.transaction() as session:
        user = User(username="alice", email="alice@example.com")
        session.add(user)
    # 2. ORM 查询
    with db.transaction() as session:
        user = session.query(User).filter_by(username="alice").one_or_none()
        assert user is not None
        assert user.email == "alice@example.com"
    # 3. ORM 更新
    with db.transaction() as session:
        user = session.query(User).filter_by(username="alice").one_or_none()
        assert user is not None
        user.email = "alice@new.com"
    with db.transaction() as session:
        user = session.query(User).filter_by(username="alice").one_or_none()
        assert user is not None
        assert user.email == "alice@new.com"
    # 4. ORM 删除
    with db.transaction() as session:
        user = session.query(User).filter_by(username="alice").one_or_none()
        assert user is not None
        session.delete(user)
    with db.transaction() as session:
        user = session.query(User).filter_by(username="alice").one_or_none()
        assert user is None
    # 5. execute 原生 SQL
    with db.transaction() as session:
        session.add(User(username="bob", email="bob@example.com"))
    rows = db.execute("SELECT username, email FROM users WHERE username=:u", {"u": "bob"})
    assert rows[0][0] == "bob"
    # 6. 异步事务
    async with db.atransaction() as session:
        result = await session.execute(text("SELECT username FROM users WHERE username=:u"), {"u": "bob"})
        row = result.first()
        assert row is not None
        assert row[0] == "bob"
    # 7. 异步关闭
    await db.aclose()
    assert db.async_engine is None
    assert db.AsyncSessionLocal is None
