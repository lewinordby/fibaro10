import os

# Any test subset must import the composition root without relying on test order.
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://example:example@127.0.0.1:5432/example")
