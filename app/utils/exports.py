from __future__ import annotations

import io
import json

import pandas as pd


def _to_iso(val):
    if hasattr(val, "isoformat"):
        try:
            return val.isoformat()
        except Exception:
            return str(val)
    return val


def make_json_export_payload(
    session_id: int, topics_df: pd.DataFrame, entries_df: pd.DataFrame
) -> str:
    payload = {
        "session_id": session_id,
        "topics": topics_df.to_dict(orient="records"),
        "entries": entries_df.map(_to_iso).to_dict(orient="records"),
    }
    return json.dumps(payload, indent=2)


def make_xlsx_export_bytes(topics_df: pd.DataFrame, entries_df: pd.DataFrame) -> bytes:
    """Create a single-sheet Excel export combining topic metadata and session entries."""

    if topics_df is None:
        topics_df = pd.DataFrame(columns=["Dimension", "Theme", "TopicID", "Topic"])
    if entries_df is None:
        entries_df = pd.DataFrame(columns=["TopicID", "Rating", "ComputedScore", "N/A", "Comment", "CreatedAt"])

    # Ensure both frames share consistent structure before merging
    topics_df = topics_df.copy()
    entries_df = entries_df.copy()

    combined = topics_df.merge(entries_df, how="left", on="TopicID") if not topics_df.empty else entries_df

    # Guarantee column ordering and presence for consumers opening the sheet in Excel
    ordered_columns = [
        "Dimension",
        "Theme",
        "TopicID",
        "Topic",
        "Rating",
        "ComputedScore",
        "N/A",
        "Comment",
        "CreatedAt",
    ]

    for column in ordered_columns:
        if column not in combined.columns:
            combined[column] = pd.NA

    combined = combined[ordered_columns]

    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        combined.to_excel(writer, index=False, sheet_name="Assessment")
    return bio.getvalue()
