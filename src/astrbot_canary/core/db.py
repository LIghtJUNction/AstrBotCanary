from __future__ import annotations
from collections.abc import Generator, AsyncGenerator
from pathlib import Path

from typing import Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from sqlalchemy.engine import Engine
from contextlib import contextmanager, asynccontextmanager

class AstrbotDatabase():
    db_path: Path
    database_url: str
    engine: Engine | None
    session: Session | None
    base: Any

    def __init__(self, db_path: Path) -> None:
        # 只设置基本属性
        self.db_path = db_path
        self.database_url = f"sqlite:///{db_path}"
        self.engine = None
        self.session = None
        self.base = None

    @classmethod
    def connect(cls, db_path: Path) -> AstrbotDatabase:
        instance = cls(db_path)
        # 在这里创建 engine 和 session
        instance.engine = create_engine(instance.database_url, future=True)
        SessionLocal: sessionmaker[Session] = sessionmaker(bind=instance.engine, future=True)
        instance.session = SessionLocal()
        return instance

    @classmethod
    def init_db(cls, db_path: Path, base: Any) -> AstrbotDatabase:
        """自动初始化数据库表结构
        db_path: Path - 数据库文件路径
        base: SQLAlchemy declarative_base 对象，包含所有模型的基类

        """
        # 确保父目录存在

        db_path.parent.mkdir(parents=True, exist_ok=True)

        engine = create_engine(f"sqlite:///{str(db_path)}", future=True)
        base.metadata.create_all(bind=engine)
        instance: AstrbotDatabase = cls.connect(db_path)
        instance.base = base
        return instance

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


    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """上下文管理器/装饰器，自动提交/回滚事务"""
        if self.session is None:
            raise Exception("Database not connected.")       
        try:
            yield self.session
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

    @asynccontextmanager
    async def atransaction(self) -> AsyncGenerator[Session, None]:
        """异步上下文管理器/装饰器，自动提交/回滚事务"""
        if self.session is None:
            raise Exception("Database not connected.")
        try:
            yield self.session
            self.session.commit()
        except Exception:
            self.session.rollback()
            raise

if __name__ == "__main__":
    from sqlalchemy import Column, Integer, String
    Base = declarative_base()
    db_path = Path("./test/astrbot_canary.db")

    # 定义复杂模型
    class User(Base):
        __tablename__ = "users"
        id = Column(Integer, primary_key=True, autoincrement=True)
        username = Column(String, unique=True, index=True)
        email = Column(String, unique=True)
        def __repr__(self):
            return f"<User(id={self.id}, username={self.username}, email={self.email})>"

    # 初始化数据库并创建表
    db = AstrbotDatabase.init_db(db_path, Base)

    # 1. 使用 ORM 批量插入用户（避免重复）
    users_data = [
        ("alice", "alice@example.com"),
        ("bob", "bob@example.com"),
        ("charlie", "charlie@example.com"),
    ]
    with db.transaction() as session:
        for username, email in users_data:
            # 检查是否已存在
            existing = session.get(User, username)
            if not existing:
                user = User(username=username, email=email)
                session.add(user)
    print("ORM 批量插入用户成功")

    # 2. 使用 ORM 查询所有用户
    with db.transaction() as session:
        users = session.query(User).all()
        print("所有用户:", users)

    # 3. 使用 ORM 更新用户邮箱
    with db.transaction() as session:
        user = session.get(User, "alice")
        if user:
            user.email = "alice@new.com"  # type: ignore[attr]
    print("ORM 更新邮箱成功")
    with db.transaction() as session:
        user = session.get(User, "alice")
        print("更新后:", user)

    # 4. 使用 ORM 删除用户
    with db.transaction() as session:
        user = session.get(User, "bob")
        if user:
            session.delete(user)
    print("ORM 删除用户成功")
    with db.transaction() as session:
        users = session.query(User).all()
        print("删除后:", users)

    # 5. 事务测试：ORM 批量插入+回滚
    try:
        with db.transaction() as session:
            dave = User(username="dave", email="dave@example.com")
            eve = User(username="eve", email="eve@example.com")
            session.add(dave)
            session.add(eve)
            raise Exception("模拟事务失败，触发回滚")
    except Exception as e:
        print("事务回滚成功，异常:", e)
    with db.transaction() as session:
        users = session.query(User).all()
        print("事务后:", users)

    # 6. 异常断言：插入重复用户名
    try:
        with db.transaction() as session:
            duplicate = User(username="alice", email="alice@dup.com")
            session.add(duplicate)
            session.commit()  # 强制提交以触发异常
    except Exception as e:
        print("插入重复用户名异常捕获:", e)

    db.close()
    print("数据库关闭")