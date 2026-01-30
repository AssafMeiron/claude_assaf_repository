"""
Historical data storage for transactions.
Stores transactions in JSON format for easy querying and trend analysis.
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from dataclasses import asdict

from .parsers import Transaction


class Storage:
    """
    Manages historical transaction data storage.
    Data is stored in JSON files organized by year-month.
    """

    def __init__(self, data_dir: str = None):
        if data_dir is None:
            data_dir = Path(__file__).parent.parent / 'data'

        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        self.transactions_file = self.data_dir / 'transactions.json'
        self.processed_files_file = self.data_dir / 'processed_files.json'

        self._transactions: List[Dict] = []
        self._processed_files: List[str] = []
        self._load()

    def _load(self):
        """Load existing data from files."""
        if self.transactions_file.exists():
            with open(self.transactions_file, 'r', encoding='utf-8') as f:
                self._transactions = json.load(f)

        if self.processed_files_file.exists():
            with open(self.processed_files_file, 'r', encoding='utf-8') as f:
                self._processed_files = json.load(f)

    def _save(self):
        """Save data to files."""
        with open(self.transactions_file, 'w', encoding='utf-8') as f:
            json.dump(self._transactions, f, ensure_ascii=False, indent=2)

        with open(self.processed_files_file, 'w', encoding='utf-8') as f:
            json.dump(self._processed_files, f, ensure_ascii=False, indent=2)

    def is_file_processed(self, file_path: str) -> bool:
        """Check if a file has already been processed."""
        file_name = os.path.basename(file_path)
        return file_name in self._processed_files

    def mark_file_processed(self, file_path: str):
        """Mark a file as processed."""
        file_name = os.path.basename(file_path)
        if file_name not in self._processed_files:
            self._processed_files.append(file_name)
            self._save()

    def add_transactions(self, transactions: List[Transaction], source_file: str = None):
        """
        Add transactions to storage, avoiding duplicates.
        Duplicates are detected by date + description + amount.
        """
        added_count = 0

        for t in transactions:
            t_dict = t.to_dict()

            # Check for duplicates
            is_duplicate = False
            for existing in self._transactions:
                if (existing['date'] == t_dict['date'] and
                    existing['description'] == t_dict['description'] and
                    abs(existing['amount'] - t_dict['amount']) < 0.01):
                    is_duplicate = True
                    break

            if not is_duplicate:
                self._transactions.append(t_dict)
                added_count += 1

        if added_count > 0:
            self._save()

        if source_file:
            self.mark_file_processed(source_file)

        return added_count

    def get_transactions(self,
                         start_date: datetime = None,
                         end_date: datetime = None,
                         category: str = None,
                         source: str = None) -> List[Transaction]:
        """
        Get transactions with optional filters.
        """
        result = []

        for t_dict in self._transactions:
            t = Transaction.from_dict(t_dict)

            if start_date and t.date < start_date:
                continue
            if end_date and t.date > end_date:
                continue
            if category and t.category != category:
                continue
            if source and t.source != source:
                continue

            result.append(t)

        # Sort by date
        result.sort(key=lambda x: x.date)
        return result

    def get_months(self) -> List[str]:
        """Get list of year-months with data (YYYY-MM format)."""
        months = set()
        for t_dict in self._transactions:
            if t_dict.get('date'):
                date = datetime.fromisoformat(t_dict['date'])
                months.add(date.strftime('%Y-%m'))
        return sorted(months)

    def get_summary_by_category(self,
                                 start_date: datetime = None,
                                 end_date: datetime = None) -> Dict[str, float]:
        """
        Get spending summary by category for a date range.
        Returns dict of category -> total amount (expenses are negative).
        """
        transactions = self.get_transactions(start_date=start_date, end_date=end_date)

        summary = {}
        for t in transactions:
            cat = t.category or 'אחר'
            if cat not in summary:
                summary[cat] = 0.0
            summary[cat] += t.amount

        return summary

    def _is_credit_card_transfer(self, transaction: Transaction) -> bool:
        """
        Check if a bank transaction is a credit card payment.
        These should be excluded from expense totals when credit card
        statements are also imported (to avoid double-counting).
        """
        if transaction.source != 'bank':
            return False

        # Common credit card company names in bank statements
        cc_keywords = [
            'ישראכרט',
            'מקס איט',
            'כאל',
            'לאומי קארד',
            'אמריקן אקספרס',
            'דיינרס',
            'visa cal',
            'mastercard',
        ]

        desc_lower = transaction.description.lower()
        for keyword in cc_keywords:
            if keyword in desc_lower or keyword.lower() in desc_lower:
                return True

        return False

    def get_monthly_summary(self, year: int, month: int, exclude_cc_transfers: bool = True) -> Dict:
        """
        Get detailed monthly summary.

        Args:
            year: Year to summarize
            month: Month to summarize
            exclude_cc_transfers: If True, exclude credit card payments from bank
                                  statements to avoid double-counting with CC statements
        """
        start_date = datetime(year, month, 1)
        if month == 12:
            end_date = datetime(year + 1, 1, 1)
        else:
            end_date = datetime(year, month + 1, 1)

        transactions = self.get_transactions(start_date=start_date, end_date=end_date)

        # Check if we have both bank and credit card data
        has_bank = any(t.source == 'bank' for t in transactions)
        has_cc = any(t.source == 'credit_card' for t in transactions)

        # Separate income, expenses, and excluded transfers
        income = []
        expenses = []
        excluded_transfers = []

        for t in transactions:
            # Exclude credit card transfers from bank if we have CC data
            if exclude_cc_transfers and has_bank and has_cc and self._is_credit_card_transfer(t):
                excluded_transfers.append(t)
                continue

            if t.amount > 0:
                income.append(t)
            else:
                expenses.append(t)

        # Summarize by category
        expense_by_category = {}
        for t in expenses:
            cat = t.category or 'אחר'
            if cat not in expense_by_category:
                expense_by_category[cat] = {'total': 0.0, 'transactions': []}
            expense_by_category[cat]['total'] += abs(t.amount)
            expense_by_category[cat]['transactions'].append(t)

        income_by_category = {}
        for t in income:
            cat = t.category or 'אחר'
            if cat not in income_by_category:
                income_by_category[cat] = {'total': 0.0, 'transactions': []}
            income_by_category[cat]['total'] += t.amount
            income_by_category[cat]['transactions'].append(t)

        total_expenses = sum(abs(t.amount) for t in expenses)
        total_income = sum(t.amount for t in income)
        total_excluded = sum(abs(t.amount) for t in excluded_transfers)

        return {
            'year': year,
            'month': month,
            'total_expenses': total_expenses,
            'total_income': total_income,
            'balance': total_income - total_expenses,
            'expense_by_category': expense_by_category,
            'income_by_category': income_by_category,
            'transaction_count': len(transactions),
            'excluded_cc_transfers': excluded_transfers,
            'total_excluded': total_excluded
        }

    def clear_all(self):
        """Clear all stored data (use with caution!)."""
        self._transactions = []
        self._processed_files = []
        self._save()


if __name__ == '__main__':
    # Test storage
    storage = Storage()
    print(f"Loaded {len(storage._transactions)} transactions")
    print(f"Processed files: {storage._processed_files}")
    print(f"Months with data: {storage.get_months()}")
