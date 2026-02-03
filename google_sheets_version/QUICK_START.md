# Google Sheets Finance Tool - Quick Start

## Step 1: Open the Template
I'll create a ready-to-use template. You just need to:
1. Open the link (I'll provide below)
2. Click "File" → "Make a copy"
3. Start using!

## Step 2: Paste Your Data

### Bank Statement:
1. Open your bank Excel file (תנועות בחשבון עו״ש)
2. Go to the "Transactions" sheet
3. Paste:
   - Column A (תאריך) → into Date column
   - Column D (תיאור פעולה) → into Description column
   - Column E (חובה) → into Amount column (expenses as negative)
4. Type "bank" in the Source column

### Credit Card:
1. Open your credit card Excel file
2. Paste:
   - Column A (תאריך רכישה) → into Date column
   - Column B (שם בית עסק) → into Description column
   - Column E (סכום חיוב) → into Amount column (as negative)
3. Type "credit_card" in the Source column

## Step 3: View Your Dashboard
- Go to the "Dashboard" sheet
- Select the month
- See your spending breakdown!

## Step 4: Fix Categorizations
- If something is in "אחר" (Other) and shouldn't be:
- Go to "Overrides" sheet
- Add the business name and correct category

---

## That's it!

The formulas will automatically:
- Categorize each transaction
- Calculate totals by category
- Exclude credit card transfers from bank (no double-counting)
- Show your spending breakdown
