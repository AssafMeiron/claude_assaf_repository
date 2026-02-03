"""
Finance Monitoring Tool - Web App
Run with: streamlit run app.py
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import re
import json

# Page config
st.set_page_config(
    page_title="Finance Monitor",
    page_icon="💰",
    layout="wide"
)

# Categories with keywords
CATEGORIES = {
    "משכנתא": {"name": "משכנתא", "name_en": "Mortgage", "keywords": ["משכנתא", "פועלים-משכנתא"]},
    "ועד_בית": {"name": "ועד בית", "name_en": "HOA", "keywords": ["ועד בית", "עזרא הסופר"]},
    "ביטוחים": {"name": "ביטוחים", "name_en": "Insurance", "keywords": ["הראל", "מגדל", "כלל", "ביטוח", "פניקס", "מנורה", "קרן מכבי"]},
    "חשמל": {"name": "חשמל", "name_en": "Electricity", "keywords": ["חברת חשמל", "חשמל"]},
    "מים": {"name": "מים", "name_en": "Water", "keywords": ["מי ", "מים", "מקורות"]},
    "סופרמרקט": {"name": "סופרמרקט", "name_en": "Supermarket", "keywords": ["רמי לוי", "שופרסל", "יוחננוף", "מגה", "ויקטורי", "סופר", "המרכולית", "קטיף עצמי", "אושר עד"]},
    "מסעדות": {"name": "מסעדות", "name_en": "Restaurants", "keywords": ["מסעדה", "קפה", "פיצה", "מקדונלד", "בורגר", "שווארמה", "לחמנינה", "ארקפה", "מוניציפל", "נונומימי"]},
    "רכב_ודלק": {"name": "רכב ודלק", "name_en": "Car & Fuel", "keywords": ["דלק", "סונול", "פז", "דור אלון", "yellow", "רכב", "מנטה", "ten"]},
    "ילדים": {"name": "ילדים", "name_en": "Kids", "keywords": ["צעצוע", "toys", "ילדים", "בייבי", "תמר זמיר"]},
    "ספורט": {"name": "ספורט", "name_en": "Sports", "keywords": ["ספורט", "כושר", "gym", "חדר כושר"]},
    "פארמה": {"name": "פארמה", "name_en": "Pharmacy", "keywords": ["סופר פארם", "פארם", "בית מרקחת"]},
    "תרומה": {"name": "תרומה", "name_en": "Donations", "keywords": ["תרומה", "צדקה", "עמותה", "מפלגת המילואימניקים"]},
    "תוכנות": {"name": "תוכנות", "name_en": "Software", "keywords": ["GOOGLE", "APPLE", "NETFLIX", "SPOTIFY", "AMAZON", "MICROSOFT", "CLAUDE"]},
    "אטט": {"name": "א.ט.ט", "name_en": "Internet/TV/Phone", "keywords": ["בזק", "הוט", "פרטנר", "סלקום", "גולן"]},
    "תחבורה": {"name": "תחבורה", "name_en": "Transportation", "keywords": ["רכבת ישראל", "אגד", "דן", "מטרופולין"]},
    "קניות": {"name": "קניות", "name_en": "Shopping", "keywords": ["איקאה", "זארה", "H&M", "קניון", "ביג", "עזריאלי", "סוהו"]},
    "בילויים": {"name": "בילויים", "name_en": "Entertainment", "keywords": ["סינמה", "קולנוע", "הופעה", "תיאטרון", "באולינג", "OUTSIDER"]},
    "משקאות": {"name": "משקאות", "name_en": "Beverages", "keywords": ["משקאות", "החן שב", "שיבולת הארץ", "יין", "בירה", "אקספרס"]},
    "מזומן": {"name": "מזומן", "name_en": "Cash", "keywords": ["כספומט", "משיכה", "ATM", "מזומן", "שיק"]},
    "הכנסה": {"name": "הכנסה", "name_en": "Income", "keywords": ["משכורת", "קצבת ילדים", "החזר", "זיכוי", "מילואים", "מופ\"ת"]},
    "העברות_כא": {"name": "העברות כ.א", "name_en": "CC Transfers", "keywords": ["ישראכרט", "מקס איט", "כאל", "לאומי קארד"]},
    "פיצוציות": {"name": "פיצוציות", "name_en": "Misc", "keywords": ["נאייקס", "מינימרקט", "קיוסק"]},
    "אחר": {"name": "אחר", "name_en": "Other", "keywords": []},
}

# Initialize session state
if 'transactions' not in st.session_state:
    st.session_state.transactions = pd.DataFrame()
if 'overrides' not in st.session_state:
    st.session_state.overrides = {}


def categorize(description: str, overrides: dict) -> str:
    """Categorize a transaction based on description."""
    desc_lower = description.lower()

    # Check overrides first
    for pattern, category in overrides.items():
        if pattern.lower() in desc_lower:
            return category

    # Check keywords
    for cat_key, cat_data in CATEGORIES.items():
        for keyword in cat_data.get("keywords", []):
            if keyword.lower() in desc_lower:
                return cat_key

    return "אחר"


def is_cc_transfer(description: str) -> bool:
    """Check if transaction is a credit card transfer."""
    cc_keywords = ["ישראכרט", "מקס איט", "כאל", "לאומי קארד"]
    desc_lower = description.lower()
    return any(kw.lower() in desc_lower for kw in cc_keywords)


def parse_bank_statement(df: pd.DataFrame) -> pd.DataFrame:
    """Parse bank statement Excel file."""
    # Find header row
    header_row = None
    for idx, row in df.iterrows():
        row_str = ' '.join([str(v) for v in row.values if pd.notna(v)])
        if 'תאריך' in row_str and ('תיאור' in row_str or 'פעולה' in row_str):
            header_row = idx
            break

    if header_row is None:
        st.error("Could not find header row in bank statement")
        return pd.DataFrame()

    transactions = []
    for idx in range(header_row + 1, len(df)):
        row = df.iloc[idx]
        date_val = row.iloc[0] if len(row) > 0 else None
        description = row.iloc[3] if len(row) > 3 else ""
        debit = row.iloc[4] if len(row) > 4 else None
        credit = row.iloc[5] if len(row) > 5 else None

        if pd.isna(date_val):
            continue

        # Parse date
        if isinstance(date_val, str):
            try:
                date_val = pd.to_datetime(date_val)
            except:
                continue

        description = str(description) if pd.notna(description) else ""

        # Debit (expense)
        if pd.notna(debit) and float(debit) > 0:
            transactions.append({
                'date': date_val,
                'description': description,
                'amount': -float(debit),
                'source': 'bank'
            })

        # Credit (income)
        if pd.notna(credit) and float(credit) > 0:
            transactions.append({
                'date': date_val,
                'description': description,
                'amount': float(credit),
                'source': 'bank'
            })

    return pd.DataFrame(transactions)


def parse_credit_card_statement(df: pd.DataFrame) -> pd.DataFrame:
    """Parse credit card statement Excel file."""
    transactions = []
    in_section = False

    for idx, row in df.iterrows():
        row_str = ' '.join([str(v) for v in row.values if pd.notna(v)])

        # Check for transaction section header
        if 'תאריך רכישה' in row_str and 'שם בית עסק' in row_str:
            in_section = True
            continue

        if in_section:
            date_val = row.iloc[0] if len(row) > 0 else None
            business = row.iloc[1] if len(row) > 1 else None
            amount = row.iloc[4] if len(row) > 4 else row.iloc[2] if len(row) > 2 else None

            if pd.isna(date_val) or 'סה"כ' in str(date_val):
                continue

            # Parse date
            if isinstance(date_val, str):
                try:
                    date_val = pd.to_datetime(date_val, format='%d.%m.%y')
                except:
                    try:
                        date_val = pd.to_datetime(date_val)
                    except:
                        continue

            if pd.isna(business) or str(business).strip() in ['', 'טרם נקלט']:
                continue

            if pd.notna(amount):
                try:
                    amount_val = float(str(amount).replace(',', '').replace('₪', ''))
                    transactions.append({
                        'date': date_val,
                        'description': str(business),
                        'amount': -abs(amount_val),
                        'source': 'credit_card'
                    })
                except:
                    pass

    return pd.DataFrame(transactions)


# Main UI
st.title("💰 Finance Monitor")
st.markdown("### ניטור פיננסי אישי")

# Sidebar for file upload
with st.sidebar:
    st.header("📁 Upload Files")

    bank_file = st.file_uploader("Bank Statement (תנועות בחשבון)", type=['xlsx', 'xls'])
    cc_file = st.file_uploader("Credit Card Statement", type=['xlsx', 'xls'])

    if st.button("🔄 Process Files", type="primary"):
        all_transactions = []

        if bank_file:
            with st.spinner("Processing bank statement..."):
                bank_df = pd.read_excel(bank_file)
                bank_trans = parse_bank_statement(bank_df)
                if not bank_trans.empty:
                    all_transactions.append(bank_trans)
                    st.success(f"✓ Bank: {len(bank_trans)} transactions")

        if cc_file:
            with st.spinner("Processing credit card..."):
                cc_df = pd.read_excel(cc_file)
                cc_trans = parse_credit_card_statement(cc_df)
                if not cc_trans.empty:
                    all_transactions.append(cc_trans)
                    st.success(f"✓ Credit Card: {len(cc_trans)} transactions")

        if all_transactions:
            st.session_state.transactions = pd.concat(all_transactions, ignore_index=True)
            # Categorize
            st.session_state.transactions['category'] = st.session_state.transactions['description'].apply(
                lambda x: categorize(x, st.session_state.overrides)
            )
            st.session_state.transactions['is_cc_transfer'] = st.session_state.transactions.apply(
                lambda x: x['source'] == 'bank' and is_cc_transfer(x['description']), axis=1
            )
            st.success(f"✅ Total: {len(st.session_state.transactions)} transactions loaded!")

# Main content
if not st.session_state.transactions.empty:
    df = st.session_state.transactions.copy()

    # Check if we have both sources
    has_both = len(df['source'].unique()) > 1

    # Filter out CC transfers if we have both
    if has_both:
        df_expenses = df[~df['is_cc_transfer']]
        excluded = df[df['is_cc_transfer']]
    else:
        df_expenses = df
        excluded = pd.DataFrame()

    # Calculate totals
    income = df_expenses[df_expenses['amount'] > 0]['amount'].sum()
    expenses = abs(df_expenses[df_expenses['amount'] < 0]['amount'].sum())
    balance = income - expenses

    # Summary cards
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("💵 הכנסות / Income", f"₪{income:,.0f}")
    with col2:
        st.metric("💸 הוצאות / Expenses", f"₪{expenses:,.0f}")
    with col3:
        st.metric("📊 מאזן / Balance", f"₪{balance:,.0f}", delta=f"₪{balance:,.0f}")

    # Show excluded transfers
    if not excluded.empty:
        with st.expander(f"ℹ️ Excluded {len(excluded)} CC transfers (₪{abs(excluded['amount'].sum()):,.0f})"):
            st.dataframe(excluded[['date', 'description', 'amount']])

    st.markdown("---")

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📊 Categories", "📋 Transactions", "⚙️ Overrides"])

    with tab1:
        st.subheader("הוצאות לפי קטגוריה / Expenses by Category")

        # Calculate by category (expenses only, excluding CC transfers)
        expense_df = df_expenses[df_expenses['amount'] < 0].copy()
        expense_df['amount'] = expense_df['amount'].abs()

        category_totals = expense_df.groupby('category')['amount'].sum().sort_values(ascending=False)

        # Create summary table
        summary_data = []
        for cat, amount in category_totals.items():
            cat_info = CATEGORIES.get(cat, {"name": cat, "name_en": ""})
            pct = (amount / expenses * 100) if expenses > 0 else 0
            summary_data.append({
                "קטגוריה": cat_info.get("name", cat),
                "Category": cat_info.get("name_en", ""),
                "סכום": f"₪{amount:,.0f}",
                "אחוז": f"{pct:.1f}%"
            })

        summary_df = pd.DataFrame(summary_data)
        st.dataframe(summary_df, use_container_width=True, hide_index=True)

        # Bar chart
        st.bar_chart(category_totals)

    with tab2:
        st.subheader("כל התנועות / All Transactions")

        # Filter options
        col1, col2 = st.columns(2)
        with col1:
            category_filter = st.selectbox("Filter by category", ["All"] + list(df['category'].unique()))
        with col2:
            source_filter = st.selectbox("Filter by source", ["All", "bank", "credit_card"])

        display_df = df_expenses.copy()
        if category_filter != "All":
            display_df = display_df[display_df['category'] == category_filter]
        if source_filter != "All":
            display_df = display_df[display_df['source'] == source_filter]

        # Format for display
        display_df = display_df.sort_values('date', ascending=False)
        display_df['amount_display'] = display_df['amount'].apply(lambda x: f"₪{x:,.2f}")
        display_df['date_display'] = display_df['date'].dt.strftime('%Y-%m-%d')

        st.dataframe(
            display_df[['date_display', 'description', 'amount_display', 'category', 'source']].rename(columns={
                'date_display': 'תאריך',
                'description': 'תיאור',
                'amount_display': 'סכום',
                'category': 'קטגוריה',
                'source': 'מקור'
            }),
            use_container_width=True,
            hide_index=True
        )

    with tab3:
        st.subheader("⚙️ Fix Categorization")
        st.markdown("Add rules to fix miscategorized transactions")

        # Show uncategorized
        uncategorized = df_expenses[df_expenses['category'] == 'אחר']
        if not uncategorized.empty:
            st.warning(f"⚠️ {len(uncategorized)} uncategorized transactions:")
            for _, row in uncategorized.iterrows():
                st.text(f"  • {row['description']}: ₪{abs(row['amount']):,.0f}")

        # Add override form
        st.markdown("### Add Override")
        col1, col2 = st.columns(2)
        with col1:
            pattern = st.text_input("Description pattern", placeholder="e.g., תמר זמיר")
        with col2:
            category = st.selectbox("Category", list(CATEGORIES.keys()))

        if st.button("➕ Add Override"):
            if pattern:
                st.session_state.overrides[pattern] = category
                # Re-categorize
                st.session_state.transactions['category'] = st.session_state.transactions['description'].apply(
                    lambda x: categorize(x, st.session_state.overrides)
                )
                st.success(f"Added: '{pattern}' → {CATEGORIES[category]['name']}")
                st.rerun()

        # Show current overrides
        if st.session_state.overrides:
            st.markdown("### Current Overrides")
            for pattern, cat in st.session_state.overrides.items():
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.text(pattern)
                with col2:
                    st.text(CATEGORIES[cat]['name'])
                with col3:
                    if st.button("🗑️", key=f"del_{pattern}"):
                        del st.session_state.overrides[pattern]
                        st.rerun()

else:
    # Welcome screen
    st.info("👈 Upload your bank and credit card files in the sidebar to get started!")

    st.markdown("""
    ### How to use:
    1. **Upload** your bank statement (תנועות בחשבון עו״ש.xls)
    2. **Upload** your credit card statement (e.g., 0429_02_2026.xlsx)
    3. Click **Process Files**
    4. View your spending breakdown!

    ### Features:
    - 📊 Automatic categorization
    - 🔄 Excludes double-counted CC transfers
    - ⚙️ Fix miscategorized transactions with overrides
    """)
