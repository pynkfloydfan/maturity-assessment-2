import math
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.infrastructure.models import Base, DimensionORM, ThemeORM, TopicORM, AssessmentSessionORM, AssessmentEntryORM, RatingScaleORM
from app.domain.services import ScoringService

def setup_db():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    return engine, SessionLocal

def seed_minimal(s):
    d = DimensionORM(name="Gov")
    s.add(d); s.flush()
    th = ThemeORM(dimension_id=d.id, name="Oversight"); s.add(th); s.flush()
    t1 = TopicORM(theme_id=th.id, name="Topic 1"); t2 = TopicORM(theme_id=th.id, name="Topic 2")
    s.add_all([t1, t2]); s.flush()
    for level, label in [(1,"Initial"),(2,"Managed"),(3,"Defined"),(4,"Quantitatively Managed"),(5,"Optimising")]:
        s.add(RatingScaleORM(level=level, label=label))
    sess = AssessmentSessionORM(name="Test")
    s.add(sess); s.flush()
    s.add_all([AssessmentEntryORM(session_id=sess.id, topic_id=t1.id, rating_level=3, is_na=False),
               AssessmentEntryORM(session_id=sess.id, topic_id=t2.id, rating_level=5, is_na=False)])
    return sess.id

def test_scoring_theme_and_dimension():
    _, SessionLocal = setup_db()
    with SessionLocal() as s:
        sid = seed_minimal(s); s.commit()
        svc = ScoringService(s)
        themes = svc.compute_theme_averages(sid)
        assert len(themes) == 1
        assert themes[0].average == 4.0
        dims = svc.compute_dimension_averages(sid)
        assert len(dims) == 1
        assert dims[0].average == 4.0

def test_scoring_prefers_computed_score():
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy import create_engine
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)
    with SessionLocal() as s:
        # minimal seed
        d = DimensionORM(name="Gov"); s.add(d); s.flush()
        th = ThemeORM(dimension_id=d.id, name="Oversight"); s.add(th); s.flush()
        t = TopicORM(theme_id=th.id, name="Topic"); s.add(t); s.flush()
        for level, label in [(1,"Initial"),(2,"Managed"),(3,"Defined"),(4,"Quantitatively Managed"),(5,"Optimising")]:
            s.add(RatingScaleORM(level=level, label=label))
        sess = AssessmentSessionORM(name="S1"); s.add(sess); s.flush()
        # entry with rating_level but also computed_score override
        e = AssessmentEntryORM(session_id=sess.id, topic_id=t.id, rating_level=2, is_na=False)
        e.computed_score = 4.25
        s.add(e); s.flush()
        svc = ScoringService(s)
        themes = svc.compute_theme_averages(sess.id)
        assert themes[0].average == 4.25
