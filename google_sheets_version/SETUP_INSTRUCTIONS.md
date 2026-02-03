# Finance Monitoring Tool - Google Sheets Version

## Quick Setup (5 minutes)

### Step 1: Create a New Google Sheet
1. Go to [sheets.google.com](https://sheets.google.com)
2. Click "+ Blank" to create a new spreadsheet
3. Name it "Finance Monitor"

### Step 2: Create These Sheets (tabs)
Create 4 sheets by clicking the "+" at the bottom:
1. **Dashboard** - Your summary view
2. **Transactions** - All your transaction data
3. **Categories** - Category definitions with keywords
4. **Overrides** - Manual categorization fixes

---

## Sheet 1: Categories

Copy this data into the "Categories" sheet:

| A (Category Key) | B (Hebrew Name) | C (English Name) | D (Keywords - comma separated) |
|------------------|-----------------|------------------|-------------------------------|
| גן_עוז | גן עוז | Daycare | גן עוז,גן ילדים,צהרון |
| משכנתא | משכנתא | Mortgage | משכנתא,פועלים-משכנתא |
| ועד_בית | ועד בית | HOA Fees | ועד בית,עזרא הסופר |
| ארנונה | ארנונה | Property Tax | ארנונה,עירייה,עיריית |
| ביטוחים | ביטוחים | Insurance | הראל,מגדל,כלל,ביטוח,פניקס,מנורה,קרן מכבי |
| חשמל | חשמל | Electricity | חברת חשמל,חשמל |
| מים | מים | Water | מי ,מים,מקורות |
| סופרמרקט | סופרמרקט | Supermarket | רמי לוי,שופרסל,יוחננוף,מגה,ויקטורי,סופר,המרכולית,קטיף עצמי,אושר עד |
| מסעדות | מסעדות ואוכל בחוץ | Restaurants | מסעדה,קפה,פיצה,מקדונלד,בורגר,שווארמה,לחמנינה,ארקפה,מוניציפל,נונומימי |
| רכב_ודלק | רכב ודלק | Car & Fuel | דלק,סונול,פז,דור אלון,yellow,רכב,מנטה,ten |
| ילדים | ילדים | Kids | צעצוע,toys,ילדים,בייבי,תמר זמיר |
| עוז | עוז | Oz (Son) | עוז |
| ספורט | ספורט | Sports | ספורט,כושר,gym,חדר כושר,יוגה,שחייה,בריכה |
| פארמה | פארמה | Pharmacy | סופר פארם,פארם,בית מרקחת,תרופ |
| תרומה | תרומה | Donations | תרומה,צדקה,עמותה,מפלגת המילואימניקים |
| תוכנות | תוכנות | Software | GOOGLE,APPLE,NETFLIX,SPOTIFY,AMAZON,MICROSOFT,CLAUDE |
| אטט | א.ט.ט | Internet/TV/Phone | בזק,הוט,פרטנר,סלקום,גולן,אינטרנט,טלפון |
| תחבורה | תחבורה | Transportation | רכבת ישראל,אגד,דן,מטרופולין,רב קו |
| קניות | קניות | Shopping | איקאה,זארה,H&M,קניון,ביג,עזריאלי,סוהו |
| בילויים | בילויים | Entertainment | סינמה,קולנוע,הופעה,תיאטרון,באולינג,OUTSIDER |
| משקאות | משקאות | Beverages | משקאות,החן שב,שיבולת הארץ,יין,בירה,אקספרס |
| מזומן | מזומן | Cash | כספומט,משיכה,ATM,מזומן,שיק |
| הכנסה | הכנסה | Income | משכורת,קצבת ילדים,החזר,זיכוי,מילואים,מופ"ת |
| העברות_כא | העברות כרטיס אשראי | CC Transfers | ישראכרט,מקס איט,כאל,לאומי קארד |
| פיצוציות | פיצוציות | Misc Small | נאייקס,מינימרקט,קיוסק |
| אחר | אחר | Other | |

---

## Sheet 2: Overrides

Set up the "Overrides" sheet with these columns:

| A (Description) | B (Category Key) |
|-----------------|------------------|
| תמר זמיר | ילדים |
| מפלגת המילואימניקים | תרומה |

Add rows here when you want to manually fix a categorization.

---

## Sheet 3: Transactions

Set up columns:

| A | B | C | D | E | F |
|---|---|---|---|---|---|
| Date | Description | Amount | Source | Category | Is CC Transfer |
| תאריך | תיאור | סכום | מקור | קטגוריה | העברת כ.א |

### How to Paste Data:

**From Bank Statement (תנועות בחשבון עו״ש):**
1. Open your bank Excel file
2. Copy the date column (A) → Paste into column A
3. Copy the description column (D) → Paste into column B
4. Copy the expense column (E) → Paste into column C (as negative numbers)
5. Type "bank" in column D for all rows

**From Credit Card Statement:**
1. Open your credit card Excel file
2. Copy the date column (A) → Paste into column A
3. Copy the business name column (B) → Paste into column B
4. Copy the charge amount column (E) → Paste into column C (as negative numbers)
5. Type "credit_card" in column D for all rows

### Formulas for Auto-Categorization:

In cell **E2** (Category), paste this formula and drag down:
```
=IFERROR(
  VLOOKUP(B2,Overrides!A:B,2,FALSE),
  IFERROR(
    INDEX(Categories!A:A,
      MATCH(TRUE,
        ARRAYFORMULA(REGEXMATCH(LOWER(B2),LOWER(Categories!D:D))),
        0
      )
    ),
    "אחר"
  )
)
```

In cell **F2** (Is CC Transfer), paste this formula and drag down:
```
=IF(AND(D2="bank",REGEXMATCH(LOWER(B2),"ישראכרט|מקס איט|כאל|לאומי קארד")),"כן","לא")
```

---

## Sheet 4: Dashboard

### Summary Section (Row 1-10)

In **A1**: `סיכום חודשי / Monthly Summary`

In **A3**: `חודש / Month:`
In **B3**: Create a dropdown with months (Data → Data Validation → List: 2026-01, 2026-02, etc.)

In **A5**: `הכנסות / Income:`
In **B5**:
```
=SUMIFS(Transactions!C:C,Transactions!C:C,">0",TEXT(Transactions!A:A,"YYYY-MM"),$B$3)
```

In **A6**: `הוצאות / Expenses:`
In **B6**:
```
=ABS(SUMIFS(Transactions!C:C,Transactions!C:C,"<0",TEXT(Transactions!A:A,"YYYY-MM"),$B$3,Transactions!F:F,"לא"))
```

In **A7**: `מאזן / Balance:`
In **B7**: `=B5-B6`

In **A8**: `העברות כ.א שהוחרגו / Excluded CC Transfers:`
In **B8**:
```
=ABS(SUMIFS(Transactions!C:C,TEXT(Transactions!A:A,"YYYY-MM"),$B$3,Transactions!F:F,"כן"))
```

### Category Breakdown (Starting Row 12)

In **A12**: `קטגוריה`
In **B12**: `סכום`
In **C12**: `אחוז`

In **A13**, create a list of categories, then in **B13**:
```
=ABS(SUMIFS(Transactions!C:C,Transactions!E:E,A13,Transactions!C:C,"<0",TEXT(Transactions!A:A,"YYYY-MM"),$B$3,Transactions!F:F,"לא"))
```

In **C13**:
```
=IF($B$6>0,B13/$B$6,0)
```

Format column C as percentage.

---

## How to Use Monthly

1. Download your bank statement Excel file
2. Download your credit card statement Excel file
3. Copy/paste the relevant columns into the Transactions sheet
4. Check the Dashboard for your summary
5. Look at "אחר" category - add overrides for any miscategorized items
6. Refresh and review!

---

## Tips

- **To fix a categorization:** Add the business name and correct category to the Overrides sheet
- **To add a new category:** Add a row to the Categories sheet
- **To see uncategorized:** Filter Transactions by Category = "אחר"
