"""
PDF Export Service — generates clean PDF summaries of doubt chats.
Uses reportlab for PDF generation.
"""

from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from .timezone import to_local, to_local_short, utc_now


def generate_chat_pdf(session) -> BytesIO:
    """
    Generate a clean, structured PDF summary of a doubt chat session.
    Returns a BytesIO buffer ready to send.
    """
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20*mm, rightMargin=20*mm,
        topMargin=20*mm, bottomMargin=20*mm,
    )

    # ─── Styles ────────────────────────────────────
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Title'],
        fontSize=18, textColor=HexColor('#2c3e50'),
        spaceAfter=4*mm,
    )
    subtitle_style = ParagraphStyle(
        'Subtitle', parent=styles['Normal'],
        fontSize=10, textColor=HexColor('#7f8c8d'),
        spaceAfter=6*mm, alignment=TA_CENTER,
    )
    heading_style = ParagraphStyle(
        'SectionHead', parent=styles['Heading2'],
        fontSize=13, textColor=HexColor('#2980b9'),
        spaceBefore=6*mm, spaceAfter=3*mm,
    )
    student_style = ParagraphStyle(
        'StudentMsg', parent=styles['Normal'],
        fontSize=10, textColor=HexColor('#2c3e50'),
        leftIndent=0, spaceAfter=2*mm,
        fontName='Helvetica-Bold',
    )
    ai_style = ParagraphStyle(
        'AIMsg', parent=styles['Normal'],
        fontSize=10, textColor=HexColor('#34495e'),
        leftIndent=8*mm, spaceAfter=4*mm,
        fontName='Helvetica',
    )
    footer_style = ParagraphStyle(
        'Footer', parent=styles['Normal'],
        fontSize=8, textColor=HexColor('#bdc3c7'),
        alignment=TA_CENTER, spaceBefore=10*mm,
    )

    # ─── Build Content ─────────────────────────────
    elements = []

    # Title
    elements.append(Paragraph("Student Doubt Summary", title_style))
    elements.append(Paragraph(
        f"Generated on {to_local(utc_now())} IST",
        subtitle_style
    ))

    # Info table
    info_data = [
        ["Student", f"{session.owner.name} ({session.owner.roll_no})"],
        ["Document", session.document.original_filename if session.document else "N/A"],
        ["Chat Started", to_local(session.created_at)],
        ["Total Messages", str(len(session.messages))],
    ]
    info_table = Table(info_data, colWidths=[35*mm, 130*mm])
    info_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('TEXTCOLOR', (0, 0), (0, -1), HexColor('#7f8c8d')),
        ('TEXTCOLOR', (1, 0), (1, -1), HexColor('#2c3e50')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    elements.append(info_table)
    elements.append(Spacer(1, 6*mm))

    # Chat messages
    elements.append(Paragraph("Conversation", heading_style))

    for msg in session.messages:
        time_str = to_local_short(msg.created_at)

        if msg.role == "user":
            text = f"[{time_str}] Student: {_escape(msg.content)}"
            elements.append(Paragraph(text, student_style))
        else:
            # Truncate very long AI responses for the summary
            content = msg.content
            if len(content) > 1500:
                content = content[:1500] + "... (truncated for summary)"
            text = f"[{time_str}] AI Tutor: {_escape(content)}"
            elements.append(Paragraph(text, ai_style))

    # Footer
    elements.append(Spacer(1, 10*mm))
    elements.append(Paragraph(
        "Smart Classroom AI — Doubt Solver Chat Export",
        footer_style
    ))

    doc.build(elements)
    buffer.seek(0)
    return buffer


def _escape(text: str) -> str:
    """Escape HTML special chars for reportlab Paragraph."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace("\n", "<br/>")
    )
