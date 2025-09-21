from __future__ import annotations

from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.api import list_dimensions_with_topics
from app.infrastructure.models import (
    AssessmentEntryORM,
    AssessmentSessionORM,
    Base,
    DimensionORM,
    RatingScaleORM,
    ThemeORM,
    ThemeLevelGuidanceORM,
    TopicORM,
)
from app.web.dependencies import get_db_session
from app.web.main import create_application
from scripts.seed_dataset import seed_from_excel


def build_app_with_db() -> tuple[TestClient, sessionmaker[Session]]:
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine, future=True)

    app = create_application()

    def override_get_db_session():
        session = SessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db_session] = override_get_db_session
    client = TestClient(app)
    return client, SessionLocal


def seed_minimal_dataset(session: Session) -> int:
    dimension = DimensionORM(name="Governance & Leadership")
    session.add(dimension)
    session.flush()

    theme = ThemeORM(name="Oversight", dimension_id=dimension.id)
    session.add(theme)
    session.flush()

    topics = [
        TopicORM(theme_id=theme.id, name="Topic A"),
        TopicORM(theme_id=theme.id, name="Topic B"),
    ]
    session.add_all(topics)
    session.flush()

    for level in range(1, 6):
        session.add(RatingScaleORM(level=level, label=f"Level {level}"))

    seed_session = AssessmentSessionORM(name="Baseline")
    session.add(seed_session)
    session.flush()

    session.add_all(
        [
            AssessmentEntryORM(session_id=seed_session.id, topic_id=topics[0].id, rating_level=3, is_na=False),
            AssessmentEntryORM(session_id=seed_session.id, topic_id=topics[1].id, rating_level=5, is_na=False),
        ]
    )

    guidance = [
        ThemeLevelGuidanceORM(theme_id=theme.id, level=level, description=f"Guidance {level}")
        for level in range(1, 6)
    ]
    session.add_all(guidance)

    return seed_session.id


def test_dashboard_endpoints_return_data():
    client, SessionLocal = build_app_with_db()
    with SessionLocal() as session:
        session_id = seed_minimal_dataset(session)
        session.commit()

    response = client.get(f"/api/sessions/{session_id}/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["dimensions"]
    assert payload["topic_scores"]

    figures_resp = client.get(f"/api/sessions/{session_id}/dashboard/figures")
    assert figures_resp.status_code == 200
    figures = figures_resp.json()
    assert isinstance(figures["tiles"], list)
    assert figures["tiles"][0]["name"] == "Governance & Leadership"
    assert figures["radar"] is not None
    assert figures["radar"]["data"]


def test_seed_from_excel_populates_descriptions(tmp_path):
    client, SessionLocal = build_app_with_db()
    excel_path = Path("app/source_data/enhanced_operational_resilience_maturity_v6.xlsx")
    assert excel_path.exists(), "Seed spreadsheet missing"

    with SessionLocal() as session:
        seed_from_excel(session, excel_path)
        session.commit()

    with SessionLocal() as session:
        dimension = (
            session.query(DimensionORM)
            .filter(DimensionORM.name == "Governance & Leadership")
            .one()
        )
        assert dimension.description
        expected_df = pd.read_excel(excel_path, sheet_name="Dimension Theme Topic Descrip")
        expected_desc = (
            expected_df.loc[
                expected_df["Dimension"].str.strip() == "Governance & Leadership",
                "Dimension_Description",
            ]
            .dropna()
            .iloc[0]
            .strip()
        )
        assert dimension.description.strip() == expected_desc.strip()

        theme_guidance_count = (
            session.query(ThemeLevelGuidanceORM)
            .count()
        )
        assert theme_guidance_count > 0

        topics_df = list_dimensions_with_topics(session)
        assert not topics_df.empty

    # Ensure API can still respond using seeded data
    with SessionLocal() as session:
        session_id = seed_minimal_dataset(session)
        session.commit()

    resp = client.get(f"/api/sessions/{session_id}/dashboard/figures")
    assert resp.status_code == 200
