import asyncpg
from config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        dsn = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")
        _pool = await asyncpg.create_pool(dsn, min_size=2, max_size=10)
    return _pool


async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


async def init_db():
    """运行迁移脚本（幂等）"""
    import os

    pool = await get_pool()
    migrations_dir = os.path.join(os.path.dirname(__file__), "..", "..", "db", "migrations")
    if not os.path.exists(migrations_dir):
        # Docker 内路径
        migrations_dir = "/db/migrations"
    for fname in sorted(os.listdir(migrations_dir)):
        if fname.endswith(".sql"):
            fpath = os.path.join(migrations_dir, fname)
            with open(fpath, "r", encoding="utf-8") as f:
                sql = f.read()
            async with pool.acquire() as conn:
                await conn.execute(sql)
