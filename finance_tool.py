#!/usr/bin/env python3
"""
Finance Monitoring Tool - Main CLI

Usage:
    python finance_tool.py import <file>...     Import bank/credit card statements
    python finance_tool.py report [--month=YYYY-MM] [--format=csv,pdf,cli]
    python finance_tool.py categories           List all categories
    python finance_tool.py override <desc> <category>  Add category override
    python finance_tool.py overrides            List all overrides
    python finance_tool.py uncategorized        Show uncategorized transactions
    python finance_tool.py interactive          Interactive categorization mode
"""

import argparse
import sys
import os
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.parsers import parse_file
from src.categorizer import Categorizer, interactive_categorize
from src.storage import Storage
from src.reports import generate_report, print_cli_report


def get_default_dirs():
    """Get default directories relative to script location."""
    base_dir = Path(__file__).parent
    return {
        'config': base_dir / 'config',
        'data': base_dir / 'data',
        'reports': base_dir / 'reports',
    }


def cmd_import(args):
    """Import statement files."""
    dirs = get_default_dirs()
    storage = Storage(str(dirs['data']))
    categorizer = Categorizer(str(dirs['config']))

    total_added = 0
    total_files = 0

    for file_path in args.files:
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            continue

        # Check if already processed
        if storage.is_file_processed(file_path) and not args.force:
            print(f"Already processed (use --force to reimport): {file_path}")
            continue

        try:
            print(f"Parsing: {file_path}")
            transactions = parse_file(file_path)

            # Categorize transactions
            categorizer.categorize_transactions(transactions)

            # Store transactions
            added = storage.add_transactions(transactions, file_path)
            total_added += added
            total_files += 1

            print(f"  -> Imported {added} new transactions (of {len(transactions)} parsed)")

            # Show category breakdown
            cat_counts = {}
            for t in transactions:
                cat = t.category or 'אחר'
                cat_counts[cat] = cat_counts.get(cat, 0) + 1

            print("  -> Categories:")
            for cat, count in sorted(cat_counts.items(), key=lambda x: -x[1]):
                if cat in categorizer.categories:
                    cat_name = categorizer.categories[cat].get('name', cat)
                else:
                    cat_name = cat
                print(f"      {cat_name}: {count}")

        except Exception as e:
            print(f"Error processing {file_path}: {e}")
            if args.verbose:
                import traceback
                traceback.print_exc()

    print(f"\nTotal: Imported {total_added} transactions from {total_files} files")


def cmd_report(args):
    """Generate report."""
    dirs = get_default_dirs()
    storage = Storage(str(dirs['data']))
    categorizer = Categorizer(str(dirs['config']))

    # Determine which month to report
    if args.month:
        try:
            year, month = map(int, args.month.split('-'))
        except ValueError:
            print("Invalid month format. Use YYYY-MM (e.g., 2026-01)")
            return
    else:
        # Use most recent month with data
        months = storage.get_months()
        if not months:
            print("No data available. Import some statements first.")
            return
        latest = months[-1]
        year, month = map(int, latest.split('-'))
        print(f"Generating report for most recent month: {latest}")

    # Get summary
    summary = storage.get_monthly_summary(year, month)

    if summary['transaction_count'] == 0:
        print(f"No transactions found for {year}-{month:02}")
        return

    # Determine formats
    formats = ['cli']
    if args.format:
        formats = [f.strip() for f in args.format.split(',')]

    # Generate report
    generate_report(summary, str(dirs['reports']), categorizer, formats)


def cmd_categories(args):
    """List all categories."""
    dirs = get_default_dirs()
    categorizer = Categorizer(str(dirs['config']))

    print("\nAvailable Categories:")
    print("-" * 60)
    print(f"{'Key':<15} {'Hebrew':<25} {'English':<20}")
    print("-" * 60)

    for key, data in categorizer.categories.items():
        name_he = data.get('name', key)
        name_en = data.get('name_en', '')
        keywords = ', '.join(data.get('keywords', [])[:3])
        if len(data.get('keywords', [])) > 3:
            keywords += '...'
        print(f"{key:<15} {name_he:<25} {name_en:<20}")

    print("-" * 60)


def cmd_override(args):
    """Add a category override."""
    dirs = get_default_dirs()
    categorizer = Categorizer(str(dirs['config']))

    description = args.description
    category = args.category

    # Check if category exists
    if category not in categorizer.categories:
        print(f"Unknown category: {category}")
        print("Available categories:")
        for key in categorizer.categories.keys():
            print(f"  - {key}")
        return

    if categorizer.add_override(description, category):
        cat_name = categorizer.categories[category].get('name', category)
        print(f"Added override: '{description}' -> {cat_name}")
    else:
        print("Failed to add override")


def cmd_overrides(args):
    """List all overrides."""
    dirs = get_default_dirs()
    categorizer = Categorizer(str(dirs['config']))

    overrides = categorizer.list_overrides()

    if not overrides:
        print("No overrides defined.")
        return

    print("\nCurrent Overrides:")
    print("-" * 60)
    print(f"{'Description':<40} {'Category':<20}")
    print("-" * 60)

    for desc, cat in overrides.items():
        if cat in categorizer.categories:
            cat_name = categorizer.categories[cat].get('name', cat)
        else:
            cat_name = cat
        print(f"{desc:<40} {cat_name:<20}")

    print("-" * 60)


def cmd_uncategorized(args):
    """Show uncategorized transactions."""
    dirs = get_default_dirs()
    storage = Storage(str(dirs['data']))
    categorizer = Categorizer(str(dirs['config']))

    transactions = storage.get_transactions(category='אחר')

    if not transactions:
        print("No uncategorized transactions.")
        return

    print(f"\nUncategorized Transactions ({len(transactions)} total):")
    print("-" * 70)

    for t in transactions:
        print(f"{t.date.strftime('%Y-%m-%d')} | {t.description[:40]:<40} | ₪{abs(t.amount):>10,.2f}")

    print("-" * 70)
    print("\nUse 'finance_tool.py override <description> <category>' to categorize")
    print("Or run 'finance_tool.py interactive' for interactive mode")


def cmd_interactive(args):
    """Interactive categorization mode."""
    dirs = get_default_dirs()
    storage = Storage(str(dirs['data']))
    categorizer = Categorizer(str(dirs['config']))

    transactions = storage.get_transactions()

    # Re-categorize all transactions
    categorizer.categorize_transactions(transactions)

    # Run interactive mode
    interactive_categorize(categorizer, transactions)

    # Re-save with new categories
    print("\nUpdating stored transactions with new categories...")
    storage.clear_all()
    storage.add_transactions(transactions)
    print("Done!")


def cmd_summary(args):
    """Show quick summary of all data."""
    dirs = get_default_dirs()
    storage = Storage(str(dirs['data']))

    months = storage.get_months()

    if not months:
        print("No data available. Import some statements first.")
        return

    print("\nData Summary:")
    print("-" * 50)
    print(f"Months with data: {len(months)}")
    print(f"Date range: {months[0]} to {months[-1]}")

    all_transactions = storage.get_transactions()
    income = sum(t.amount for t in all_transactions if t.amount > 0)
    expenses = sum(abs(t.amount) for t in all_transactions if t.amount < 0)

    print(f"Total transactions: {len(all_transactions)}")
    print(f"Total income: ₪{income:,.2f}")
    print(f"Total expenses: ₪{expenses:,.2f}")
    print(f"Net: ₪{income - expenses:,.2f}")
    print("-" * 50)


def main():
    parser = argparse.ArgumentParser(
        description='Finance Monitoring Tool - Track and analyze your spending',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python finance_tool.py import statement.xlsx
  python finance_tool.py import *.xlsx --force
  python finance_tool.py report --month=2026-01 --format=cli,csv,pdf
  python finance_tool.py override "המרכולית" סופרמרקט
  python finance_tool.py interactive
        """
    )

    subparsers = parser.add_subparsers(dest='command', help='Available commands')

    # Import command
    import_parser = subparsers.add_parser('import', help='Import statement files')
    import_parser.add_argument('files', nargs='+', help='Excel files to import')
    import_parser.add_argument('--force', '-f', action='store_true',
                               help='Re-import already processed files')
    import_parser.add_argument('--verbose', '-v', action='store_true',
                               help='Show detailed error messages')

    # Report command
    report_parser = subparsers.add_parser('report', help='Generate financial report')
    report_parser.add_argument('--month', '-m', help='Month to report (YYYY-MM)')
    report_parser.add_argument('--format', '-f', default='cli',
                               help='Output formats: cli,csv,pdf (comma-separated)')

    # Categories command
    subparsers.add_parser('categories', help='List all categories')

    # Override command
    override_parser = subparsers.add_parser('override', help='Add category override')
    override_parser.add_argument('description', help='Transaction description to match')
    override_parser.add_argument('category', help='Category key to assign')

    # Overrides command
    subparsers.add_parser('overrides', help='List all overrides')

    # Uncategorized command
    subparsers.add_parser('uncategorized', help='Show uncategorized transactions')

    # Interactive command
    subparsers.add_parser('interactive', help='Interactive categorization mode')

    # Summary command
    subparsers.add_parser('summary', help='Show data summary')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Dispatch to command handler
    commands = {
        'import': cmd_import,
        'report': cmd_report,
        'categories': cmd_categories,
        'override': cmd_override,
        'overrides': cmd_overrides,
        'uncategorized': cmd_uncategorized,
        'interactive': cmd_interactive,
        'summary': cmd_summary,
    }

    if args.command in commands:
        commands[args.command](args)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
