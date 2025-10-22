from pathlib import Path

import pytest
from sqlalchemy import Integer, String, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from astrbot_canary.core.db import AstrbotDatabase


class Base(DeclarativeBase): ...


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
    db = AstrbotDatabase.init_base(db_path, Base)
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
    rows = db.execute(
        "SELECT username, email FROM users WHERE username=:u",
        {"u": "bob"},
    )
    assert rows[0][0] == "bob"
    # 6. 异步事务
    async with db.atransaction() as session:
        result = await session.execute(
            text("SELECT username FROM users WHERE username=:u"),
            {"u": "bob"},
        )
        row = result.first()
        assert row is not None
        assert row[0] == "bob"
    # 7. 异步关闭
    await db.aclose()
    assert db.async_engine is None
    assert db.AsyncSessionLocal is None


def test_session_scope_not_connected(tmp_path: Path):
    db = AstrbotDatabase(tmp_path / "not_exist.db")
    with pytest.raises(RuntimeError, match="Database not connected"):
        with db.session_scope():
            pass


def test_bind_base(tmp_path: Path):
    # 覆盖engine为None分支，需保证Base2已定义
    class Base2(DeclarativeBase):
        pass

    class Item(Base2):
        __tablename__ = "items"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        name: Mapped[str] = mapped_column(String)

    db2 = AstrbotDatabase(tmp_path / "bind_base2.db")  # 此时engine为None
    db2.bind_base(Base2)
    rows2 = db2.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='items'",
    )
    assert rows2 and rows2[0][0] == "items"
    dbfile = tmp_path / "bind_base.db"
    db = AstrbotDatabase.connect(dbfile)

    class Base2(DeclarativeBase):
        pass

    class Item(Base2):
        __tablename__ = "items"
        id: Mapped[int] = mapped_column(Integer, primary_key=True)
        name: Mapped[str] = mapped_column(String)

    db.bind_base(Base2)
    # 检查表是否创建成功
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='items'",
    )
    assert rows and rows[0][0] == "items"
    db.close()
    db = AstrbotDatabase(tmp_path / "not_exist.db")
    with pytest.raises(RuntimeError, match="Database not connected"):
        with db.session_scope():
            pass


def test_execute_not_connected(tmp_path: Path):
    db = AstrbotDatabase(tmp_path / "not_exist.db")
    with pytest.raises(RuntimeError, match="Database not connected"):
        db.execute("SELECT 1")


def test_execute_params_none_and_no_rows(tmp_path: Path):
    dbfile = tmp_path / "test.db"
    db = AstrbotDatabase.connect(dbfile)
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    # 非查询语句，params=None，result.returns_rows=False
    assert db.execute("INSERT INTO t (id) VALUES (1)") is None
    db.close()


def test_execute_params_and_returns_rows(tmp_path: Path):
    dbfile = tmp_path / "test.db"
    db = AstrbotDatabase.connect(dbfile)
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    db.execute("INSERT INTO t (id) VALUES (2)")
    rows = db.execute("SELECT id FROM t WHERE id=:id", {"id": 2})
    assert rows[0][0] == 2
    db.close()


def test_session_scope_rollback(tmp_path: Path):
    dbfile = tmp_path / "test.db"
    db = AstrbotDatabase.connect(dbfile)
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    try:
        with db.session_scope() as session:
            session.execute("INSERT INTO t (id) VALUES (3)")
            raise Exception("force rollback")
    except Exception:
        pass
    # 插入未提交，应无数据
    rows = db.execute("SELECT * FROM t WHERE id=3")
    assert rows == []
    db.close()


def test_transaction_rollback(tmp_path: Path):
    dbfile = tmp_path / "test.db"
    db = AstrbotDatabase.connect(dbfile)
    db.execute("CREATE TABLE t (id INTEGER PRIMARY KEY)")
    try:
        with db.transaction() as session:
            session.execute("INSERT INTO t (id) VALUES (4)")
            raise Exception("force rollback")
    except Exception:
        pass
    rows = db.execute("SELECT * FROM t WHERE id=4")
    assert rows == []
    db.close()


def test_enter_exit(tmp_path: Path):
    dbfile = tmp_path / "test.db"
    db = AstrbotDatabase.connect(dbfile)
    with db as db2:
        assert db2.engine is not None
    assert db.engine is None  # __exit__ 应关闭引擎


def test_aenter_aexit(tmp_path: Path):
    import asyncio

    dbfile = tmp_path / "test.db"
    db = AstrbotDatabase.connect(dbfile)

    async def run():
        async with db as db2:
            assert db2.engine is not None
        assert db.async_engine is None

    asyncio.run(run())


def test_enter_auto_connect(tmp_path: Path):
    dbfile = tmp_path / "test_auto_connect.db"
    db = AstrbotDatabase(dbfile)  # 此时 engine 为 None
    # __enter__ 应自动 connect
    with db as db2:
        assert db2.engine is not None
    assert db.engine is None


@pytest.mark.asyncio
async def test_aenter_auto_connect(tmp_path: Path):
    dbfile = tmp_path / "test_auto_connect_async.db"
    db = AstrbotDatabase(dbfile)
    # 此时engine/async_engine均为None，__aenter__应自动connect
    async with db as db2:
        assert db2.async_engine is not None
    assert db.async_engine is None


def test_exit_exception(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    dbfile = tmp_path / "test_exit_exception.db"
    db = AstrbotDatabase.connect(dbfile)

    # monkeypatch close 抛异常，__exit__应捕获
    def bad_close():
        raise Exception("close error")

    db.close = bad_close
    try:
        db.__exit__(None, None, None)
    except Exception:
        pytest.fail("__exit__ should suppress exception")


@pytest.mark.asyncio
async def test_aexit_exception(monkeypatch: pytest.MonkeyPatch, tmp_path: Path):
    dbfile = tmp_path / "test_aexit_exception.db"
    db = AstrbotDatabase.connect(dbfile)

    async def bad_aclose():
        raise Exception("aclose error")

    db.aclose = bad_aclose
    try:
        await db.__aexit__(None, None, None)
    except Exception:
        pytest.fail("__aexit__ should suppress exception")


@pytest.mark.asyncio
async def test_atransaction_rollback(tmp_path: Path):
    dbfile = tmp_path / "test_atrans_rollback.db"
    db = AstrbotDatabase.connect(dbfile)
    # 初始化async_engine/AsyncSessionLocal
    async with db.atransaction() as session:
        pass

    # patch session.rollback 以检测被调用
    class DummySession:
        def __init__(self):
            self.rolled = False

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def rollback(self):
            self.rolled = True

        class DummyBegin:
            async def __aenter__(self_):
                return self_

            async def __aexit__(self_, exc_type, exc, tb):
                return False

        def begin(self):
            return DummySession.DummyBegin()

    dummy = DummySession()

    class DummyAsyncSessionLocal:
        def __call__(self):
            class Ctx:
                async def __aenter__(self_):
                    return dummy

                async def __aexit__(self_, exc_type, exc, tb):
                    return False

            return Ctx()

    db.AsyncSessionLocal = DummyAsyncSessionLocal()
    # 触发异常，检查rollback
    with pytest.raises(ValueError):
        async with db.atransaction() as session:
            raise ValueError("force error")
    assert dummy.rolled
