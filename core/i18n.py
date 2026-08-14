"""
Bilingual (fa/en) support: string translation, Persian digit conversion,
and Jalali (Shamsi) calendar formatting for the Persian patient UI.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Literal

import jdatetime
from persiantools import digits

Language = Literal["fa", "en"]

# ---------------------------------------------------------------------------
# Translation strings
# ---------------------------------------------------------------------------
# Keep flat and namespaced by dot-path so layouts can do t("nav.dashboard", lang).

TRANSLATIONS: dict[str, dict[Language, str]] = {
    "app.title": {"en": "Pain Management Dashboard", "fa": "سامانه مدیریت درد"},
    "nav.dashboard": {"en": "Dashboard", "fa": "داشبورد"},
    "nav.patients": {"en": "Patients", "fa": "بیماران"},
    "nav.pain_tracking": {"en": "Pain Tracking", "fa": "ثبت درد"},
    "nav.medications": {"en": "Medications", "fa": "داروها"},
    "nav.appointments": {"en": "Appointments", "fa": "نوبت‌ها"},
    "nav.reports": {"en": "Reports", "fa": "گزارش‌ها"},
    "nav.logout": {"en": "Log out", "fa": "خروج"},
    "auth.username": {"en": "Username", "fa": "نام کاربری"},
    "auth.password": {"en": "Password", "fa": "رمز عبور"},
    "auth.login": {"en": "Log in", "fa": "ورود"},
    "auth.invalid_credentials": {"en": "Invalid username or password.", "fa": "نام کاربری یا رمز عبور نادرست است."},
    "pain.vas_label": {"en": "Pain level (0–10)", "fa": "شدت درد (۰ تا ۱۰)"},
    "pain.body_map_prompt": {"en": "Tap where it hurts", "fa": "محل درد را لمس کنید"},
    "pain.quality": {"en": "Pain quality", "fa": "نوع درد"},
    "pain.submit": {"en": "Submit", "fa": "ثبت"},
    "pain.history": {"en": "Pain history", "fa": "سابقه درد"},
    "med.taken_confirm": {"en": "I took this dose", "fa": "این دوز را مصرف کردم"},
    "med.side_effect_report": {"en": "Report a side effect", "fa": "گزارش عوارض جانبی"},
    "alert.high_pain": {"en": "High pain reported", "fa": "درد شدید گزارش شد"},
    "alert.missed_dose": {"en": "Missed medication dose", "fa": "دوز دارو فراموش شد"},
    "alert.upcoming_appt": {"en": "Upcoming appointment", "fa": "نوبت پیش رو"},
    "common.save": {"en": "Save", "fa": "ذخیره"},
    "common.cancel": {"en": "Cancel", "fa": "لغو"},
    "common.date": {"en": "Date", "fa": "تاریخ"},
    "common.loading": {"en": "Loading...", "fa": "در حال بارگذاری..."},
    # --- Body pain map (module 8) ---
    "body_part.neck": {"en": "Neck", "fa": "گردن"},
    "body_part.right_shoulder": {"en": "Right shoulder", "fa": "شانه راست"},
    "body_part.left_shoulder": {"en": "Left shoulder", "fa": "شانه چپ"},
    "body_part.lower_back": {"en": "Lower back", "fa": "کمر"},
    "body_part.hip": {"en": "Hip", "fa": "لگن"},
    "body_part.right_knee": {"en": "Right knee", "fa": "زانوی راست"},
    "body_part.left_knee": {"en": "Left knee", "fa": "زانوی چپ"},
    "pain.select_patient": {"en": "Select patient", "fa": "انتخاب بیمار"},
    "pain.select_locations": {"en": "Selected locations", "fa": "نواحی انتخاب‌شده"},
    "pain.select_locations_hint": {
        "en": "Click one or more points on the body map",
        "fa": "یک یا چند نقطه را روی نقشه بدن انتخاب کنید",
    },
    "pain.none_selected": {"en": "No locations selected yet", "fa": "هنوز نقطه‌ای انتخاب نشده است"},
    "pain.record_success": {"en": "Pain record saved.", "fa": "ثبت درد ذخیره شد."},
    "pain.record_error_no_location": {
        "en": "Select at least one body location.",
        "fa": "حداقل یک ناحیه از بدن را انتخاب کنید.",
    },
    "pain.record_error_no_patient": {"en": "Select a patient first.", "fa": "ابتدا یک بیمار انتخاب کنید."},
    "pain.recent_history": {"en": "Recent pain records", "fa": "سوابق اخیر درد"},
    "pain.no_history": {"en": "No pain records for this patient yet.", "fa": "هنوز سابقه‌ای برای این بیمار ثبت نشده."},
    "pain.notes_placeholder": {"en": "Optional notes...", "fa": "یادداشت (اختیاری)..."},
    # --- PDF reports (module 11) ---
    "report.patient_summary": {"en": "Patient Summary Report", "fa": "گزارش خلاصه پرونده بیمار"},
    "report.insurance_report": {"en": "Insurance Report", "fa": "گزارش بیمه"},
    "report.pain_progress": {"en": "Pain Progress Report", "fa": "گزارش روند درد"},
    "report.medication_history": {"en": "Medication History", "fa": "سابقه مصرف دارو"},
    "report.patient_info": {"en": "Patient Information", "fa": "اطلاعات بیمار"},
    "report.name": {"en": "Name", "fa": "نام"},
    "report.dob": {"en": "Date of Birth", "fa": "تاریخ تولد"},
    "report.gender": {"en": "Gender", "fa": "جنسیت"},
    "report.blood_type": {"en": "Blood Type", "fa": "گروه خونی"},
    "report.phone": {"en": "Phone", "fa": "تلفن"},
    "report.city": {"en": "City", "fa": "شهر"},
    "report.diagnoses": {"en": "Diagnoses", "fa": "تشخیص‌ها"},
    "report.icd10": {"en": "ICD-10", "fa": "کد ICD-10"},
    "report.pain_type": {"en": "Pain Type", "fa": "نوع درد"},
    "report.date": {"en": "Date", "fa": "تاریخ"},
    "report.medications": {"en": "Medications", "fa": "داروها"},
    "report.drug": {"en": "Drug", "fa": "دارو"},
    "report.dosage": {"en": "Dosage", "fa": "دوز"},
    "report.frequency": {"en": "Frequency", "fa": "دفعات مصرف"},
    "report.route": {"en": "Route", "fa": "روش مصرف"},
    "report.status": {"en": "Status", "fa": "وضعیت"},
    "report.active": {"en": "Active", "fa": "فعال"},
    "report.inactive": {"en": "Inactive", "fa": "غیرفعال"},
    "report.treatments": {"en": "Treatments", "fa": "درمان‌ها"},
    "report.treatment_type": {"en": "Type", "fa": "نوع"},
    "report.outcome": {"en": "Outcome", "fa": "نتیجه"},
    "report.cost": {"en": "Cost", "fa": "هزینه"},
    "report.avg_vas": {"en": "Average VAS Score", "fa": "میانگین شدت درد"},
    "report.max_vas": {"en": "Maximum VAS Score", "fa": "بیشینه شدت درد"},
    "report.records_count": {"en": "Total Records", "fa": "تعداد سوابق"},
    "report.taken": {"en": "Taken", "fa": "مصرف شده"},
    "report.missed": {"en": "Missed", "fa": "فراموش شده"},
    "report.generated_on": {"en": "Generated on", "fa": "تاریخ صدور"},
    "report.page": {"en": "Page", "fa": "صفحه"},
    "report.confidential": {
        "en": "CONFIDENTIAL — Protected Health Information",
        "fa": "محرمانه — اطلاعات سلامت حفاظت‌شده",
    },
    "report.no_data": {"en": "No data available.", "fa": "داده‌ای موجود نیست."},
    "common.male": {"en": "Male", "fa": "مرد"},
    "common.female": {"en": "Female", "fa": "زن"},
    "common.other": {"en": "Other", "fa": "سایر"},
}


def t(key: str, lang: Language = "en") -> str:
    """Translate a key. Falls back to English, then to the raw key if missing."""
    entry = TRANSLATIONS.get(key)
    if entry is None:
        return key
    return entry.get(lang) or entry.get("en") or key


# ---------------------------------------------------------------------------
# Persian digits
# ---------------------------------------------------------------------------


def to_persian_digits(value: str | int | float) -> str:
    """Convert Western digits (123) to Persian digits (۱۲۳)."""
    return digits.en_to_fa(str(value))


def to_english_digits(value: str) -> str:
    """Convert Persian digits (۱۲۳) back to Western digits (123) — for parsing form input."""
    return digits.fa_to_en(value)


# ---------------------------------------------------------------------------
# Jalali (Shamsi) calendar
# ---------------------------------------------------------------------------


def gregorian_to_jalali_str(d: date | datetime, persian_digits: bool = True) -> str:
    """Format a Gregorian date/datetime as a Jalali date string (YYYY/MM/DD)."""
    j = jdatetime.date.fromgregorian(date=d.date() if isinstance(d, datetime) else d)
    formatted = j.strftime("%Y/%m/%d")
    return to_persian_digits(formatted) if persian_digits else formatted


def jalali_str_to_gregorian(jalali_str: str) -> date:
    """Parse a 'YYYY/MM/DD' Jalali string (Persian or Western digits) into a Gregorian date."""
    normalized = to_english_digits(jalali_str)
    year, month, day = (int(p) for p in normalized.split("/"))
    return jdatetime.date(year, month, day).togregorian()


def format_date_for_locale(d: date | datetime, lang: Language) -> str:
    """Single entry point layouts should use: Jalali+Persian-digits for fa, ISO for en."""
    if lang == "fa":
        return gregorian_to_jalali_str(d)
    return d.strftime("%Y-%m-%d") if isinstance(d, (date, datetime)) else str(d)
