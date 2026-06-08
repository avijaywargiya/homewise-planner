# HomeWise Planner

**Make smarter buy, rent, refinance, and mortgage prepayment decisions.**

A lightweight local Streamlit web application that helps families evaluate major housing decisions without needing any paid APIs, logins, or external services. All calculations run locally in Python.

---

## What the App Does

HomeWise Planner walks you through six decision-oriented modules:

| Tab | Question Answered |
|-----|-------------------|
| **Buy Affordability** | How much house can I safely afford? |
| **Rent vs Buy** | Is buying financially better than renting over my time horizon? |
| **Mortgage Scenarios** | How does my monthly payment change under different loan assumptions? |
| **Refi Check** | Would refinancing make sense if rates fall? |
| **Prepay vs Invest** | Should extra cash go toward mortgage principal or investments? |
| **Summary Report** | Overall HomeWise Score (0–100) with exportable report |

---

## Installation

### Prerequisites

- Python 3.9 or newer
- pip

### Steps

```bash
# 1. Clone or download this project
cd HomeWisePlanner

# 2. (Recommended) Create a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app.py
```

The app will open at `http://localhost:8501` in your browser.

---

## How to Use

1. **Fill in the sidebar** with your household income, savings, expenses, and planning assumptions. These feed all modules.
2. **Visit each tab** in order — earlier tabs pre-populate inputs for later ones.
3. **Review the Summary Report** tab for your HomeWise Score and a combined view.
4. **Download** a CSV or Markdown report from the Summary tab.

---

## Module Descriptions

### Profile & Assumptions (Sidebar + Tab 1)
Enter household income, savings, monthly expenses, debt payments, and planning assumptions (investment return, inflation, tax rate, time horizon). All other modules use these as defaults.

### Buy Affordability (Tab 2)
Calculates monthly payment breakdown, upfront cash required, remaining savings, emergency fund coverage, housing-to-income ratio, and debt-to-income ratio. Returns a **Comfortable / Stretched / Risky** status.

### Rent vs Buy (Tab 3)
Compares the net wealth outcome of buying versus continuing to rent and investing the difference. Shows a breakeven year and a plain-English recommendation.

### Mortgage Scenarios (Tab 4)
Side-by-side comparison of up to 3 mortgage scenarios (e.g., 30-year vs 15-year, more down payment). Includes bar charts for monthly payment, total interest, and upfront cash.

### Refi Check (Tab 5)
Models a hypothetical refinance: new payment, monthly savings, breakeven months, and total savings over expected stay. Returns **Likely Worth Considering / Not Clearly Worth It / Unfavorable**.

### Prepay vs Invest (Tab 6)
Compares putting extra monthly cash toward mortgage principal versus investing it. Accounts for after-tax investment returns and notes the certainty difference between prepaying (guaranteed return = mortgage rate) and investing (higher potential, more risk).

### Summary Report (Tab 7)
Aggregates all module outputs into a single view with the **HomeWise Score (0–100)**. Provides CSV and Markdown download buttons.

---

## HomeWise Score

| Score | Band |
|-------|------|
| 80–100 | Strong / Comfortable |
| 60–79 | Manageable — watch carefully |
| 40–59 | Stretched |
| < 40 | High Risk |

Points are deducted for high housing-to-income ratio, high DTI, low emergency fund after purchase, negative cash flow, buying significantly underperforming renting, payment shock vs current rent, and heavy upfront cash usage.

---

## File Structure

```
HomeWisePlanner/
├── app.py                   # Main Streamlit application
├── requirements.txt         # Python dependencies
├── README.md
└── utils/
    ├── __init__.py
    └── calculations.py      # All financial calculation functions
```

---

## Deploying to Streamlit Community Cloud

1. Push this project to a public GitHub repository.
2. Go to [share.streamlit.io](https://share.streamlit.io) and connect your GitHub account.
3. Select the repository and set the main file to `app.py`.
4. Click **Deploy**. No additional configuration needed.

---

## Disclaimer

> **This tool is for educational planning purposes only and does not constitute financial, mortgage, tax, or investment advice.** Always consult qualified professionals before making major financial decisions.

---

## Future Enhancement Ideas

- Save/load assumptions as JSON for multiple scenarios
- Compare multiple saved housing plans side by side
- PMI (private mortgage insurance) calculation when down payment < 20%
- Amortization schedule export (full month-by-month table)
- Property tax lookup by state/county
- Affordability rules by lender type (conventional, FHA, jumbo)
- AI-generated narrative summary
- Integration with a broader family financial roadmap tool
- Streamlit Community Cloud deployment guide with custom domain
