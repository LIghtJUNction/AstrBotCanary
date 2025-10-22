from __future__ import annotations

from contextlib import asynccontextmanager, contextmanager
from logging import getLogger
from typing import TYPE_CHECKING, Any, Self

from sqlalchemy import create_engine, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator, Mapping, Sequence
    from pathlib import Path
    from types import TracebackType

    from sqlalchemy.engine import Engine


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
        # 使用 resolve 并替换反斜杠,保证 Windows 路径在 sqlite url 中正确
        db_str = str(db_path.resolve()).replace("\\", "/")
        self.database_url = f"sqlite:///{db_str}"
        self.engine = None
        self.SessionLocal = None
        self.async_engine = None
        self.AsyncSessionLocal = None
        self.base = None

    @classmethod
    def connect(cls, db_path: Path) -> AstrbotDatabase:
        instance = cls(db_path)
        # 在这里创建 engine 和 session factory(不要在实例上保存单个 Session)
        instance.engine = create_engine(instance.database_url, future=True)
        instance.SessionLocal = sessionmaker(
            bind=instance.engine,
            future=True,
            expire_on_commit=False,
        )
        return instance

    @classmethod
    def init_base(cls, db_path: Path, base: type[DeclarativeBase]) -> AstrbotDatabase:
        """自动初始化数据库表结构.

        db_path:Path - 数据库文件路径
        base: SQLAlchemy declarative_base 对象,包含所有模型的基类.

        """
        # 确保父目录存在
        db_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用临时 engine 创建表,然后 dispose
        db_str = str(db_path.resolve()).replace("\\", "/")
        tmp_engine = create_engine(f"sqlite:///{db_str}", future=True)
        try:
            base.metadata.create_all(bind=tmp_engine)
        finally:
            tmp_engine.dispose()

        instance: AstrbotDatabase = cls.connect(db_path)
        instance.base = base
        return instance

    def bind_base(self, base: type[DeclarativeBase]) -> None:
        """动态绑定DeclarativeBase基类,并自动创建表结构.

        base: SQLAlchemy declarative_base对象,包含所有模型的基类.
        """
        # 绑定base
        self.base = base
        # 确保父目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        # 创建表结构
        if self.engine is None:
            self.engine = create_engine(self.database_url, future=True)
        base.metadata.create_all(bind=self.engine)

    @contextmanager
    def session_scope(self) -> Generator[Session]:
        """提供独立的 session 上下文:自动 commit/rollback 并确保 close.."""
        if self.SessionLocal is None:
            msg = "Database not connected. Call connect() first."
            raise RuntimeError(msg)
        session: Session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def execute(
        self,
        query: str,
        params: Mapping[str, Any] | Sequence[Any] | None = None,
    ) -> list[Any] | None:
        "执行原生 SQL.SELECT 返回行列表;非查询返回 None(可根据需要改为返回 rowcount).."
        if self.engine is None:
            msg = "Database not connected."
        raise RuntimeError(msg)
        stmt = text(query)
        # 使用连接和事务来执行原生 SQL
        with self.engine.connect() as conn, conn.begin():
            if params is None:
                result = conn.execute(stmt)
            else:
                result = conn.execute(stmt, params)
            if result.returns_rows:
                return list(result.fetchall())
        return None

    def close(self) -> None:
        if self.engine:
            self.engine.dispose()
            self.engine = None
            self.SessionLocal = None
        # 注意:async_engine 的释放需要在异步上下文中完成.
        # 请在异步代码中调用 `await db.aclose()` 来释放 async 引擎和会话工厂.

    async def aclose(self) -> None:
        """异步释放 AsyncEngine 和 AsyncSession 工厂.仅在 async 函数中调用.."""
        if self.async_engine is not None:
            # AsyncEngine.dispose() 在 SQLAlchemy 中是 async 方法,需要 await
            await self.async_engine.dispose()
            self.async_engine = None
        if self.AsyncSessionLocal is not None:
            self.AsyncSessionLocal = None

    @contextmanager
    def transaction(self) -> Generator[Session]:
        """兼容旧 API 的事务上下文,委托给 session_scope.."""
        with self.session_scope() as session:
            yield session

    @asynccontextmanager
    async def atransaction(self) -> AsyncGenerator[AsyncSession]:
        """异步事务上下文管理器..

        如果尚未创建 async engine/session factory,会基于同一路径自动创建
        一个 `sqlite+aiosqlite://` 的 AsyncEngine.返回的 session 可用于
        `async with db.atransaction() as session:` 并可执行异步 ORM/SQL 操作.
        """
        if self.AsyncSessionLocal is None:
            if self.async_engine is None:
                # 构造基于 aiosqlite 的 async url(sqlite:/// -> sqlite+aiosqlite:///)
                async_db_url = self.database_url.replace(
                    "sqlite:///",
                    "sqlite+aiosqlite:///",
                )
                self.async_engine = create_async_engine(async_db_url, future=True)
            self.AsyncSessionLocal = async_sessionmaker(
                bind=self.async_engine,
                expire_on_commit=False,
                class_=AsyncSession,
                future=True,
            )

        async with self.AsyncSessionLocal() as session, session.begin():
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    # 支持同步上下文管理(with db: ...)
    def __enter__(self) -> Self:
        if self.engine is None:
            # 直接在当前实例上初始化 engine
            self.engine = create_engine(self.database_url, future=True)
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                future=True,
                expire_on_commit=False,
            )
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        # 退出同步上下文时关闭同步资源
        try:
            self.close()
        except Exception:
            getLogger("astrbot.module.core.database").exception(
                "Exception during __exit__",
            )

    # 支持异步上下文管理(async with db: ...)
    async def __aenter__(self) -> Self:
        if self.async_engine is None:
            # lazy create async engine/session factory
            if self.engine is None:
                self.connect(self.db_path)
            async_db_url = self.database_url.replace(
                "sqlite:///",
                "sqlite+aiosqlite:///",
            )
            self.async_engine = create_async_engine(async_db_url, future=True)
            self.AsyncSessionLocal = async_sessionmaker(
                bind=self.async_engine,
                expire_on_commit=False,
                class_=AsyncSession,
                future=True,
            )
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        try:
            await self.aclose()
        except Exception:
            getLogger("astrbot.module.core.database").exception(
                "Exception during __aexit__",
            )
