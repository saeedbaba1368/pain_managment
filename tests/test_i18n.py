"""Unit tests for core/i18n.py -- no database required."""
from __future__ import annotations


def test_translation_lookup_both_languages():
    from core.i18n import t

    assert t("nav.dashboard", "en") == "Dashboard"
    assert t("nav.dashboard", "fa") == "داشبورد"


def test_translation_falls_back_to_key_when_missing():
    from core.i18n import t

    assert t("some.nonexistent.key", "en") == "some.nonexistent.key"


def test_translation_falls_back_to_english_when_locale_missing():
    from core.i18n import TRANSLATIONS, t

    # Pick a real key and simulate a missing fa string without mutating
    # the module-level dict for other tests.
    key = "nav.dashboard"
    partial = {"en": TRANSLATIONS[key]["en"]}
    TRANSLATIONS[key], original = partial, TRANSLATIONS[key]
    try:
        assert t(key, "fa") == TRANSLATIONS[key]["en"]
    finally:
        TRANSLATIONS[key] = original


def test_persian_digit_roundtrip():
    from core.i18n import to_english_digits, to_persian_digits

    fa = to_persian_digits(1234567890)
    assert fa != "1234567890"
    assert to_english_digits(fa) == "1234567890"
