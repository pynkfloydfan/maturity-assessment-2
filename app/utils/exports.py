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
    bio = io.BytesIO()
    with pd.ExcelWriter(bio, engine="xlsxwriter") as writer:
        topics_df.to_excel(writer, index=False, sheet_name="Topics")
        entries_df.to_excel(writer, index=False, sheet_name="Entries")
    return bio.getvalue()
