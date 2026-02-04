"""
Finance Monitoring Tool v2 - Modern Web App
Features:
- Google Sheets storage for persistence
- Multi-month tracking & trend analysis
- Multiple credit cards (Assaf + Tehila)
- Per-transaction category editing
- One-time/special expense exclusion
- Modern UI
"""

import streamlit as st
import pandas as pd
from datetime import datetime
import plotly.express as px
import plotly.graph_objects as go
from streamlit_gsheets import GSheetsConnection
import json

# =============================================================================
# Page Config & Styling
# =============================================================================
st.set_page_config(
    page_title="💰 Finance Monitor",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for modern look
st.markdown("""
<style>
    /* Main background */
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }

    /* Cards */
    .metric-card {
        background: linear-gradient(135deg, #0f3460 0%, #1a1a2e 100%);
        border-radius: 16px;
        padding: 20px;
        border: 1px solid #e94560;
        box-shadow: 0 4px 15px rgba(233, 69, 96, 0.2);
    }

    /* Headers */
    h1, h2, h3 {
        color: #e94560 !important;
    }

    /* Metric values */
    [data-testid="stMetricValue"] {
        font-size: 2rem !important;
        color: #00d9ff !important;
    }

    /* Sidebar */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #0f3460 100%);
    }

    /* Buttons */
    .stButton > button {
        background: linear-gradient(90deg, #e94560 0%, #0f3460 100%);
        color: white;
        border: none;
        border-radius: 10px;
        padding: 10px 25px;
        font-weight: bold;
    }

    .stButton > button:hover {
        background: linear-gradient(90deg, #0f3460 0%, #e94560 100%);
        transform: scale(1.02);
    }

    /* Tables */
    .dataframe {
        border-radius: 10px !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }

    .stTabs [data-baseweb="tab"] {
        background-color: #0f3460;
        border-radius: 10px;
        color: white;
        padding: 10px 20px;
    }

    .stTabs [aria-selected="true"] {
        background-color: #e94560 !important;
    }
</style>
""", unsafe_allow_html=True)

# =============================================================================
# Categories Configuration
# =============================================================================
CATEGORIES = {
    "משכנתא": {"name": "משכנתא", "name_en": "Mortgage", "icon": "🏠", "keywords": ["משכנתא", "פועלים-משכנתא"]},
    "ועד_בית": {"name": "ועד בית", "name_en": "HOA", "icon": "🏢", "keywords": ["ועד בית", "עזרא הסופר"]},
    "ביטוחים": {"name": "ביטוחים", "name_en": "Insurance", "icon": "🛡️", "keywords": ["הראל", "מגדל", "כלל", "ביטוח", "פניקס", "מנורה", "קרן מכבי"]},
    "חשמל": {"name": "חשמל", "name_en": "Electricity", "icon": "⚡", "keywords": ["חברת חשמל", "חשמל"]},
    "מים": {"name": "מים", "name_en": "Water", "icon": "💧", "keywords": ["מי ", "מים", "מקורות"]},
    "סופרמרקט": {"name": "סופרמרקט", "name_en": "Supermarket", "icon": "🛒", "keywords": ["רמי לוי", "שופרסל", "יוחננוף", "מגה", "ויקטורי", "סופר", "המרכולית", "קטיף עצמי", "אושר עד"]},
    "מסעדות": {"name": "מסעדות", "name_en": "Restaurants", "icon": "🍽️", "keywords": ["מסעדה", "קפה", "פיצה", "מקדונלד", "בורגר", "שווארמה", "לחמנינה", "ארקפה", "מוניציפל", "נונומימי"]},
    "רכב_ודלק": {"name": "רכב ודלק", "name_en": "Car & Fuel", "icon": "🚗", "keywords": ["דלק", "סונול", "פז", "דור אלון", "yellow", "רכב", "מנטה", "ten"]},
    "ילדים": {"name": "ילדים", "name_en": "Kids", "icon": "👶", "keywords": ["צעצוע", "toys", "ילדים", "בייבי", "תמר זמיר"]},
    "ספורט": {"name": "ספורט", "name_en": "Sports", "icon": "🏃", "keywords": ["ספורט", "כושר", "gym", "חדר כושר"]},
    "פארמה": {"name": "פארמה", "name_en": "Pharmacy", "icon": "💊", "keywords": ["סופר פארם", "פארם", "בית מרקחת"]},
    "תרומה": {"name": "תרומה", "name_en": "Donations", "icon": "❤️", "keywords": ["תרומה", "צדקה", "עמותה", "מפלגת המילואימניקים"]},
    "תוכנות": {"name": "תוכנות", "name_en": "Software", "icon": "💻", "keywords": ["GOOGLE", "APPLE", "NETFLIX", "SPOTIFY", "AMAZON", "MICROSOFT", "CLAUDE"]},
    "אטט": {"name": "א.ט.ט", "name_en": "Internet/TV/Phone", "icon": "📱", "keywords": ["בזק", "הוט", "פרטנר", "סלקום", "גולן"]},
    "תחבורה": {"name": "תחבורה", "name_en": "Transportation", "icon": "🚌", "keywords": ["רכבת ישראל", "אגד", "דן", "מטרופולין"]},
    "קניות": {"name": "קניות", "name_en": "Shopping", "icon": "🛍️", "keywords": ["איקאה", "זארה", "H&M", "קניון", "ביג", "עזריאלי", "סוהו"]},
    "בילויים": {"name": "בילויים", "name_en": "Entertainment", "icon": "🎬", "keywords": ["סינמה", "קולנוע", "הופעה", "תיאטרון", "באולינג", "OUTSIDER"]},
    "משקאות": {"name": "משקאות", "name_en": "Beverages", "icon": "🍷", "keywords": ["משקאות", "החן שב", "שיבולת הארץ", "יין", "בירה", "אקספרס"]},
    "מזומן": {"name": "מזומן", "name_en": "Cash", "icon": "💵", "keywords": ["כספומט", "משיכה", "ATM", "מזומן", "שיק"]},
    "הכנסה": {"name": "הכנסה", "name_en": "Income", "icon": "💰", "keywords": ["משכורת", "קצבת ילדים", "החזר", "זיכוי", "מילואים", "מופ\"ת"]},
    "העברות_כא": {"name": "העברות כ.א", "name_en": "CC Transfers", "icon": "💳", "keywords": ["ישראכרט", "מקס איט", "כאל", "לאומי קארד"]},
    "פיצוציות": {"name": "פיצוציות", "name_en": "Misc", "icon": "🔹", "keywords": ["נאייקס", "מינימרקט", "קיוסק"]},
    "חד_פעמי": {"name": "חד פעמי", "name_en": "One-time", "icon": "⭐", "keywords": []},
    "אחר": {"name": "אחר", "name_en": "Other", "icon": "❓", "keywords": []},
}

CARD_OWNERS = ["Assaf", "Tehila"]

# =============================================================================
# Session State Initialization
# =============================================================================
if 'transactions' not in st.session_state:
    st.session_state.transactions = pd.DataFrame()
if 'overrides' not in st.session_state:
    st.session_state.overrides = {}
if 'use_demo_data' not in st.session_state:
    st.session_state.use_demo_data = False
if 'gsheet_connected' not in st.session_state:
    st.session_state.gsheet_connected = False

# =============================================================================
# Helper Functions
# =============================================================================

def categorize(description: str, overrides: dict) -> str:
    """Categorize a transaction based on description."""
    if pd.isna(description):
        return "אחר"
    desc_lower = str(description).lower()

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
    if pd.isna(description):
        return False
    cc_keywords = ["ישראכרט", "מקס איט", "כאל", "לאומי קארד"]
    desc_lower = str(description).lower()
    return any(kw.lower() in desc_lower for kw in cc_keywords)


def detect_month(df: pd.DataFrame) -> str:
    """Auto-detect month from transaction dates."""
    if 'date' not in df.columns or df.empty:
        return datetime.now().strftime("%Y-%m")

    dates = pd.to_datetime(df['date'], errors='coerce')
    valid_dates = dates.dropna()
    if valid_dates.empty:
        return datetime.now().strftime("%Y-%m")

    # Get most common month
    months = valid_dates.dt.to_period('M')
    most_common = months.mode()
    if len(most_common) > 0:
        return str(most_common[0])
    return datetime.now().strftime("%Y-%m")


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

        try:
            if isinstance(date_val, str):
                date_val = pd.to_datetime(date_val)
            description = str(description) if pd.notna(description) else ""

            if pd.notna(debit) and float(debit) > 0:
                transactions.append({
                    'date': date_val,
                    'description': description,
                    'amount': -float(debit),
                    'source': 'bank',
                    'card_owner': 'Assaf',
                    'is_one_time': False
                })

            if pd.notna(credit) and float(credit) > 0:
                transactions.append({
                    'date': date_val,
                    'description': description,
                    'amount': float(credit),
                    'source': 'bank',
                    'card_owner': 'Assaf',
                    'is_one_time': False
                })
        except:
            continue

    return pd.DataFrame(transactions)


def parse_credit_card_statement(df: pd.DataFrame, card_owner: str = "Assaf") -> pd.DataFrame:
    """Parse credit card statement Excel file."""
    transactions = []
    in_section = False

    for idx, row in df.iterrows():
        row_str = ' '.join([str(v) for v in row.values if pd.notna(v)])

        if 'תאריך רכישה' in row_str and 'שם בית עסק' in row_str:
            in_section = True
            continue

        if in_section:
            date_val = row.iloc[0] if len(row) > 0 else None
            business = row.iloc[1] if len(row) > 1 else None
            amount = row.iloc[4] if len(row) > 4 else row.iloc[2] if len(row) > 2 else None

            if pd.isna(date_val) or 'סה"כ' in str(date_val):
                continue

            try:
                if isinstance(date_val, str):
                    try:
                        date_val = pd.to_datetime(date_val, format='%d.%m.%y')
                    except:
                        date_val = pd.to_datetime(date_val)

                if pd.isna(business) or str(business).strip() in ['', 'טרם נקלט']:
                    continue

                if pd.notna(amount):
                    amount_val = float(str(amount).replace(',', '').replace('₪', ''))
                    transactions.append({
                        'date': date_val,
                        'description': str(business),
                        'amount': -abs(amount_val),
                        'source': 'credit_card',
                        'card_owner': card_owner,
                        'is_one_time': False
                    })
            except:
                pass

    return pd.DataFrame(transactions)


def get_category_display(cat_key: str) -> str:
    """Get display name with icon for category."""
    cat = CATEGORIES.get(cat_key, {"name": cat_key, "icon": "❓"})
    return f"{cat.get('icon', '')} {cat.get('name', cat_key)}"


# =============================================================================
# Google Sheets Functions
# =============================================================================

def check_gsheets_connection():
    """Check if Google Sheets is configured and accessible."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        # Try to read - this will fail if not configured
        df = conn.read(worksheet="Transactions", ttl=5)
        return True, "Connected"
    except Exception as e:
        error_msg = str(e)
        if "secrets" in error_msg.lower():
            return False, "Not configured"
        return False, f"Error: {error_msg[:50]}"


def load_from_gsheets():
    """Load data from Google Sheets."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df = conn.read(worksheet="Transactions", ttl=60)
        if df is not None and not df.empty:
            # Handle column types
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'], errors='coerce')
            if 'is_one_time' in df.columns:
                df['is_one_time'] = df['is_one_time'].fillna(False).astype(bool)
            if 'is_cc_transfer' in df.columns:
                df['is_cc_transfer'] = df['is_cc_transfer'].fillna(False).astype(bool)
            return df, None
        return pd.DataFrame(), None
    except Exception as e:
        return pd.DataFrame(), str(e)


def save_to_gsheets(df: pd.DataFrame):
    """Save data to Google Sheets."""
    try:
        conn = st.connection("gsheets", type=GSheetsConnection)
        df_to_save = df.copy()
        # Convert date to string for storage
        if 'date' in df_to_save.columns:
            df_to_save['date'] = df_to_save['date'].astype(str)
        conn.update(worksheet="Transactions", data=df_to_save)
        return True, None
    except Exception as e:
        return False, str(e)


# Try to load from Google Sheets on startup
if 'gsheets_checked' not in st.session_state:
    st.session_state.gsheets_checked = False
    st.session_state.gsheets_connected = False
    st.session_state.gsheets_error = None

if not st.session_state.gsheets_checked:
    connected, msg = check_gsheets_connection()
    st.session_state.gsheets_connected = connected
    st.session_state.gsheets_error = None if connected else msg
    st.session_state.gsheets_checked = True

    # If connected and no local data, try to load from sheets
    if connected and st.session_state.transactions.empty:
        loaded_df, error = load_from_gsheets()
        if not loaded_df.empty:
            st.session_state.transactions = loaded_df


# =============================================================================
# Main UI
# =============================================================================

# Header
st.markdown("""
<div style='text-align: center; padding: 20px;'>
    <h1 style='font-size: 3rem; margin-bottom: 0;'>💰 Finance Monitor</h1>
    <p style='color: #888; font-size: 1.2rem;'>ניטור פיננסי אישי למשפחה</p>
</div>
""", unsafe_allow_html=True)

# =============================================================================
# Sidebar
# =============================================================================

with st.sidebar:
    st.markdown("## 📁 Upload Files")

    # Bank statement
    bank_file = st.file_uploader(
        "🏦 Bank Statement",
        type=['xlsx', 'xls'],
        help="תנועות בחשבון עו״ש"
    )

    # Credit card files with owner selection
    st.markdown("### 💳 Credit Cards")

    cc_files = st.file_uploader(
        "Credit Card Statements",
        type=['xlsx', 'xls'],
        accept_multiple_files=True,
        help="Upload one or more credit card statements"
    )

    # Owner selection for each file
    cc_owners = {}
    if cc_files:
        st.markdown("**Assign card owners:**")
        for i, f in enumerate(cc_files):
            cc_owners[f.name] = st.selectbox(
                f"{f.name[:20]}...",
                CARD_OWNERS,
                key=f"owner_{i}"
            )

    # Process button
    if st.button("🚀 Process Files", type="primary", use_container_width=True):
        all_transactions = []

        if bank_file:
            with st.spinner("Processing bank..."):
                bank_df = pd.read_excel(bank_file)
                bank_trans = parse_bank_statement(bank_df)
                if not bank_trans.empty:
                    all_transactions.append(bank_trans)
                    st.success(f"✓ Bank: {len(bank_trans)} transactions")

        for cc_file in cc_files:
            with st.spinner(f"Processing {cc_file.name}..."):
                cc_df = pd.read_excel(cc_file)
                owner = cc_owners.get(cc_file.name, "Assaf")
                cc_trans = parse_credit_card_statement(cc_df, owner)
                if not cc_trans.empty:
                    all_transactions.append(cc_trans)
                    st.success(f"✓ {owner}'s card: {len(cc_trans)} transactions")

        if all_transactions:
            new_df = pd.concat(all_transactions, ignore_index=True)

            # Categorize
            new_df['category'] = new_df['description'].apply(
                lambda x: categorize(x, st.session_state.overrides)
            )
            new_df['is_cc_transfer'] = new_df.apply(
                lambda x: x['source'] == 'bank' and is_cc_transfer(x['description']),
                axis=1
            )

            # Detect month
            month = detect_month(new_df)
            new_df['month'] = month

            # Merge with existing data
            if not st.session_state.transactions.empty:
                st.session_state.transactions = pd.concat(
                    [st.session_state.transactions, new_df],
                    ignore_index=True
                ).drop_duplicates(subset=['date', 'description', 'amount'])
            else:
                st.session_state.transactions = new_df

            st.success(f"✅ Loaded {len(new_df)} transactions for {month}")

    st.markdown("---")

    # Google Sheets connection status and controls
    st.markdown("### ☁️ Cloud Storage")

    if st.session_state.gsheets_connected:
        st.success("✅ Google Sheets connected!")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save", use_container_width=True):
                if not st.session_state.transactions.empty:
                    success, error = save_to_gsheets(st.session_state.transactions)
                    if success:
                        st.success("Saved!")
                    else:
                        st.error(f"Save failed: {error}")
                else:
                    st.warning("No data to save")

        with col2:
            if st.button("📥 Load", use_container_width=True):
                loaded_df, error = load_from_gsheets()
                if not loaded_df.empty:
                    st.session_state.transactions = loaded_df
                    st.success(f"Loaded {len(loaded_df)} transactions!")
                    st.rerun()
                elif error:
                    st.error(f"Load failed: {error}")
                else:
                    st.info("No data in Google Sheets yet")
    else:
        st.warning(f"⚠️ {st.session_state.gsheets_error or 'Not connected'}")
        st.caption("Check Streamlit secrets configuration")

# =============================================================================
# Main Content
# =============================================================================

if st.session_state.transactions.empty:
    # Welcome screen
    st.markdown("""
    <div style='text-align: center; padding: 50px; background: rgba(15, 52, 96, 0.5); border-radius: 20px; margin: 20px;'>
        <h2>👋 Welcome!</h2>
        <p style='font-size: 1.2rem; color: #888;'>Upload your bank and credit card files to get started.</p>
        <br>
        <div style='display: flex; justify-content: center; gap: 30px; flex-wrap: wrap;'>
            <div style='text-align: center;'>
                <span style='font-size: 3rem;'>📊</span>
                <p>Track Spending</p>
            </div>
            <div style='text-align: center;'>
                <span style='font-size: 3rem;'>📈</span>
                <p>See Trends</p>
            </div>
            <div style='text-align: center;'>
                <span style='font-size: 3rem;'>💳</span>
                <p>Multiple Cards</p>
            </div>
            <div style='text-align: center;'>
                <span style='font-size: 3rem;'>⚙️</span>
                <p>Customize</p>
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

else:
    df = st.session_state.transactions.copy()

    # Month selector
    available_months = sorted(df['month'].unique(), reverse=True)

    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        selected_month = st.selectbox(
            "📅 Select Month",
            available_months,
            index=0
        )
    with col2:
        show_all_months = st.checkbox("Show all months", value=False)
    with col3:
        include_one_time = st.checkbox("Include one-time", value=False)

    # Filter data
    if show_all_months:
        df_filtered = df.copy()
    else:
        df_filtered = df[df['month'] == selected_month].copy()

    # Exclude CC transfers and optionally one-time expenses
    has_both = len(df_filtered['source'].unique()) > 1
    df_display = df_filtered[~df_filtered['is_cc_transfer']].copy()

    if not include_one_time:
        df_regular = df_display[~df_display['is_one_time']]
        df_one_time = df_display[df_display['is_one_time']]
    else:
        df_regular = df_display
        df_one_time = pd.DataFrame()

    # =============================================================================
    # Summary Cards
    # =============================================================================

    income = df_regular[df_regular['amount'] > 0]['amount'].sum()
    expenses = abs(df_regular[df_regular['amount'] < 0]['amount'].sum())
    balance = income - expenses

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            "💵 Income",
            f"₪{income:,.0f}",
            help="Total income"
        )

    with col2:
        st.metric(
            "💸 Expenses",
            f"₪{expenses:,.0f}",
            help="Total expenses (excluding one-time)"
        )

    with col3:
        delta_color = "normal" if balance >= 0 else "inverse"
        st.metric(
            "📊 Balance",
            f"₪{balance:,.0f}",
            delta=f"₪{balance:,.0f}",
            delta_color=delta_color
        )

    with col4:
        one_time_total = abs(df_one_time[df_one_time['amount'] < 0]['amount'].sum()) if not df_one_time.empty else 0
        st.metric(
            "⭐ One-time",
            f"₪{one_time_total:,.0f}",
            help="Excluded special expenses"
        )

    st.markdown("---")

    # =============================================================================
    # Tabs
    # =============================================================================

    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 Categories",
        "📈 Trends",
        "📋 Transactions",
        "⭐ One-time",
        "⚙️ Settings"
    ])

    # -------------------------------------------------------------------------
    # Tab 1: Categories
    # -------------------------------------------------------------------------
    with tab1:
        expense_df = df_regular[df_regular['amount'] < 0].copy()
        expense_df['amount'] = expense_df['amount'].abs()

        if not expense_df.empty:
            category_totals = expense_df.groupby('category')['amount'].sum().sort_values(ascending=True)

            # Pie chart
            col1, col2 = st.columns([1, 1])

            with col1:
                fig = px.pie(
                    values=category_totals.values,
                    names=[get_category_display(c) for c in category_totals.index],
                    title="Spending by Category",
                    hole=0.4,
                    color_discrete_sequence=px.colors.qualitative.Set3
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)

            with col2:
                fig = px.bar(
                    x=category_totals.values,
                    y=[get_category_display(c) for c in category_totals.index],
                    orientation='h',
                    title="Spending Breakdown",
                    color=category_totals.values,
                    color_continuous_scale='Reds'
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white',
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)

            # Summary table
            st.markdown("### 📋 Category Summary")
            summary_data = []
            for cat in category_totals.index[::-1]:
                amount = category_totals[cat]
                pct = (amount / expenses * 100) if expenses > 0 else 0
                cat_info = CATEGORIES.get(cat, {"icon": "❓", "name": cat, "name_en": ""})
                summary_data.append({
                    "": cat_info.get("icon", "❓"),
                    "קטגוריה": cat_info.get("name", cat),
                    "Category": cat_info.get("name_en", ""),
                    "Amount": f"₪{amount:,.0f}",
                    "Percent": f"{pct:.1f}%"
                })

            st.dataframe(
                pd.DataFrame(summary_data),
                use_container_width=True,
                hide_index=True
            )

    # -------------------------------------------------------------------------
    # Tab 2: Trends
    # -------------------------------------------------------------------------
    with tab2:
        if len(available_months) > 1:
            # Monthly totals
            monthly_data = df[~df['is_cc_transfer'] & ~df['is_one_time']].copy()
            monthly_summary = monthly_data.groupby('month').agg({
                'amount': lambda x: (x[x > 0].sum(), abs(x[x < 0].sum()))
            }).reset_index()

            monthly_summary['income'] = monthly_summary['amount'].apply(lambda x: x[0])
            monthly_summary['expenses'] = monthly_summary['amount'].apply(lambda x: x[1])
            monthly_summary['balance'] = monthly_summary['income'] - monthly_summary['expenses']

            # Trend chart
            fig = go.Figure()
            fig.add_trace(go.Bar(name='Income', x=monthly_summary['month'], y=monthly_summary['income'], marker_color='#00d9ff'))
            fig.add_trace(go.Bar(name='Expenses', x=monthly_summary['month'], y=monthly_summary['expenses'], marker_color='#e94560'))
            fig.add_trace(go.Scatter(name='Balance', x=monthly_summary['month'], y=monthly_summary['balance'], mode='lines+markers', line=dict(color='#ffd700', width=3)))

            fig.update_layout(
                title="Monthly Trend",
                barmode='group',
                paper_bgcolor='rgba(0,0,0,0)',
                plot_bgcolor='rgba(0,0,0,0)',
                font_color='white'
            )
            st.plotly_chart(fig, use_container_width=True)

            # Category trends
            st.markdown("### Category Trends Over Time")
            cat_monthly = monthly_data[monthly_data['amount'] < 0].groupby(['month', 'category'])['amount'].sum().abs().reset_index()

            if not cat_monthly.empty:
                fig = px.line(
                    cat_monthly,
                    x='month',
                    y='amount',
                    color='category',
                    title="Spending by Category Over Time"
                )
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    font_color='white'
                )
                st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📊 Upload more months to see trends!")

    # -------------------------------------------------------------------------
    # Tab 3: Transactions
    # -------------------------------------------------------------------------
    with tab3:
        st.markdown("### All Transactions")

        # Filters
        col1, col2, col3 = st.columns(3)
        with col1:
            cat_filter = st.selectbox("Category", ["All"] + list(df_display['category'].unique()))
        with col2:
            owner_filter = st.selectbox("Card Owner", ["All"] + CARD_OWNERS)
        with col3:
            source_filter = st.selectbox("Source", ["All", "bank", "credit_card"])

        # Apply filters
        display_df = df_display.copy()
        if cat_filter != "All":
            display_df = display_df[display_df['category'] == cat_filter]
        if owner_filter != "All":
            display_df = display_df[display_df['card_owner'] == owner_filter]
        if source_filter != "All":
            display_df = display_df[display_df['source'] == source_filter]

        display_df = display_df.sort_values('date', ascending=False)

        # Editable table
        st.markdown("**Click on a row to edit category or mark as one-time:**")

        for idx, row in display_df.head(50).iterrows():
            col1, col2, col3, col4, col5 = st.columns([1, 3, 1.5, 1.5, 1])

            with col1:
                st.text(row['date'].strftime('%d/%m') if pd.notna(row['date']) else '')
            with col2:
                st.text(row['description'][:35] if len(str(row['description'])) > 35 else row['description'])
            with col3:
                st.text(f"₪{row['amount']:,.0f}")
            with col4:
                new_cat = st.selectbox(
                    "Cat",
                    list(CATEGORIES.keys()),
                    index=list(CATEGORIES.keys()).index(row['category']) if row['category'] in CATEGORIES else 0,
                    key=f"cat_{idx}",
                    label_visibility="collapsed"
                )
                if new_cat != row['category']:
                    st.session_state.transactions.loc[idx, 'category'] = new_cat
            with col5:
                is_onetime = st.checkbox(
                    "⭐",
                    value=row['is_one_time'],
                    key=f"onetime_{idx}",
                    help="Mark as one-time expense"
                )
                if is_onetime != row['is_one_time']:
                    st.session_state.transactions.loc[idx, 'is_one_time'] = is_onetime

    # -------------------------------------------------------------------------
    # Tab 4: One-time Expenses
    # -------------------------------------------------------------------------
    with tab4:
        st.markdown("### ⭐ One-time / Special Expenses")
        st.markdown("These are excluded from monthly averages but tracked separately.")

        all_one_time = df[df['is_one_time'] == True].copy()

        if not all_one_time.empty:
            total_one_time = abs(all_one_time[all_one_time['amount'] < 0]['amount'].sum())
            st.metric("Total One-time Expenses (All Time)", f"₪{total_one_time:,.0f}")

            st.dataframe(
                all_one_time[['date', 'description', 'amount', 'category', 'card_owner']].sort_values('date', ascending=False),
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No one-time expenses marked yet. Go to Transactions tab and click ⭐ to mark items.")

    # -------------------------------------------------------------------------
    # Tab 5: Settings
    # -------------------------------------------------------------------------
    with tab5:
        st.markdown("### ⚙️ Category Overrides")
        st.markdown("Add rules to auto-categorize transactions.")

        col1, col2 = st.columns(2)
        with col1:
            pattern = st.text_input("Description pattern", placeholder="e.g., תמר זמיר")
        with col2:
            category = st.selectbox("Assign to category", list(CATEGORIES.keys()))

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
                    st.text(get_category_display(cat))
                with col3:
                    if st.button("🗑️", key=f"del_{pattern}"):
                        del st.session_state.overrides[pattern]
                        st.rerun()

        st.markdown("---")
        st.markdown("### 🗑️ Data Management")

        if st.button("Clear All Data", type="secondary"):
            st.session_state.transactions = pd.DataFrame()
            st.session_state.overrides = {}
            st.rerun()
