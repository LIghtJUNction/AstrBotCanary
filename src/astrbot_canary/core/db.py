from __future__ import annotations
from collections.abc import Generator, AsyncGenerator
from pathlib import Path
from typing import Any
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
)
from contextlib import contextmanager, asynccontextmanager

class AstrbotDatabase:
    db_path: Path
    database_url: str
    engine: Engine | None
    SessionLocal: sessionmaker[Session] | None
    async_engine: AsyncEngine | None
    AsyncSessionLocal: async_sessionmaker[AsyncSession] | None
    base: Any

    def __init__(self, db_path: Path) -> None:
        # 只设置基本属性
        self.db_path = db_path
        # 使用 resolve 并替换反斜杠，保证 Windows 路径在 sqlite url 中正确
        db_str = str(db_path.resolve()).replace("\\", "/")
        self.database_url = f"sqlite:///{db_str}"
        self.engine = None
        self.SessionLocal = None
        self.async_engine = None
        self.AsyncSessionLocal = None
        self.base = None

    @classmethod
    def connect(cls, db_path: Path) -> "AstrbotDatabase":
        instance = cls(db_path)
        # 在这里创建 engine 和 session factory（不要在实例上保存单个 Session）
        instance.engine = create_engine(instance.database_url, future=True)
        instance.SessionLocal = sessionmaker(bind=instance.engine, future=True, expire_on_commit=False)
        return instance

    @classmethod
    def init_db(cls, db_path: Path, base: Any) -> "AstrbotDatabase":
        """自动初始化数据库表结构
        db_path: Path - 数据库文件路径
        base: SQLAlchemy declarative_base 对象，包含所有模型的基类

        """
        # 确保父目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用临时 engine 创建表，然后 dispose
        db_str = str(db_path.resolve()).replace("\\", "/")
        tmp_engine = create_engine(f"sqlite:///{db_str}", future=True)
        try:
            base.metadata.create_all(bind=tmp_engine)
        finally:
            tmp_engine.dispose()

        instance: AstrbotDatabase = cls.connect(db_path)
        instance.base = base
        return instance

    @contextmanager
    def session_scope(self) -> Generator[Session, None, None]:
        """提供独立的 session 上下文：自动 commit/rollback 并确保 close。"""
        if self.SessionLocal is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        session: Session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def execute(self, query: str, params: Any = None) -> Any:
        """
        执行原生 SQL。SELECT 返回行列表；非查询返回 None（可根据需要改为返回 rowcount）。
        """
        if self.engine is None:
            raise RuntimeError("Database not connected.")
        stmt = text(query)
        # 使用连接和事务来执行原生 SQL
        with self.engine.connect() as conn:
            with conn.begin():
                if params is None:
                    result = conn.execute(stmt)
                else:
                    result = conn.execute(stmt, params)
                if result.returns_rows:
                    return result.fetchall()
                return None

    def close(self) -> None:
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.SessionLocal = None
        # 注意：async_engine 的释放需要在异步上下文中完成。
        # 请在异步代码中调用 `await db.aclose()` 来释放 async 引擎和会话工厂。


    async def aclose(self) -> None:
        """异步释放 AsyncEngine 和 AsyncSession 工厂。仅在 async 函数中调用。"""
        if self.async_engine is not None:
            # AsyncEngine.dispose() 在 SQLAlchemy 中是 async 方法，需要 await
            await self.async_engine.dispose()
            self.async_engine = None
        if self.AsyncSessionLocal is not None:
            self.AsyncSessionLocal = None


    @contextmanager
    def transaction(self) -> Generator[Session, None, None]:
        """兼容旧 API 的事务上下文，委托给 session_scope。"""
        with self.session_scope() as session:
            yield session

    @asynccontextmanager
    async def atransaction(self) -> AsyncGenerator[AsyncSession, None]:
        """异步事务上下文管理器。

        如果尚未创建 async engine/session factory，会基于同一路径自动创建
        一个 `sqlite+aiosqlite://` 的 AsyncEngine。返回的 session 可用于
        `async with db.atransaction() as session:` 并可执行异步 ORM/SQL 操作。
        """
        if self.AsyncSessionLocal is None:
            if self.async_engine is None:
                # 构造基于 aiosqlite 的 async url（sqlite:/// -> sqlite+aiosqlite:///）
                async_db_url = self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
                self.async_engine = create_async_engine(async_db_url, future=True)
            self.AsyncSessionLocal = async_sessionmaker(bind=self.async_engine, expire_on_commit=False, class_=AsyncSession, future=True)

        async with self.AsyncSessionLocal() as session:
            async with session.begin():
                try:
                    yield session
                except Exception:
                    await session.rollback()
                    raise

    # 支持同步上下文管理（with db: ...）
    def __enter__(self) -> "AstrbotDatabase":
        # 如果尚未连接则尝试 connect
        if self.engine is None:
            self.connect(self.db_path)
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        # 退出同步上下文时关闭同步资源
        try:
            self.close()
        except Exception:
            pass

    # 支持异步上下文管理（async with db: ...）
    async def __aenter__(self) -> "AstrbotDatabase":
        if self.async_engine is None:
            # lazy create async engine/session factory
            if self.engine is None:
                self.connect(self.db_path)
            async_db_url = self.database_url.replace("sqlite:///", "sqlite+aiosqlite:///")
            self.async_engine = create_async_engine(async_db_url, future=True)
            self.AsyncSessionLocal = async_sessionmaker(bind=self.async_engine, expire_on_commit=False, class_=AsyncSession, future=True)
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        try:
            await self.aclose()
        except Exception:
            pass

