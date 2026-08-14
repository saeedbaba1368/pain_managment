"""
PDF report generation (spec feature #9): patient summary, pain progress
(with a trend chart), medication history, and insurance report — each
bilingual (fa/en), matching the clinic color palette used in the Dash
charts (components/charts.py).

RTL / Persian text: ReportLab draws glyphs left-to-right with no script
awareness, so Persian strings are reshaped (joins letterforms) and
bidi-reordered before drawing — see `_shape()`. This requires a real
Persian TTF: the web UI ships assets/Vazirmatn.woff2, which ReportLab
cannot load directly. Drop `Vazirmatn-Regular.ttf` (and optionally
`-Bold.ttf`) into assets/ — e.g. from
https://github.com/rastikerdar/vazirmatn/releases — and it's picked up
automatically; without it, Persian reports fall back to Helvetica, which
has no Persian glyphs and will render boxes instead of letters.

Every function here returns raw PDF bytes — callers (a Dash callback via
dcc.Download, or the FastAPI reports endpoints) decide how to ship them.
"""
from __future__ import annotations

import io
import os
from datetime import datetime, timezone
from typing import Optional, Sequence

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
from reportlab.graphics.charts.lineplots import LinePlot
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.widgets.markers import makeMarker

from core.i18n import Language, format_date_for_locale, t, to_persian_digits
from models import Diagnosis, Medication, MedicationLog, PainRecord, Patient, Treatment

# ---------------------------------------------------------------------------
# Palette (mirrors components/charts.py CLINIC_COLORWAY)
# ---------------------------------------------------------------------------

CLINIC_PRIMARY = colors.HexColor("#2c6e9e")
CLINIC_ACCENT = colors.HexColor("#4caf90")
CLINIC_WARN = colors.HexColor("#e2a83f")
CLINIC_DANGER = colors.HexColor("#c9534b")
CLINIC_GREY = colors.HexColor("#6c757d")
CLINIC_ROW_ALT = colors.HexColor("#f4f7fa")
CLINIC_GRID = colors.HexColor("#dee2e6")

_ASSETS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
_fonts_registered = False


def _register_fonts() -> str:
    """Registers the Vazirmatn TTF if present; returns the font name to use
    for Persian text (falls back to Helvetica, which cannot render Persian
    glyphs, if no TTF has been provided — see module docstring)."""
    global _fonts_registered
    font_name = "Vazirmatn"
    if not _fonts_registered:
        ttf_path = os.path.join(_ASSETS_DIR, "Vazirmatn-Regular.ttf")
        if os.path.exists(ttf_path):
            pdfmetrics.registerFont(TTFont(font_name, ttf_path))
            bold_path = os.path.join(_ASSETS_DIR, "Vazirmatn-Bold.ttf")
            pdfmetrics.registerFont(TTFont(f"{font_name}-Bold", bold_path if os.path.exists(bold_path) else ttf_path))
        _fonts_registered = True
    return font_name if font_name in pdfmetrics.getRegisteredFontNames() else "Helvetica"


def _shape(text: object, lang: Language) -> str:
    """Reshape + bidi-reorder Persian text for correct on-page display.
    English text (and non-string values) pass through as plain str()."""
    text = "" if text is None else str(text)
    if lang != "fa" or not text:
        return text
    try:
        import arabic_reshaper
        from bidi.algorithm import get_display

        return get_display(arabic_reshaper.reshape(text))
    except ImportError:
        return text  # degrade gracefully rather than fail report generation


def _styles(lang: Language) -> dict:
    sheet = getSampleStyleSheet()
    font = _register_fonts() if lang == "fa" else "Helvetica"
    bold_font = f"{font}-Bold" if f"{font}-Bold" in pdfmetrics.getRegisteredFontNames() else "Helvetica-Bold"
    align = "RIGHT" if lang == "fa" else "LEFT"

    return {
        "font": font,
        "bold_font": bold_font,
        "align": align,
        "title": ParagraphStyle(
            "ReportTitle", parent=sheet["Title"], fontName=bold_font, alignment=TA_CENTER,
            textColor=CLINIC_PRIMARY, fontSize=18, spaceAfter=2,
        ),
        "subtitle": ParagraphStyle(
            "ReportSubtitle", parent=sheet["Normal"], fontName=font, alignment=TA_CENTER,
            textColor=CLINIC_GREY, fontSize=9, spaceAfter=16,
        ),
        "heading": ParagraphStyle(
            "SectionHeading", parent=sheet["Heading2"], fontName=bold_font,
            alignment=(4 if lang == "fa" else 0), textColor=CLINIC_PRIMARY, fontSize=13,
            spaceBefore=14, spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "Body", parent=sheet["Normal"], fontName=font,
            alignment=(4 if lang == "fa" else 0), fontSize=10, leading=14,
        ),
    }


def _gender_label(patient: Patient, lang: Language) -> str:
    return t(f"common.{patient.gender.value}", lang)


def _localized_number(value: object, lang: Language) -> str:
    return to_persian_digits(value) if lang == "fa" else str(value)


def _patient_info_table(patient: Patient, lang: Language, styles: dict) -> Table:
    pairs = [
        (t("report.name", lang), patient.full_name),
        (t("report.dob", lang), format_date_for_locale(patient.birth_date, lang)),
        (t("report.gender", lang), _gender_label(patient, lang)),
        (t("report.blood_type", lang), patient.blood_type.value),
        (t("report.phone", lang), _localized_number(patient.phone, lang) if lang == "fa" else patient.phone),
        (t("report.city", lang), patient.city or "-"),
    ]
    rows = [[_shape(b, lang), _shape(a, lang)] if lang == "fa" else [_shape(a, lang), _shape(b, lang)] for a, b in pairs]

    table = Table(rows, colWidths=[4.5 * cm, 9 * cm])
    table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), styles["font"]),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (0 if lang != "fa" else 1, 0), (0 if lang != "fa" else 1, -1), styles["bold_font"]),
        ("TEXTCOLOR", (0 if lang != "fa" else 1, 0), (0 if lang != "fa" else 1, -1), CLINIC_PRIMARY),
        ("ALIGN", (0, 0), (-1, -1), styles["align"]),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LINEBELOW", (0, 0), (-1, -1), 0.4, CLINIC_GRID),
    ]))
    return table


def _data_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[object]],
    lang: Language,
    styles: dict,
    col_widths: Optional[Sequence[float]] = None,
) -> Table:
    ordered_headers = list(reversed(headers)) if lang == "fa" else list(headers)
    ordered_rows = [list(reversed(r)) for r in rows] if lang == "fa" else [list(r) for r in rows]
    ordered_widths = list(reversed(col_widths)) if (col_widths and lang == "fa") else col_widths

    data = [[_shape(h, lang) for h in ordered_headers]] + [[_shape(c, lang) for c in r] for r in ordered_rows]
    table = Table(data, colWidths=ordered_widths, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), CLINIC_PRIMARY),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), styles["bold_font"]),
        ("FONTNAME", (0, 1), (-1, -1), styles["font"]),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (0, 0), (-1, -1), styles["align"]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, CLINIC_ROW_ALT]),
        ("GRID", (0, 0), (-1, -1), 0.25, CLINIC_GRID),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
    ]))
    return table


def _pain_trend_drawing(pain_records: Sequence[PainRecord], lang: Language) -> Drawing:
    """Simple VAS-over-time line chart. Dates aren't plotted on the x-axis
    tick labels (they vary too much in width for ReportLab's fixed-slot
    axis labelling) — the caller lists the covered date range in a caption
    beneath the chart instead."""
    ordered = sorted(pain_records, key=lambda r: r.timestamp)
    drawing = Drawing(460, 190)

    if len(ordered) < 2:
        drawing.add(String(140, 95, _shape(t("report.no_data", lang), lang), fontSize=10, fillColor=CLINIC_GREY))
        return drawing

    plot = LinePlot()
    plot.x, plot.y = 45, 25
    plot.width, plot.height = 400, 145
    plot.data = [[(i, r.vas_score) for i, r in enumerate(ordered)]]
    plot.lines[0].strokeColor = CLINIC_PRIMARY
    plot.lines[0].strokeWidth = 2
    plot.lines[0].symbol = makeMarker("Circle")
    plot.joinedLines = 1

    plot.yValueAxis.valueMin = 0
    plot.yValueAxis.valueMax = 10
    plot.yValueAxis.valueStep = 2
    plot.yValueAxis.labels.fontSize = 8
    plot.yValueAxis.labels.fillColor = CLINIC_GREY

    plot.xValueAxis.valueMin = 0
    plot.xValueAxis.valueMax = len(ordered) - 1
    plot.xValueAxis.labels.fontSize = 0  # see docstring — dates go in the caption instead

    drawing.add(plot)
    drawing.add(String(0, 170, _shape(t("pain.vas_label", lang), lang), fontSize=8, fillColor=CLINIC_GREY))
    return drawing


def _footer(canvas, doc, lang: Language) -> None:
    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(CLINIC_GREY)
    canvas.drawCentredString(A4[0] / 2, 1.2 * cm, f"{t('report.page', lang)} {doc.page}")
    canvas.setFont("Helvetica-Oblique", 7)
    canvas.setFillColor(CLINIC_DANGER)
    canvas.drawCentredString(A4[0] / 2, 0.75 * cm, t("report.confidential", lang))
    canvas.restoreState()


def _build_pdf(story: list, lang: Language) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=2 * cm, rightMargin=2 * cm, topMargin=1.8 * cm, bottomMargin=2 * cm,
        title=t("app.title", lang),
    )
    footer = lambda canvas, doc_: _footer(canvas, doc_, lang)
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return buffer.getvalue()


def _title_block(title_key: str, lang: Language, styles: dict) -> list:
    return [
        Paragraph(_shape(t(title_key, lang), lang), styles["title"]),
        Paragraph(
            f"{_shape(t('report.generated_on', lang), lang)}: {format_date_for_locale(datetime.now(timezone.utc), lang)}",
            styles["subtitle"],
        ),
    ]


# ---------------------------------------------------------------------------
# Public report builders
# ---------------------------------------------------------------------------


def generate_patient_summary_pdf(
    patient: Patient,
    diagnoses: Sequence[Diagnosis],
    medications: Sequence[Medication],
    treatments: Sequence[Treatment],
    lang: Language = "en",
) -> bytes:
    """Full bilingual patient chart summary: demographics, diagnoses,
    current/past medications, and treatment history."""
    styles = _styles(lang)
    story: list = _title_block("report.patient_summary", lang, styles)
    story += [Paragraph(_shape(t("report.patient_info", lang), lang), styles["heading"]), _patient_info_table(patient, lang, styles)]

    story.append(Paragraph(_shape(t("report.diagnoses", lang), lang), styles["heading"]))
    if diagnoses:
        rows = [
            [format_date_for_locale(d.diagnosis_date, lang), d.icd10_code, d.description, d.pain_type.value.replace("_", " ").title()]
            for d in sorted(diagnoses, key=lambda d: d.diagnosis_date, reverse=True)
        ]
        story.append(_data_table(
            [t("report.date", lang), t("report.icd10", lang), "Description", t("report.pain_type", lang)],
            rows, lang, styles, col_widths=[2.3 * cm, 2 * cm, 6.7 * cm, 2.5 * cm],
        ))
    else:
        story.append(Paragraph(_shape(t("report.no_data", lang), lang), styles["body"]))

    story.append(Paragraph(_shape(t("report.medications", lang), lang), styles["heading"]))
    if medications:
        rows = [
            [m.drug_name, m.dosage, m.frequency, m.route, t("report.active", lang) if m.is_active else t("report.inactive", lang)]
            for m in sorted(medications, key=lambda m: m.start_date, reverse=True)
        ]
        story.append(_data_table(
            [t("report.drug", lang), t("report.dosage", lang), t("report.frequency", lang), t("report.route", lang), t("report.status", lang)],
            rows, lang, styles, col_widths=[3.3 * cm, 2.3 * cm, 3.3 * cm, 2.6 * cm, 2 * cm],
        ))
    else:
        story.append(Paragraph(_shape(t("report.no_data", lang), lang), styles["body"]))

    story.append(Paragraph(_shape(t("report.treatments", lang), lang), styles["heading"]))
    if treatments:
        rows = [
            [format_date_for_locale(tr.date, lang), tr.treatment_type.value.replace("_", " ").title(), tr.outcome or "-", f"${tr.cost:,.2f}" if tr.cost else "-"]
            for tr in sorted(treatments, key=lambda tr: tr.date, reverse=True)
        ]
        story.append(_data_table(
            [t("report.date", lang), t("report.treatment_type", lang), t("report.outcome", lang), t("report.cost", lang)],
            rows, lang, styles, col_widths=[2.5 * cm, 3.5 * cm, 4.5 * cm, 2.8 * cm],
        ))
    else:
        story.append(Paragraph(_shape(t("report.no_data", lang), lang), styles["body"]))

    return _build_pdf(story, lang)


def generate_pain_progress_report(patient: Patient, pain_records: Sequence[PainRecord], lang: Language = "en") -> bytes:
    """VAS trend chart + full pain record history for one patient."""
    styles = _styles(lang)
    story: list = _title_block("report.pain_progress", lang, styles)
    story += [Paragraph(_shape(t("report.patient_info", lang), lang), styles["heading"]), _patient_info_table(patient, lang, styles)]

    story.append(Paragraph(_shape(t("pain.history", lang), lang), styles["heading"]))
    if pain_records:
        scores = [r.vas_score for r in pain_records]
        ordered = sorted(pain_records, key=lambda r: r.timestamp)
        stats_pairs = [
            (t("report.records_count", lang), _localized_number(len(pain_records), lang)),
            (t("report.avg_vas", lang), _localized_number(f"{sum(scores) / len(scores):.1f}", lang)),
            (t("report.max_vas", lang), _localized_number(max(scores), lang)),
        ]
        stats_rows = [[_shape(b, lang), _shape(a, lang)] if lang == "fa" else [_shape(a, lang), _shape(b, lang)] for a, b in stats_pairs]
        stats_table = Table(stats_rows, colWidths=[6 * cm, 4 * cm])
        stats_table.setStyle(TableStyle([
            ("FONTNAME", (0, 0), (-1, -1), styles["font"]),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("ALIGN", (0, 0), (-1, -1), styles["align"]),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ]))
        story += [stats_table, Spacer(1, 0.4 * cm), _pain_trend_drawing(pain_records, lang)]
        story.append(Paragraph(
            _shape(f"{format_date_for_locale(ordered[0].timestamp, lang)} \u2192 {format_date_for_locale(ordered[-1].timestamp, lang)}", lang),
            ParagraphStyle("caption", parent=styles["body"], alignment=TA_CENTER, fontSize=8, textColor=CLINIC_GREY),
        ))
        story.append(Spacer(1, 0.4 * cm))

        history_rows = [
            [format_date_for_locale(r.timestamp, lang), _localized_number(r.vas_score, lang), r.pain_quality or "-"]
            for r in sorted(pain_records, key=lambda r: r.timestamp, reverse=True)
        ]
        story.append(_data_table(
            [t("report.date", lang), t("pain.vas_label", lang), t("pain.quality", lang)],
            history_rows, lang, styles, col_widths=[3.5 * cm, 4 * cm, 5.5 * cm],
        ))
    else:
        story.append(Paragraph(_shape(t("report.no_data", lang), lang), styles["body"]))

    return _build_pdf(story, lang)


def generate_medication_history_pdf(
    patient: Patient,
    medications: Sequence[Medication],
    logs_by_medication: Optional[dict[int, Sequence[MedicationLog]]] = None,
    lang: Language = "en",
) -> bytes:
    """Medication list plus, where available, an adherence summary
    (taken vs. missed doses) per drug — logs_by_medication maps
    medication_id -> its MedicationLog rows."""
    styles = _styles(lang)
    logs_by_medication = logs_by_medication or {}
    story: list = _title_block("report.medication_history", lang, styles)
    story += [Paragraph(_shape(t("report.patient_info", lang), lang), styles["heading"]), _patient_info_table(patient, lang, styles)]

    story.append(Paragraph(_shape(t("report.medications", lang), lang), styles["heading"]))
    if medications:
        rows = []
        for m in sorted(medications, key=lambda m: m.start_date, reverse=True):
            logs = logs_by_medication.get(m.id, [])
            taken = sum(1 for l in logs if l.taken)
            missed = sum(1 for l in logs if l.missed)
            adherence = f"{taken} {t('report.taken', lang)} / {missed} {t('report.missed', lang)}" if logs else "-"
            rows.append([
                m.drug_name, m.dosage, m.frequency,
                format_date_for_locale(m.start_date, lang),
                format_date_for_locale(m.end_date, lang) if m.end_date else t("report.active", lang),
                adherence,
            ])
        story.append(_data_table(
            [t("report.drug", lang), t("report.dosage", lang), t("report.frequency", lang), t("common.date", lang), t("report.status", lang), "Adherence"],
            rows, lang, styles, col_widths=[3 * cm, 2 * cm, 2.7 * cm, 2.3 * cm, 2.3 * cm, 3.7 * cm],
        ))
    else:
        story.append(Paragraph(_shape(t("report.no_data", lang), lang), styles["body"]))

    return _build_pdf(story, lang)


def generate_insurance_report_pdf(
    patient: Patient,
    diagnoses: Sequence[Diagnosis],
    treatments: Sequence[Treatment],
    lang: Language = "en",
) -> bytes:
    """Insurance-facing report: diagnoses (with ICD-10 codes insurers need)
    plus billable treatments and their total cost."""
    styles = _styles(lang)
    story: list = _title_block("report.insurance_report", lang, styles)
    story += [Paragraph(_shape(t("report.patient_info", lang), lang), styles["heading"]), _patient_info_table(patient, lang, styles)]

    story.append(Paragraph(_shape(t("report.diagnoses", lang), lang), styles["heading"]))
    if diagnoses:
        rows = [
            [format_date_for_locale(d.diagnosis_date, lang), d.icd10_code, d.description]
            for d in sorted(diagnoses, key=lambda d: d.diagnosis_date, reverse=True)
        ]
        story.append(_data_table(
            [t("report.date", lang), t("report.icd10", lang), "Description"],
            rows, lang, styles, col_widths=[2.5 * cm, 2.5 * cm, 8.5 * cm],
        ))
    else:
        story.append(Paragraph(_shape(t("report.no_data", lang), lang), styles["body"]))

    story.append(Paragraph(_shape(t("report.treatments", lang), lang), styles["heading"]))
    total_cost = sum((tr.cost or 0) for tr in treatments)
    if treatments:
        rows = [
            [format_date_for_locale(tr.date, lang), tr.treatment_type.value.replace("_", " ").title(), f"${tr.cost:,.2f}" if tr.cost else "-"]
            for tr in sorted(treatments, key=lambda tr: tr.date, reverse=True)
        ]
        story.append(_data_table(
            [t("report.date", lang), t("report.treatment_type", lang), t("report.cost", lang)],
            rows, lang, styles, col_widths=[3 * cm, 5 * cm, 5.5 * cm],
        ))
        story.append(Spacer(1, 0.3 * cm))
        total_style = ParagraphStyle("total", parent=styles["body"], fontName=styles["bold_font"], textColor=CLINIC_PRIMARY, alignment=2)
        story.append(Paragraph(_shape(f"{t('report.cost', lang)}: ${total_cost:,.2f}", lang), total_style))
    else:
        story.append(Paragraph(_shape(t("report.no_data", lang), lang), styles["body"]))

    return _build_pdf(story, lang)
