from __future__ import annotations
from typing import Iterable, Optional
from sqlalchemy.orm import Session
from .models import (
    DimensionORM, ThemeORM, TopicORM, AssessmentSessionORM, AssessmentEntryORM, RatingScaleORM, ExplanationORM
)

class DimensionRepo:
    def __init__(self, s: Session):
        self.s = s
    def get_by_name(self, name: str) -> Optional[DimensionORM]:
        return self.s.query(DimensionORM).filter_by(name=name).one_or_none()
    def add(self, dim: DimensionORM):
        self.s.add(dim)
    def list(self) -> list[DimensionORM]:
        return self.s.query(DimensionORM).order_by(DimensionORM.name).all()

class ThemeRepo:
    def __init__(self, s: Session):
        self.s = s
    def get_by_name(self, dimension_id: int, name: str) -> Optional[ThemeORM]:
        return self.s.query(ThemeRepo.model()).filter_by(dimension_id=dimension_id, name=name).one_or_none()
    @staticmethod
    def model():
        return ThemeORM
    def add(self, theme: ThemeORM):
        self.s.add(theme)
    def list_by_dimension(self, dimension_id: int) -> list[ThemeORM]:
        return self.s.query(ThemeORM).filter_by(dimension_id=dimension_id).order_by(ThemeORM.name).all()

class TopicRepo:
    def __init__(self, s: Session):
        self.s = s
    def get_by_name(self, theme_id: int, name: str) -> Optional[TopicORM]:
        return self.s.query(TopicORM).filter_by(theme_id=theme_id, name=name).one_or_none()
    def add(self, topic: TopicORM):
        self.s.add(topic)
    def list_by_theme(self, theme_id: int) -> list[TopicORM]:
        return self.s.query(TopicORM).filter_by(theme_id=theme_id).order_by(TopicORM.name).all()

class RatingScaleRepo:
    def __init__(self, s: Session):
        self.s = s
    def upsert(self, level: int, label: str):
        obj = self.s.get(RatingScaleORM, level)
        if obj is None:
            obj = RatingScaleORM(level=level, label=label)
            self.s.add(obj)
        else:
            obj.label = label
        return obj
    def all(self) -> list[RatingScaleORM]:
        return self.s.query(RatingScaleORM).order_by(RatingScaleORM.level).all()

class ExplanationRepo:
    def __init__(self, s: Session):
        self.s = s
    def add(self, exp: ExplanationORM):
        self.s.add(exp)
    def list_for_topic(self, topic_id: int) -> list[ExplanationORM]:
        return self.s.query(ExplanationORM).filter_by(topic_id=topic_id).order_by(ExplanationORM.level, ExplanationORM.id).all()

class SessionRepo:
    def __init__(self, s: Session):
        self.s = s
    def create(self, name: str, assessor: str | None, organization: str | None, notes: str | None) -> AssessmentSessionORM:
        obj = AssessmentSessionORM(name=name, assessor=assessor, organization=organization, notes=notes)
        self.s.add(obj)
        self.s.flush()
        return obj
    def get(self, session_id: int) -> AssessmentSessionORM | None:
        return self.s.get(AssessmentSessionORM, session_id)
    def list(self) -> list[AssessmentSessionORM]:
        return self.s.query(AssessmentSessionORM).order_by(AssessmentSessionORM.created_at.desc()).all()

class EntryRepo:
    def __init__(self, s: Session):
        self.s = s
    def upsert(self, session_id: int, topic_id: int, rating_level: int | None, is_na: bool, comment: str | None):
        obj = self.s.query(AssessmentEntryORM).filter_by(session_id=session_id, topic_id=topic_id).one_or_none()
        if obj is None:
            obj = AssessmentEntryORM(session_id=session_id, topic_id=topic_id)
            self.s.add(obj)
        obj.rating_level = rating_level
        obj.is_na = bool(is_na)
        obj.comment = comment
        self.s.flush()
        return obj
    def list_for_session(self, session_id: int) -> list[AssessmentEntryORM]:
        return self.s.query(AssessmentEntryORM).filter_by(session_id=session_id).all()
