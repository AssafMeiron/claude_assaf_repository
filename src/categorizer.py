"""
Transaction categorization engine with override support.
"""

import json
import os
from typing import Dict, List, Optional, Tuple
from pathlib import Path


class Categorizer:
    """
    Categorizes transactions based on keywords and manual overrides.
    Overrides take priority over keyword matching.
    """

    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # Default to config directory relative to this file
            config_dir = Path(__file__).parent.parent / 'config'

        self.config_dir = Path(config_dir)
        self.categories: Dict = {}
        self.overrides: Dict = {}
        self._load_config()

    def _load_config(self):
        """Load categories and overrides from config files."""
        # Load categories
        categories_file = self.config_dir / 'categories.json'
        if categories_file.exists():
            with open(categories_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.categories = data.get('categories', {})

        # Load overrides
        overrides_file = self.config_dir / 'overrides.json'
        if overrides_file.exists():
            with open(overrides_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.overrides = data.get('overrides', {})

    def save_overrides(self):
        """Save overrides to config file."""
        overrides_file = self.config_dir / 'overrides.json'
        data = {
            "_comment": "Manual category overrides. Key is the business name (exact or partial match), value is the category key.",
            "overrides": self.overrides
        }
        with open(overrides_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def add_override(self, description: str, category_key: str) -> bool:
        """
        Add a manual override for a transaction description.

        Args:
            description: The transaction description to match
            category_key: The category key to assign

        Returns:
            True if successful, False if category doesn't exist
        """
        if category_key not in self.categories and category_key != 'אחר':
            return False

        self.overrides[description] = category_key
        self.save_overrides()
        return True

    def remove_override(self, description: str) -> bool:
        """Remove an override."""
        if description in self.overrides:
            del self.overrides[description]
            self.save_overrides()
            return True
        return False

    def list_overrides(self) -> Dict[str, str]:
        """List all current overrides."""
        return self.overrides.copy()

    def get_category_names(self) -> List[Tuple[str, str, str]]:
        """Get list of (key, hebrew_name, english_name) for all categories."""
        result = []
        for key, data in self.categories.items():
            result.append((key, data.get('name', key), data.get('name_en', '')))
        return result

    def categorize(self, description: str) -> Tuple[str, str, str]:
        """
        Categorize a transaction based on its description.

        Returns:
            Tuple of (category_key, category_name_hebrew, category_name_english)
        """
        description_lower = description.lower()
        description_clean = description.strip()

        # First, check overrides (exact match)
        if description_clean in self.overrides:
            cat_key = self.overrides[description_clean]
            if cat_key in self.categories:
                cat = self.categories[cat_key]
                return (cat_key, cat.get('name', cat_key), cat.get('name_en', ''))

        # Check overrides (partial match)
        for override_pattern, cat_key in self.overrides.items():
            if override_pattern.lower() in description_lower or description_lower in override_pattern.lower():
                if cat_key in self.categories:
                    cat = self.categories[cat_key]
                    return (cat_key, cat.get('name', cat_key), cat.get('name_en', ''))

        # Then, check keyword matching
        for cat_key, cat_data in self.categories.items():
            keywords = cat_data.get('keywords', [])
            for keyword in keywords:
                if keyword.lower() in description_lower:
                    return (cat_key, cat_data.get('name', cat_key), cat_data.get('name_en', ''))

        # Default to 'אחר' (Other)
        if 'אחר' in self.categories:
            other_cat = self.categories['אחר']
            return ('אחר', other_cat.get('name', 'אחר'), other_cat.get('name_en', 'Other'))

        return ('אחר', 'אחר', 'Other')

    def categorize_transactions(self, transactions: list) -> list:
        """
        Categorize a list of Transaction objects.
        Modifies the transactions in place and returns them.
        """
        for t in transactions:
            cat_key, cat_name, cat_name_en = self.categorize(t.description)
            t.category = cat_key
        return transactions


def interactive_categorize(categorizer: Categorizer, transactions: list):
    """
    Interactive mode to review and fix categorizations.
    """
    uncategorized = [t for t in transactions if t.category == 'אחר']

    if not uncategorized:
        print("All transactions are categorized!")
        return

    print(f"\n{len(uncategorized)} transactions in 'Other' category:")
    print("-" * 60)

    categories = categorizer.get_category_names()
    print("\nAvailable categories:")
    for i, (key, name_he, name_en) in enumerate(categories, 1):
        print(f"  {i:2}. {name_he} ({name_en})")

    print("\nFor each uncategorized transaction, enter category number or 's' to skip:")
    print("-" * 60)

    for t in uncategorized:
        print(f"\n{t.date.strftime('%Y-%m-%d')} | {t.description[:40]:40} | {t.amount:>10.2f} ILS")
        choice = input("Category number (or 's' to skip, 'q' to quit): ").strip()

        if choice.lower() == 'q':
            break
        if choice.lower() == 's':
            continue

        try:
            idx = int(choice) - 1
            if 0 <= idx < len(categories):
                cat_key = categories[idx][0]
                categorizer.add_override(t.description, cat_key)
                t.category = cat_key
                print(f"  -> Added override: '{t.description}' -> {categories[idx][1]}")
        except ValueError:
            print("  -> Skipped (invalid input)")


if __name__ == '__main__':
    # Test categorization
    cat = Categorizer()

    test_descriptions = [
        "המרכולית",
        "CLAUDE.AI SUBSCRIPTION",
        "משכורת/לאומי",
        "ועד בית - עזרא הסופר",
        "רכבת ישראל - תל אביב",
        "הראל חיים",
        "Unknown Business",
    ]

    print("Category test:")
    for desc in test_descriptions:
        key, name_he, name_en = cat.categorize(desc)
        print(f"  {desc:35} -> {name_he} ({name_en})")
