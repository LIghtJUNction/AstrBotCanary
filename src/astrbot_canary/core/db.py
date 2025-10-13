from __future__ import annotations
from collections.abc import Generator
from pathlib import Path
from types import TracebackType
from typing import Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.engine import Engine
from contextlib import contextmanager

class AstrbotDatabase():
    database_url: str
    engine: Engine | None
    session: Session | None

    def __init__(self, db_path: Path) -> None:
        # 实例属性，实际可重定义，不是全局常量
        self.database_url = f"sqlite:///{db_path}"
        self.engine = create_engine(self.database_url, future=True)
        SessionLocal: sessionmaker[Session] = sessionmaker(bind=self.engine, future=True)
        self.session = SessionLocal()

    @classmethod
    def connect(cls, db_path: Path) -> AstrbotDatabase:
        return cls(db_path)

    @classmethod
    def init_db(cls, db_path: Path, base: Any) -> None:
        """自动初始化数据库表结构"""
        # 确保父目录存在

        db_path.parent.mkdir(parents=True, exist_ok=True)

        engine = create_engine(f"sqlite:///{str(db_path)}", future=True)
        base.metadata.create_all(bind=engine)

    def execute(self, query: str, params: Any = None) -> Any:
        if self.session is None:
            raise Exception("Database not connected.")
        try:
            if params is None:
                result = self.session.execute(text(query))
            else:
                result = self.session.execute(text(query), params)
            self.session.commit()
            try:
                return result.fetchall()
            except Exception:
                return None
        except Exception as e:
            self.session.rollback()
            raise e


    def close(self) -> None:
        if self.session:
            self.session.close()
            self.session = None
        if self.engine:
            self.engine.dispose()
            self.engine = None

    def get_session(self) -> Session:
        if self.session is None:
            raise Exception("Session not initialized.")
        return self.session

    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """上下文管理器/装饰器，自动提交/回滚事务"""
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise

    def __enter__(self) -> AstrbotDatabase:
        return self
    def __exit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        self.close()
    async def __aenter__(self) -> AstrbotDatabase:
        return self
    async def __aexit__(self, exc_type: type[BaseException] | None, exc_val: BaseException | None, exc_tb: TracebackType | None) -> None:
        self.close()


if __name__ == "__main__":
    from sqlalchemy import Column, Integer, String
    Base = declarative_base()
    db_path = Path("./test/astrbot_canary.db")
    AstrbotDatabase.init_db(db_path, Base)

    # 定义复杂模型
    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True, autoincrement=True)
        username = Column(String, unique=True, index=True)
        email = Column(String, unique=True)
        def __repr__(self):
            return f"<User(id={self.id}, username={self.username}, email={self.email})>"

    # 重新初始化表结构
    AstrbotDatabase.init_db(db_path, Base)

    db = AstrbotDatabase.connect(db_path)

    # 1. 批量插入用户（避免重复报错）
    users = [
        ("alice", "alice@example.com"),
        ("bob", "bob@example.com"),
        ("charlie", "charlie@example.com"),
    ]
    for username, email in users:
        db.execute("INSERT OR IGNORE INTO users (username, email) VALUES (:username, :email)", {"username": username, "email": email})

    print("批量插入用户成功")

    # 2. 查询所有用户
    rows = db.execute("SELECT * FROM users")
    print("所有用户:", rows)

    # 3. 更新用户邮箱
    db.execute("UPDATE users SET email=:email WHERE username=:username", {"email": "alice@new.com", "username": "alice"})
    print("更新邮箱成功")
    print("更新后:", db.execute("SELECT * FROM users WHERE username=:username", {"username": "alice"}))

    # 4. 删除用户
    db.execute("DELETE FROM users WHERE username=:username", {"username": "bob"})
    print("删除用户成功")
    print("删除后:", db.execute("SELECT * FROM users"))

    # 5. 事务测试：批量插入+回滚
    try:
        with db.transaction() as session:
            session.execute(text("INSERT INTO users (username, email) VALUES (:username, :email)"), {"username": "dave", "email": "dave@example.com"})
            session.execute(text("INSERT INTO users (username, email) VALUES (:username, :email)"), {"username": "eve", "email": "eve@example.com"})
            raise Exception("模拟事务失败，触发回滚")
    except Exception as e:
        print("事务回滚成功，异常:", e)
    print("事务后:", db.execute("SELECT * FROM users"))

    # 6. 异常断言：插入重复用户名
    try:
        db.execute("INSERT INTO users (username, email) VALUES (:username, :email)", {"username": "alice", "email": "alice@dup.com"})
    except Exception as e:
        print("插入重复用户名异常捕获:", e)

    db.close()
    print("数据库关闭")