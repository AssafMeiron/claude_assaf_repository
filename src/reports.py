"""
Report generation module.
Supports CLI output, CSV export, and PDF reports.
"""

import csv
import json
from datetime import datetime
from typing import Dict, List, Optional
from pathlib import Path

from .parsers import Transaction
from .categorizer import Categorizer


def format_currency(amount: float, currency: str = 'ILS') -> str:
    """Format amount as currency string."""
    if currency == 'ILS':
        return f"₪{abs(amount):,.2f}"
    elif currency == 'USD':
        return f"${abs(amount):,.2f}"
    else:
        return f"{abs(amount):,.2f} {currency}"


def print_cli_report(summary: Dict, categorizer: Categorizer = None):
    """
    Print a formatted CLI report.
    """
    year = summary['year']
    month = summary['month']
    month_name = datetime(year, month, 1).strftime('%B %Y')

    print("\n" + "=" * 70)
    print(f"  דוח פיננסי - {month:02}/{year}")
    print(f"  Financial Report - {month_name}")
    print("=" * 70)

    # Summary
    print(f"\n  סיכום / Summary")
    print(f"  {'-' * 40}")
    print(f"  {'הכנסות / Income:':<30} {format_currency(summary['total_income']):>15}")
    print(f"  {'הוצאות / Expenses:':<30} {format_currency(summary['total_expenses']):>15}")
    print(f"  {'מאזן / Balance:':<30} {format_currency(summary['balance']):>15}")
    print(f"  {'מספר תנועות / Transactions:':<30} {summary['transaction_count']:>15}")

    # Expenses by category
    print(f"\n  הוצאות לפי קטגוריה / Expenses by Category")
    print(f"  {'-' * 60}")

    expense_cats = summary.get('expense_by_category', {})
    sorted_expenses = sorted(expense_cats.items(), key=lambda x: x[1]['total'], reverse=True)

    total_expenses = summary['total_expenses']

    for cat_key, data in sorted_expenses:
        # Get category display name
        if categorizer and cat_key in categorizer.categories:
            cat_name = categorizer.categories[cat_key].get('name', cat_key)
            cat_name_en = categorizer.categories[cat_key].get('name_en', '')
        else:
            cat_name = cat_key
            cat_name_en = ''

        amount = data['total']
        pct = (amount / total_expenses * 100) if total_expenses > 0 else 0
        tx_count = len(data['transactions'])

        # Create bar chart
        bar_len = int(pct / 2)
        bar = '█' * bar_len

        print(f"  {cat_name:<20} {format_currency(amount):>12} ({pct:5.1f}%) {bar}")

    # Income by category
    income_cats = summary.get('income_by_category', {})
    if income_cats:
        print(f"\n  הכנסות לפי קטגוריה / Income by Category")
        print(f"  {'-' * 60}")

        sorted_income = sorted(income_cats.items(), key=lambda x: x[1]['total'], reverse=True)

        for cat_key, data in sorted_income:
            if categorizer and cat_key in categorizer.categories:
                cat_name = categorizer.categories[cat_key].get('name', cat_key)
            else:
                cat_name = cat_key

            amount = data['total']
            tx_count = len(data['transactions'])

            print(f"  {cat_name:<20} {format_currency(amount):>12} ({tx_count} transactions)")

    print("\n" + "=" * 70 + "\n")


def generate_csv_report(summary: Dict, output_path: str, categorizer: Categorizer = None):
    """
    Generate a CSV report file.
    """
    with open(output_path, 'w', newline='', encoding='utf-8-sig') as f:
        writer = csv.writer(f)

        year = summary['year']
        month = summary['month']

        # Header
        writer.writerow(['Financial Report', f'{month:02}/{year}'])
        writer.writerow([])

        # Summary
        writer.writerow(['Summary'])
        writer.writerow(['Metric', 'Amount (ILS)'])
        writer.writerow(['Total Income', summary['total_income']])
        writer.writerow(['Total Expenses', summary['total_expenses']])
        writer.writerow(['Balance', summary['balance']])
        writer.writerow(['Transaction Count', summary['transaction_count']])
        writer.writerow([])

        # Expenses by category
        writer.writerow(['Expenses by Category'])
        writer.writerow(['Category (Hebrew)', 'Category (English)', 'Amount (ILS)', 'Percentage', 'Transaction Count'])

        expense_cats = summary.get('expense_by_category', {})
        sorted_expenses = sorted(expense_cats.items(), key=lambda x: x[1]['total'], reverse=True)
        total_expenses = summary['total_expenses']

        for cat_key, data in sorted_expenses:
            if categorizer and cat_key in categorizer.categories:
                cat_name = categorizer.categories[cat_key].get('name', cat_key)
                cat_name_en = categorizer.categories[cat_key].get('name_en', '')
            else:
                cat_name = cat_key
                cat_name_en = ''

            amount = data['total']
            pct = (amount / total_expenses * 100) if total_expenses > 0 else 0
            tx_count = len(data['transactions'])

            writer.writerow([cat_name, cat_name_en, amount, f'{pct:.1f}%', tx_count])

        writer.writerow([])

        # Detailed transactions
        writer.writerow(['Detailed Transactions'])
        writer.writerow(['Date', 'Description', 'Amount (ILS)', 'Category', 'Source'])

        all_transactions = []
        for cat_key, data in expense_cats.items():
            for t in data['transactions']:
                all_transactions.append(t)

        for cat_key, data in summary.get('income_by_category', {}).items():
            for t in data['transactions']:
                all_transactions.append(t)

        all_transactions.sort(key=lambda x: x.date)

        for t in all_transactions:
            if categorizer and t.category in categorizer.categories:
                cat_name = categorizer.categories[t.category].get('name', t.category)
            else:
                cat_name = t.category or 'אחר'

            writer.writerow([
                t.date.strftime('%Y-%m-%d'),
                t.description,
                t.amount,
                cat_name,
                t.source
            ])

    print(f"CSV report saved to: {output_path}")


def generate_pdf_report(summary: Dict, output_path: str, categorizer: Categorizer = None):
    """
    Generate a PDF report.
    Requires reportlab library.
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import cm
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
    except ImportError:
        print("PDF generation requires reportlab. Install with: pip install reportlab")
        print("Falling back to CSV report...")
        csv_path = output_path.replace('.pdf', '.csv')
        generate_csv_report(summary, csv_path, categorizer)
        return

    # Create document
    doc = SimpleDocTemplate(output_path, pagesize=A4,
                           rightMargin=2*cm, leftMargin=2*cm,
                           topMargin=2*cm, bottomMargin=2*cm)

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=1  # Center
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=12,
        spaceBefore=20
    )

    story = []

    year = summary['year']
    month = summary['month']
    month_name = datetime(year, month, 1).strftime('%B %Y')

    # Title
    story.append(Paragraph(f"Financial Report - {month_name}", title_style))
    story.append(Spacer(1, 20))

    # Summary table
    story.append(Paragraph("Summary", heading_style))

    summary_data = [
        ['Metric', 'Amount (ILS)'],
        ['Total Income', format_currency(summary['total_income'])],
        ['Total Expenses', format_currency(summary['total_expenses'])],
        ['Balance', format_currency(summary['balance'])],
        ['Transactions', str(summary['transaction_count'])]
    ]

    summary_table = Table(summary_data, colWidths=[8*cm, 6*cm])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    story.append(summary_table)
    story.append(Spacer(1, 20))

    # Expenses by category
    story.append(Paragraph("Expenses by Category", heading_style))

    expense_data = [['Category', 'Amount (ILS)', 'Percentage']]

    expense_cats = summary.get('expense_by_category', {})
    sorted_expenses = sorted(expense_cats.items(), key=lambda x: x[1]['total'], reverse=True)
    total_expenses = summary['total_expenses']

    for cat_key, data in sorted_expenses:
        if categorizer and cat_key in categorizer.categories:
            cat_name = categorizer.categories[cat_key].get('name_en', cat_key)
        else:
            cat_name = cat_key

        amount = data['total']
        pct = (amount / total_expenses * 100) if total_expenses > 0 else 0

        expense_data.append([cat_name, format_currency(amount), f'{pct:.1f}%'])

    expense_table = Table(expense_data, colWidths=[7*cm, 4*cm, 3*cm])
    expense_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.darkblue),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 0), (-1, 0), 11),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.lightblue),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey])
    ]))
    story.append(expense_table)

    # Build PDF
    doc.build(story)
    print(f"PDF report saved to: {output_path}")


def generate_report(summary: Dict,
                   output_dir: str,
                   categorizer: Categorizer = None,
                   formats: List[str] = None):
    """
    Generate reports in multiple formats.

    Args:
        summary: Monthly summary dict from Storage.get_monthly_summary()
        output_dir: Directory to save reports
        categorizer: Categorizer instance for category names
        formats: List of formats to generate ('cli', 'csv', 'pdf')
    """
    if formats is None:
        formats = ['cli', 'csv']

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    year = summary['year']
    month = summary['month']
    base_name = f"finance_report_{year}_{month:02}"

    if 'cli' in formats:
        print_cli_report(summary, categorizer)

    if 'csv' in formats:
        csv_path = output_dir / f"{base_name}.csv"
        generate_csv_report(summary, str(csv_path), categorizer)

    if 'pdf' in formats:
        pdf_path = output_dir / f"{base_name}.pdf"
        generate_pdf_report(summary, str(pdf_path), categorizer)


if __name__ == '__main__':
    # Test report generation
    from .storage import Storage
    from .categorizer import Categorizer

    storage = Storage()
    categorizer = Categorizer()

    months = storage.get_months()
    if months:
        latest = months[-1]
        year, month = map(int, latest.split('-'))
        summary = storage.get_monthly_summary(year, month)
        generate_report(summary, './reports', categorizer, ['cli'])
