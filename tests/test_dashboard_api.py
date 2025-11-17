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
            AssessmentEntryORM(
                session_id=seed_session.id,
                topic_id=topics[0].id,
                current_maturity=3,
                desired_maturity=3,
                current_is_na=False,
                desired_is_na=False,
            ),
            AssessmentEntryORM(
                session_id=seed_session.id,
                topic_id=topics[1].id,
                current_maturity=5,
                desired_maturity=5,
                current_is_na=False,
                desired_is_na=False,
            ),
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


def test_dimension_assessment_endpoint():
    client, SessionLocal = build_app_with_db()
    with SessionLocal() as session:
        session_id = seed_minimal_dataset(session)
        session.commit()

    with SessionLocal() as session:
        dimension_id = session.query(DimensionORM.id).scalar()
        assert dimension_id is not None

    response = client.get(
        f"/api/dimensions/{dimension_id}/assessment",
        params={"session_id": session_id},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["dimension"]["id"] == dimension_id
    assert payload["themes"]
    assert payload["progress"]["total_topics"] == 2
    first_theme = payload["themes"][0]
    first_topic = first_theme["topics"][0]
    assert "current_maturity" in first_topic
    assert "desired_maturity" in first_topic


def test_seed_from_excel_populates_descriptions(tmp_path):
    client, SessionLocal = build_app_with_db()
    excel_path = Path("app/source_data/Maturity_Assessment_Data.xlsx")
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
        topic_with_metadata = (
            session.query(TopicORM)
            .filter(TopicORM.impact.isnot(None))
            .filter(TopicORM.benefits.isnot(None))
            .first()
        )
        assert topic_with_metadata is not None
        assert topic_with_metadata.regulations is not None

    # Ensure API can still respond using seeded data
    with SessionLocal() as session:
        session_id = seed_minimal_dataset(session)
        session.commit()

    resp = client.get(f"/api/sessions/{session_id}/dashboard/figures")
    assert resp.status_code == 200


def test_export_session_xlsx_single_sheet(tmp_path):
    client, SessionLocal = build_app_with_db()
    with SessionLocal() as session:
        session_id = seed_minimal_dataset(session)
        session.commit()

    response = client.get(f"/api/sessions/{session_id}/exports/xlsx")
    assert response.status_code == 200

    export_path = tmp_path / "assessment.xlsx"
    export_path.write_bytes(response.content)

    xls = pd.ExcelFile(export_path)
    assert xls.sheet_names == ["Assessment"]

    df = xls.parse("Assessment")
    for column in [
        "Dimension",
        "Theme",
        "TopicID",
        "Topic",
        "Impact",
        "Benefits",
        "Basic",
        "Advanced",
        "Evidence",
        "Regulations",
        "Rating",
        "N/A",
        "Comment",
    ]:
        assert column in df.columns

    # Ensure topics are present and aligned with entries
    assert df["TopicID"].notna().sum() >= 2


def test_import_session_xlsx_updates_entries(tmp_path):
    client, SessionLocal = build_app_with_db()
    with SessionLocal() as session:
        session_id = seed_minimal_dataset(session)
        session.commit()
        topics = session.query(TopicORM).order_by(TopicORM.id).all()

    upload_df = pd.DataFrame(
        [
            {
                "TopicID": topics[0].id,
                "Rating": 2,
                "ComputedScore": None,
                "N/A": False,
                "Comment": "Adjusted score",
            },
            {
                "TopicID": topics[1].id,
                "Rating": 4,
                "ComputedScore": None,
                "N/A": False,
                "Comment": "Progress noted",
            },
        ]
    )

    upload_path = tmp_path / "upload.xlsx"
    with pd.ExcelWriter(upload_path, engine="xlsxwriter") as writer:
        upload_df.to_excel(writer, index=False, sheet_name="Assessment")

    with upload_path.open("rb") as fh:
        response = client.post(
            f"/api/sessions/{session_id}/imports/xlsx",
            files={
                "file": (
                    "upload.xlsx",
                    fh.read(),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                )
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["processed"] == 2

    with SessionLocal() as session:
        entries = (
            session.query(AssessmentEntryORM)
            .filter(AssessmentEntryORM.session_id == session_id)
            .order_by(AssessmentEntryORM.topic_id)
            .all()
        )
        assert [entry.current_maturity for entry in entries] == [2, 4]
        assert [entry.comment for entry in entries] == ["Adjusted score", "Progress noted"]
