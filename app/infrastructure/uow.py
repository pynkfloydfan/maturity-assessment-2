from __future__ import annotations
from contextlib import contextmanager
from typing import Iterator
from sqlalchemy.orm import Session, sessionmaker

class UnitOfWork:
    def __init__(self, SessionLocal: sessionmaker):
        self.SessionLocal = SessionLocal
    @contextmanager
    def begin(self) -> Iterator[Session]:
        s = self.SessionLocal()
        try:
            yield s
            s.commit()
        except Exception:
            s.rollback()
            raise
        finally:
            s.close()
