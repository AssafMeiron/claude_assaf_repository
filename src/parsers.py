"""
Parsers for bank and credit card statements.
Supports:
- Bank Yahav Excel statements (תנועות בחשבון עו״ש)
- Isracard credit card Excel statements
"""

import pandas as pd
from datetime import datetime
from typing import List, Dict, Optional
from dataclasses import dataclass, asdict
import re


@dataclass
class Transaction:
    """Represents a single financial transaction."""
    date: datetime
    description: str
    amount: float
    currency: str
    source: str  # 'bank' or 'credit_card'
    source_file: str
    card_number: Optional[str] = None
    category: Optional[str] = None

    def to_dict(self) -> Dict:
        d = asdict(self)
        d['date'] = self.date.isoformat() if self.date else None
        return d

    @classmethod
    def from_dict(cls, d: Dict) -> 'Transaction':
        d = d.copy()
        if d.get('date'):
            d['date'] = datetime.fromisoformat(d['date'])
        return cls(**d)


def parse_date(date_val) -> Optional[datetime]:
    """Parse various date formats."""
    if pd.isna(date_val):
        return None

    if isinstance(date_val, datetime):
        return date_val

    if isinstance(date_val, pd.Timestamp):
        return date_val.to_pydatetime()

    if isinstance(date_val, str):
        # Try different formats
        date_str = date_val.strip()
        formats = [
            '%d.%m.%y',      # 30.01.26
            '%d.%m.%Y',      # 30.01.2026
            '%Y-%m-%d',      # 2026-01-30
            '%d/%m/%y',      # 30/01/26
            '%d/%m/%Y',      # 30/01/2026
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue

    return None


def parse_amount(amount_val) -> Optional[float]:
    """Parse amount values, handling various formats."""
    if pd.isna(amount_val):
        return None

    if isinstance(amount_val, (int, float)):
        return float(amount_val)

    if isinstance(amount_val, str):
        # Remove currency symbols and whitespace
        cleaned = re.sub(r'[₪$€,\s]', '', amount_val)
        try:
            return float(cleaned)
        except ValueError:
            return None

    return None


def parse_bank_statement(file_path: str) -> List[Transaction]:
    """
    Parse Bank Yahav statement (תנועות בחשבון עו״ש).

    Expected structure:
    - Header rows at the top (metadata)
    - Data columns: תאריך, תאריך ערך, אסמכתא, תיאור פעולה, חובה(₪), זכות(₪), יתרה
    """
    transactions = []

    # Read Excel file
    df = pd.read_excel(file_path)

    # Find the header row (contains 'תאריך' and 'תיאור פעולה')
    header_row = None
    for idx, row in df.iterrows():
        row_values = [str(v) for v in row.values if not pd.isna(v)]
        if any('תאריך' in v for v in row_values) and any('תיאור פעולה' in v or 'תיאור' in v for v in row_values):
            header_row = idx
            break

    if header_row is None:
        raise ValueError(f"Could not find header row in bank statement: {file_path}")

    # Process rows after header
    for idx in range(header_row + 1, len(df)):
        row = df.iloc[idx]

        # Column indices (based on analysis):
        # 0: תאריך, 3: תיאור פעולה, 4: חובה (debit), 5: זכות (credit)
        date_val = row.iloc[0] if len(row) > 0 else None
        description = row.iloc[3] if len(row) > 3 else None
        debit = row.iloc[4] if len(row) > 4 else None
        credit = row.iloc[5] if len(row) > 5 else None

        date = parse_date(date_val)
        if date is None:
            continue

        # Clean description
        if pd.isna(description):
            description = ""
        description = str(description).strip()

        # Handle both debit (expense) and credit (income)
        debit_amount = parse_amount(debit)
        credit_amount = parse_amount(credit)

        # Create transaction for debit (expense)
        if debit_amount and debit_amount > 0:
            transactions.append(Transaction(
                date=date,
                description=description,
                amount=-debit_amount,  # Negative for expenses
                currency='ILS',
                source='bank',
                source_file=file_path
            ))

        # Create transaction for credit (income)
        if credit_amount and credit_amount > 0:
            transactions.append(Transaction(
                date=date,
                description=description,
                amount=credit_amount,  # Positive for income
                currency='ILS',
                source='bank',
                source_file=file_path
            ))

    return transactions


def parse_credit_card_statement(file_path: str) -> List[Transaction]:
    """
    Parse Isracard credit card statement.

    Expected structure:
    - Multiple sections with different headers
    - Main transaction section has: תאריך רכישה, שם בית עסק, סכום עסקה, מטבע עסקה, סכום חיוב
    """
    transactions = []

    # Read Excel file
    df = pd.read_excel(file_path)

    # Extract card number from filename or content
    card_number = None
    file_name = file_path.split('/')[-1]
    match = re.search(r'(\d{4})', file_name)
    if match:
        card_number = match.group(1)

    # Also try to find card number in the data
    for idx, row in df.iterrows():
        for val in row.values:
            if not pd.isna(val) and isinstance(val, str):
                match = re.search(r'[-–]\s*(\d{4})\s*$', val)
                if match:
                    card_number = match.group(1)
                    break

    # Find transaction sections and parse them
    in_transaction_section = False
    current_header_row = None

    for idx, row in df.iterrows():
        row_values = [str(v) if not pd.isna(v) else '' for v in row.values]
        row_text = ' '.join(row_values)

        # Check for transaction section headers
        if 'תאריך רכישה' in row_text and 'שם בית עסק' in row_text:
            in_transaction_section = True
            current_header_row = idx
            continue

        # Check for section end (totals or empty section)
        if in_transaction_section:
            first_val = row.iloc[0] if len(row) > 0 else None

            # Skip if first column is empty or contains summary text
            if pd.isna(first_val):
                continue

            first_str = str(first_val)
            if 'סה"כ' in first_str or first_str.strip() == '':
                in_transaction_section = False
                continue

            # Parse transaction row
            # Columns: 0=date, 1=business name, 2=amount, 3=currency, 4=charge amount (ILS)
            date_val = row.iloc[0]
            business_name = row.iloc[1] if len(row) > 1 else None
            amount = row.iloc[2] if len(row) > 2 else None
            currency = row.iloc[3] if len(row) > 3 else None
            charge_amount = row.iloc[4] if len(row) > 4 else None

            date = parse_date(date_val)
            if date is None:
                continue

            # Clean business name
            if pd.isna(business_name):
                business_name = ""
            business_name = str(business_name).strip()

            # Skip empty business names
            if not business_name or business_name == 'טרם נקלט':
                continue

            # Parse amounts
            original_amount = parse_amount(amount)
            ils_amount = parse_amount(charge_amount)

            # Determine currency
            currency_str = 'ILS'
            if not pd.isna(currency):
                currency_val = str(currency).strip()
                if '$' in currency_val:
                    currency_str = 'USD'
                elif '€' in currency_val:
                    currency_str = 'EUR'

            # Use ILS charge amount if available, otherwise original amount
            final_amount = ils_amount if ils_amount is not None else original_amount
            if final_amount is None:
                continue

            # All credit card transactions are expenses (negative)
            transactions.append(Transaction(
                date=date,
                description=business_name,
                amount=-abs(final_amount),  # Negative for expenses
                currency='ILS',  # We use the ILS charge amount
                source='credit_card',
                source_file=file_path,
                card_number=card_number
            ))

    return transactions


def parse_file(file_path: str) -> List[Transaction]:
    """
    Auto-detect file type and parse accordingly.
    """
    file_lower = file_path.lower()

    # Try to detect file type from content or name
    try:
        df = pd.read_excel(file_path)
        first_rows_text = ' '.join([str(v) for v in df.iloc[:10].values.flatten() if not pd.isna(v)])

        if 'תנועות בחשבון' in first_rows_text or 'בנק יהב' in first_rows_text:
            return parse_bank_statement(file_path)
        elif 'פירוט עסקאות' in first_rows_text or 'ישראכרט' in first_rows_text or 'מסטרקארד' in first_rows_text:
            return parse_credit_card_statement(file_path)
        else:
            # Try based on filename
            if 'עו' in file_path or 'bank' in file_lower:
                return parse_bank_statement(file_path)
            else:
                return parse_credit_card_statement(file_path)
    except Exception as e:
        raise ValueError(f"Could not parse file {file_path}: {e}")


if __name__ == '__main__':
    # Test parsing
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        transactions = parse_file(file_path)
        print(f"Parsed {len(transactions)} transactions from {file_path}")
        for t in transactions[:5]:
            print(f"  {t.date.strftime('%Y-%m-%d')} | {t.description[:30]:30} | {t.amount:>10.2f} ILS")
