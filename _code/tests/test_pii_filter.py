"""Tests for PII/ID column detection and redaction."""

import pandas as pd

from engram_r.pii_filter import auto_redact, detect_id_columns, redact_columns


class TestDetectIdColumns:
    def test_catches_subject_id(self):
        df = pd.DataFrame({"SubjectID": [1], "Age": [70]})
        assert "SubjectID" in detect_id_columns(df)

    def test_catches_patient_id(self):
        df = pd.DataFrame({"PatientId": [1], "Score": [5]})
        assert "PatientId" in detect_id_columns(df)

    def test_catches_mrn(self):
        df = pd.DataFrame({"MRN": ["A1"], "Value": [1.0]})
        assert "MRN" in detect_id_columns(df)

    def test_catches_ssn(self):
        df = pd.DataFrame({"SSN": ["123"], "Data": [1]})
        assert "SSN" in detect_id_columns(df)

    def test_catches_name_columns(self):
        df = pd.DataFrame({"FirstName": ["A"], "LastName": ["B"], "Age": [1]})
        flagged = detect_id_columns(df)
        assert "FirstName" in flagged
        assert "LastName" in flagged

    def test_catches_email(self):
        df = pd.DataFrame({"Email": ["a@b.com"], "Score": [1]})
        assert "Email" in detect_id_columns(df)

    def test_catches_bare_id(self):
        df = pd.DataFrame({"ID": [1], "Value": [2]})
        assert "ID" in detect_id_columns(df)

    def test_catches_sample_id(self):
        df = pd.DataFrame({"Sample_ID": [1], "Value": [2]})
        assert "Sample_ID" in detect_id_columns(df)

    def test_ignores_safe_columns(self):
        df = pd.DataFrame({"Age": [70], "GFAP": [0.45], "Diagnosis": ["P+"]})
        assert detect_id_columns(df) == []


class TestRedactColumns:
    def test_replaces_with_redacted(self):
        df = pd.DataFrame({"SubjectID": ["S001", "S002"], "Age": [70, 68]})
        result = redact_columns(df, ["SubjectID"])
        assert all(result["SubjectID"] == "[REDACTED]")
        assert list(result["Age"]) == [70, 68]

    def test_does_not_modify_original(self):
        df = pd.DataFrame({"SubjectID": ["S001"], "Age": [70]})
        redact_columns(df, ["SubjectID"])
        assert df["SubjectID"].iloc[0] == "S001"

    def test_handles_missing_column(self):
        df = pd.DataFrame({"Age": [70]})
        result = redact_columns(df, ["Nonexistent"])
        assert list(result.columns) == ["Age"]


class TestAutoRedact:
    def test_detects_and_redacts(self):
        df = pd.DataFrame({
            "SubjectID": ["S001"],
            "PatientName": ["John"],
            "Age": [70],
            "GFAP": [0.45],
        })
        result, flagged = auto_redact(df)
        assert "SubjectID" in flagged
        assert "PatientName" in flagged
        assert result["SubjectID"].iloc[0] == "[REDACTED]"
        assert result["Age"].iloc[0] == 70

    def test_no_pii_returns_unchanged(self):
        df = pd.DataFrame({"Age": [70], "Score": [5.0]})
        result, flagged = auto_redact(df)
        assert flagged == []
        assert result.equals(df)
