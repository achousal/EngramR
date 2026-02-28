"""PII / ID column detection and redaction for EDA safety.

Detects columns likely to contain personally identifiable information
or subject identifiers (common in biomedical datasets) and redacts them.
"""

from __future__ import annotations

import logging
import re

import pandas as pd

logger = logging.getLogger(__name__)

# Patterns that suggest a column contains identifiers
_ID_PATTERNS: list[re.Pattern] = [
    re.compile(r"\b(subject|patient|participant|person|individual)[\s_]?id\b", re.I),
    re.compile(r"\bMRN\b", re.I),
    re.compile(r"\bSSN\b", re.I),
    re.compile(r"\b(first|last|full|patient|subject|participant)[\s_]?name\b", re.I),
    re.compile(r"\bDOB\b", re.I),
    re.compile(r"\bdate[\s_]?of[\s_]?birth\b", re.I),
    re.compile(r"\bemail\b", re.I),
    re.compile(r"\bphone\b", re.I),
    re.compile(r"\baddress\b", re.I),
    re.compile(r"\bzip[\s_]?code\b", re.I),
    re.compile(r"\bsample[\s_]?id\b", re.I),
    re.compile(r"\brecord[\s_]?id\b", re.I),
    re.compile(r"^id$", re.I),
    re.compile(r"[\s_]id$", re.I),
]


def detect_id_columns(df: pd.DataFrame) -> list[str]:
    """Detect columns whose names match PII/identifier patterns.

    Args:
        df: Input DataFrame.

    Returns:
        List of column names flagged as potential identifiers.
    """
    flagged = []
    for col in df.columns:
        col_str = str(col)
        for pattern in _ID_PATTERNS:
            if pattern.search(col_str):
                flagged.append(col)
                break
    return flagged


def redact_columns(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    """Replace values in specified columns with '[REDACTED]'.

    Returns a copy; does not modify the original DataFrame.

    Args:
        df: Input DataFrame.
        columns: Column names to redact.

    Returns:
        New DataFrame with specified columns redacted.
    """
    df_out = df.copy()
    existing = [c for c in columns if c in df_out.columns]
    for col in existing:
        df_out[col] = "[REDACTED]"
    return df_out


def auto_redact(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Detect and redact ID-like columns automatically.

    Args:
        df: Input DataFrame.

    Returns:
        Tuple of (redacted DataFrame, list of redacted column names).
    """
    flagged = detect_id_columns(df)
    if flagged:
        logger.warning("Auto-redacted columns: %s", flagged)
    return redact_columns(df, flagged), flagged
