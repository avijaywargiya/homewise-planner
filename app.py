"""
HomeWise Planner
Make smarter buy, rent, refinance, and mortgage prepayment decisions.
"""

import io
import csv
import streamlit as st
import pandas as pd

from utils.calculations import (
    calculate_monthly_mortgage_payment,
    calculate_affordability_metrics,
    calculate_rent_vs_buy,
    calculate_refi_breakeven,
    calculate_prepay_vs_invest,
    calculate_homewise_score,
    calculate_total_interest,
    calculate_remaining_balance,
    calculate_future_value,
)

# ---------------------------------------------------------------------------
# Page config
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="HomeWise Planner",
    page_icon="🏠",
    layout="wide",
    initial_sidebar_state="expanded",
)

DISCLAIMER = (
    "> **Disclaimer:** This tool is for illustration purposes only and does not constitute "
    "financial, mortgage, tax, or investment advice."
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_dollar(v: float) -> str:
    return f"${v:,.0f}"


def fmt_pct(v: float) -> str:
    return f"{v:.1f}%"


def status_badge(status: str) -> str:
    colors = {"Comfortable": "🟢", "Stretched": "🟡", "Risky": "🔴"}
    return f"{colors.get(status, '')} {status}"


def section_header(title: str, subtitle: str = ""):
    st.markdown(f"## {title}")
    if subtitle:
        st.markdown(f"*{subtitle}*")
    st.markdown("---")


# ---------------------------------------------------------------------------
# Sidebar — Profile & Assumptions
# ---------------------------------------------------------------------------

def sidebar_inputs() -> dict:
    st.sidebar.title("🏠 HomeWise Planner")
    st.sidebar.markdown("*Make smarter housing decisions.*")
    st.sidebar.markdown("---")
    st.sidebar.markdown("### Household Profile")

    age = st.sidebar.number_input("Your current age", 18, 80, 35, 1)
    gross_income = st.sidebar.number_input("Annual gross household income ($)", 0, 2_000_000, 120_000, 1_000)
    after_tax_income = st.sidebar.number_input(
        "Annual after-tax income ($) — optional, 0 to estimate",
        0, 2_000_000, 0, 1_000,
        help="Leave at 0 and we'll estimate using your tax rate below.",
    )
    monthly_expenses = st.sidebar.number_input("Monthly non-housing expenses ($)", 0, 50_000, 3_500, 100)
    current_rent = st.sidebar.number_input("Current monthly rent ($)", 0, 20_000, 2_200, 50)
    monthly_debt = st.sidebar.number_input("Existing monthly debt payments ($)", 0, 10_000, 400, 50,
                                            help="Car loans, student loans, credit cards, etc. (exclude housing).")
    liquid_savings = st.sidebar.number_input("Current liquid savings ($)", 0, 5_000_000, 80_000, 1_000)
    emergency_months = st.sidebar.number_input("Emergency fund target (months of expenses)", 1, 24, 6, 1)
    monthly_retirement = st.sidebar.number_input("Monthly retirement contributions ($)", 0, 10_000, 800, 50)
    monthly_other_savings = st.sidebar.number_input("Other monthly savings/investments ($)", 0, 10_000, 300, 50)

    st.sidebar.markdown("---")
    st.sidebar.markdown("### Planning Assumptions")
    income_growth = st.sidebar.slider("Expected annual income growth (%)", 0.0, 10.0, 3.0, 0.1)
    inflation = st.sidebar.slider("Expected annual inflation (%)", 0.0, 10.0, 3.0, 0.1)
    investment_return = st.sidebar.slider("Expected annual investment return (%)", 0.0, 15.0, 7.0, 0.1)
    tax_rate = st.sidebar.slider("Effective federal+state tax rate (%)", 0.0, 50.0, 25.0, 0.5)
    marginal_tax_rate = st.sidebar.slider("Marginal tax rate (for deduction sensitivity)", 0.0, 50.0, 32.0, 0.5)
    horizon_years = st.sidebar.slider("Planning time horizon (years)", 1, 30, 10, 1)

    # Derive after-tax income if not provided
    if after_tax_income == 0:
        after_tax_income = gross_income * (1 - tax_rate / 100)

    gross_monthly = gross_income / 12
    after_tax_monthly = after_tax_income / 12

    return dict(
        age=age,
        gross_income=gross_income,
        after_tax_income=after_tax_income,
        gross_monthly=gross_monthly,
        after_tax_monthly=after_tax_monthly,
        monthly_expenses=monthly_expenses,
        current_rent=current_rent,
        monthly_debt=monthly_debt,
        liquid_savings=liquid_savings,
        emergency_months=emergency_months,
        monthly_retirement=monthly_retirement,
        monthly_other_savings=monthly_other_savings,
        income_growth=income_growth,
        inflation=inflation,
        investment_return=investment_return,
        tax_rate=tax_rate,
        marginal_tax_rate=marginal_tax_rate,
        horizon_years=horizon_years,
    )


# ---------------------------------------------------------------------------
# Tab 1 — Profile summary
# ---------------------------------------------------------------------------

def tab_profile(p: dict):
    section_header("Profile & Assumptions", "Your household and planning inputs")
    st.markdown(DISCLAIMER)
    st.markdown("")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Gross Monthly Income", fmt_dollar(p["gross_monthly"]))
        st.metric("After-Tax Monthly Income", fmt_dollar(p["after_tax_monthly"]))
        st.metric("Current Monthly Rent", fmt_dollar(p["current_rent"]))
    with col2:
        st.metric("Monthly Non-Housing Expenses", fmt_dollar(p["monthly_expenses"]))
        st.metric("Existing Monthly Debt Payments", fmt_dollar(p["monthly_debt"]))
        st.metric("Liquid Savings", fmt_dollar(p["liquid_savings"]))
    with col3:
        st.metric("Monthly Retirement Contributions", fmt_dollar(p["monthly_retirement"]))
        st.metric("Emergency Fund Target", f"{p['emergency_months']} months")
        st.metric("Planning Horizon", f"{p['horizon_years']} years")

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Expected Income Growth", fmt_pct(p["income_growth"]))
    with col2:
        st.metric("Expected Investment Return", fmt_pct(p["investment_return"]))
    with col3:
        st.metric("Effective Tax Rate", fmt_pct(p["tax_rate"]))

    monthly_free = (
        p["after_tax_monthly"]
        - p["current_rent"]
        - p["monthly_debt"]
        - p["monthly_expenses"]
        - p["monthly_retirement"]
        - p["monthly_other_savings"]
    )
    st.markdown("---")
    st.markdown("### Current Monthly Cash Flow (Renting)")
    col1, col2 = st.columns(2)
    with col1:
        rows = {
            "After-tax income": p["after_tax_monthly"],
            "Rent": -p["current_rent"],
            "Debt payments": -p["monthly_debt"],
            "Non-housing expenses": -p["monthly_expenses"],
            "Retirement contributions": -p["monthly_retirement"],
            "Other savings": -p["monthly_other_savings"],
            "**Free cash flow**": monthly_free,
        }
        df = pd.DataFrame({"Amount": rows}).reset_index()
        df.columns = ["Category", "Amount ($)"]
        df["Amount ($)"] = df["Amount ($)"].map(lambda x: f"${x:,.0f}")
        st.dataframe(df, hide_index=True, use_container_width=True)
    with col2:
        color = "green" if monthly_free >= 0 else "red"
        st.metric("Monthly free cash flow (renting)", fmt_dollar(monthly_free))
        if monthly_free < 0:
            st.warning("Your current budget shows negative cash flow. Review your inputs.")


# ---------------------------------------------------------------------------
# Tab 2 — Buy Affordability
# ---------------------------------------------------------------------------

def tab_affordability(p: dict) -> dict | None:
    section_header("Buy Affordability", "How much house can you safely afford?")

    with st.expander("Home Purchase Inputs", expanded=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            home_price = st.number_input("Target home price ($)", 50_000, 5_000_000, 450_000, 5_000, key="aff_price")
            down_payment = st.number_input("Down payment ($)", 0, 5_000_000, 90_000, 1_000, key="aff_dp")
            mortgage_rate = st.number_input("Mortgage interest rate (%)", 0.0, 20.0, 6.75, 0.05, key="aff_rate")
            loan_term = st.selectbox("Loan term (years)", [15, 20, 30], index=2, key="aff_term")
        with col2:
            property_tax_rate = st.number_input("Property tax rate (%)", 0.0, 5.0, 1.1, 0.05, key="aff_ptax")
            annual_insurance = st.number_input("Annual homeowners insurance ($)", 0, 20_000, 1_800, 100, key="aff_ins")
            monthly_hoa = st.number_input("Monthly HOA fee ($)", 0, 5_000, 0, 25, key="aff_hoa")
            maintenance_pct = st.number_input("Annual maintenance (% of home value)", 0.0, 5.0, 1.0, 0.1, key="aff_maint")
        with col3:
            closing_cost_pct = st.number_input("Closing cost (%)", 0.0, 10.0, 2.5, 0.1, key="aff_close")
            moving_cost = st.number_input("Moving/furnishing cost ($)", 0, 100_000, 5_000, 500, key="aff_move")

    if down_payment > home_price:
        st.error("Down payment cannot exceed home price.")
        return None

    m = calculate_affordability_metrics(
        home_price=home_price,
        down_payment=down_payment,
        mortgage_rate=mortgage_rate,
        loan_term=loan_term,
        property_tax_rate=property_tax_rate,
        annual_insurance=annual_insurance,
        monthly_hoa=monthly_hoa,
        maintenance_pct=maintenance_pct,
        closing_cost_pct=closing_cost_pct,
        moving_cost=moving_cost,
        gross_monthly_income=p["gross_monthly"],
        after_tax_monthly_income=p["after_tax_monthly"],
        monthly_debt_payments=p["monthly_debt"],
        liquid_savings=p["liquid_savings"],
        emergency_fund_target_months=p["emergency_months"],
        monthly_non_housing_expenses=p["monthly_expenses"],
        monthly_retirement=p["monthly_retirement"],
        monthly_other_savings=p["monthly_other_savings"],
    )

    st.markdown("---")
    # Affordability status banner
    status = m["status"]
    if status == "Comfortable":
        st.success(f"### Affordability Status: {status_badge(status)}")
    elif status == "Stretched":
        st.warning(f"### Affordability Status: {status_badge(status)}")
    else:
        st.error(f"### Affordability Status: {status_badge(status)}")

    st.markdown(m["interpretation"])
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### Monthly Payment Breakdown")
        breakdown = {
            "Principal & Interest": m["pi_payment"],
            "Property Tax": m["monthly_tax"],
            "Homeowners Insurance": m["monthly_insurance"],
            "HOA": m["monthly_hoa"],
            "Maintenance Reserve": m["monthly_maintenance"],
            "**Total Housing Cost**": m["total_monthly_housing"],
        }
        df = pd.DataFrame({"Monthly ($)": breakdown}).reset_index()
        df.columns = ["Item", "Monthly ($)"]
        df["Monthly ($)"] = df["Monthly ($)"].map(lambda x: f"${x:,.0f}")
        st.dataframe(df, hide_index=True, use_container_width=True)

    with col2:
        st.markdown("#### Upfront Cash Required")
        upfront = {
            "Down Payment": down_payment,
            "Closing Costs": m["closing_costs"],
            "Moving/Furnishing": moving_cost,
            "**Total Cash Needed**": m["total_cash_needed"],
        }
        df2 = pd.DataFrame({"Amount ($)": upfront}).reset_index()
        df2.columns = ["Item", "Amount ($)"]
        df2["Amount ($)"] = df2["Amount ($)"].map(lambda x: f"${x:,.0f}")
        st.dataframe(df2, hide_index=True, use_container_width=True)

    with col3:
        st.markdown("#### Key Ratios & Cash Position")
        st.metric("Housing Cost / Gross Income", fmt_pct(m["housing_pct_gross"]),
                  delta="over 28% limit" if m["housing_pct_gross"] > 28 else "within 28%",
                  delta_color="inverse" if m["housing_pct_gross"] > 28 else "normal")
        st.metric("Debt-to-Income Ratio", fmt_pct(m["dti"]),
                  delta="over 36% limit" if m["dti"] > 36 else "within 36%",
                  delta_color="inverse" if m["dti"] > 36 else "normal")
        st.metric("Remaining Savings After Closing", fmt_dollar(m["remaining_savings"]))
        ef_display = max(0.0, m["emergency_fund_months_remaining"])
        st.metric("Emergency Fund After Closing", f"{ef_display:.1f} months",
                  delta=f"target: {p['emergency_months']} months",
                  delta_color="inverse" if ef_display < p["emergency_months"] else "normal")
        st.metric("Monthly Cash Flow After Purchase", fmt_dollar(m["monthly_cash_flow"]),
                  delta_color="inverse" if m["monthly_cash_flow"] < 0 else "normal")

    if m["remaining_savings"] < 0:
        st.error("You do not have enough liquid savings to cover this purchase.")

    return dict(
        home_price=home_price,
        down_payment=down_payment,
        mortgage_rate=mortgage_rate,
        loan_term=loan_term,
        property_tax_rate=property_tax_rate,
        annual_insurance=annual_insurance,
        monthly_hoa=monthly_hoa,
        maintenance_pct=maintenance_pct,
        closing_cost_pct=closing_cost_pct,
        moving_cost=moving_cost,
        metrics=m,
    )


# ---------------------------------------------------------------------------
# Tab 3 — Rent vs Buy
# ---------------------------------------------------------------------------

def tab_rent_vs_buy(p: dict, aff: dict | None) -> dict | None:
    section_header("Rent vs Buy", "Is buying better than renting over your time horizon?")

    with st.expander("Rent vs Buy Inputs", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**Buying Inputs**")
            home_price = st.number_input("Home price ($)", 50_000, 5_000_000,
                                          aff["home_price"] if aff else 450_000, 5_000, key="rvb_price")
            down_payment = st.number_input("Down payment ($)", 0, 5_000_000,
                                            aff["down_payment"] if aff else 90_000, 1_000, key="rvb_dp")
            mortgage_rate = st.number_input("Mortgage rate (%)", 0.0, 20.0,
                                             aff["mortgage_rate"] if aff else 6.75, 0.05, key="rvb_rate")
            loan_term = st.selectbox("Loan term", [15, 20, 30],
                                      index=[15, 20, 30].index(aff["loan_term"]) if aff else 2, key="rvb_term")
            property_tax_rate = st.number_input("Property tax rate (%)", 0.0, 5.0,
                                                 aff["property_tax_rate"] if aff else 1.1, 0.05, key="rvb_ptax")
            annual_insurance = st.number_input("Annual insurance ($)", 0, 20_000,
                                                aff["annual_insurance"] if aff else 1_800, 100, key="rvb_ins")
            monthly_hoa = st.number_input("Monthly HOA ($)", 0, 5_000,
                                           aff["monthly_hoa"] if aff else 0, 25, key="rvb_hoa")
            maintenance_pct = st.number_input("Annual maintenance (% of value)", 0.0, 5.0,
                                               aff["maintenance_pct"] if aff else 1.0, 0.1, key="rvb_maint")
            closing_cost_pct = st.number_input("Closing cost (%)", 0.0, 10.0,
                                                aff["closing_cost_pct"] if aff else 2.5, 0.1, key="rvb_close")
        with col2:
            st.markdown("**Renting & Market Assumptions**")
            monthly_rent = st.number_input("Monthly rent ($)", 0, 20_000, p["current_rent"], 50, key="rvb_rent")
            annual_rent_increase = st.number_input("Annual rent increase (%)", 0.0, 15.0, 3.0, 0.1, key="rvb_rentinc")
            renters_insurance = st.number_input("Renter's insurance ($/month)", 0, 500, 15, 5, key="rvb_rins")
            home_appreciation = st.number_input("Expected annual home appreciation (%)", 0.0, 15.0, 3.5, 0.1, key="rvb_appr")
            selling_cost_pct = st.number_input("Selling cost (% of future home value)", 0.0, 10.0, 6.0, 0.1, key="rvb_sell")
            horizon = st.slider("Time horizon (years)", 1, 30, p["horizon_years"], 1, key="rvb_horizon")
            inv_return = st.number_input("Investment return if renting (%)", 0.0, 15.0, p["investment_return"], 0.1, key="rvb_inv")

    if down_payment > home_price:
        st.error("Down payment cannot exceed home price.")
        return None

    r = calculate_rent_vs_buy(
        home_price=home_price,
        down_payment=down_payment,
        mortgage_rate=mortgage_rate,
        loan_term=loan_term,
        property_tax_rate=property_tax_rate,
        annual_insurance=annual_insurance,
        monthly_hoa=monthly_hoa,
        maintenance_pct=maintenance_pct,
        closing_cost_pct=closing_cost_pct,
        home_appreciation_pct=home_appreciation,
        selling_cost_pct=selling_cost_pct,
        monthly_rent=monthly_rent,
        annual_rent_increase_pct=annual_rent_increase,
        renters_insurance_monthly=renters_insurance,
        investment_return_pct=inv_return,
        horizon_years=horizon,
    )

    st.markdown("---")
    rec = r["recommendation"]
    if rec == "Buying may be better":
        st.success(f"### Result: 🏠 {rec}")
    elif rec == "Renting may be better":
        st.info(f"### Result: 🏢 {rec}")
    else:
        st.warning(f"### Result: ⚖️ {rec}")

    st.markdown(r["interpretation"])
    st.markdown("---")

    col1, col2 = st.columns(2)
    with col1:
        st.markdown("#### Renting Scenario")
        rent_data = {
            "Total rent paid": r["total_rent_paid"],
            "Renter's insurance": r["total_renters_insurance"],
            "FV of invested upfront cash": r["fv_invested_upfront"],
            "FV of monthly cost advantage": max(0, r["fv_monthly_diff"]),
            "**Net wealth position (renting)**": r["rent_net_wealth"],
        }
        df = pd.DataFrame({"Amount ($)": rent_data}).reset_index()
        df.columns = ["Item", "Amount ($)"]
        df["Amount ($)"] = df["Amount ($)"].map(lambda x: f"${x:,.0f}")
        st.dataframe(df, hide_index=True, use_container_width=True)

    with col2:
        st.markdown("#### Buying Scenario")
        buy_data = {
            "Total mortgage payments": r["total_mortgage_paid"],
            "Total property tax": r["total_tax_paid"],
            "Total insurance": r["total_insurance_paid"],
            "Total HOA": r["total_hoa_paid"],
            "Total maintenance": r["total_maintenance_paid"],
            "Future home value": r["future_home_value"],
            "Remaining mortgage balance": r["remaining_balance"],
            "Selling costs": r["selling_costs"],
            "Home equity at sale": r["home_equity"],
            "**Net wealth position (buying)**": r["buy_net_wealth"],
        }
        df2 = pd.DataFrame({"Amount ($)": buy_data}).reset_index()
        df2.columns = ["Item", "Amount ($)"]
        df2["Amount ($)"] = df2["Amount ($)"].map(lambda x: f"${x:,.0f}")
        st.dataframe(df2, hide_index=True, use_container_width=True)

    st.markdown("---")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Net Position — Renting", fmt_dollar(r["rent_net_wealth"]))
    with col2:
        st.metric("Net Position — Buying", fmt_dollar(r["buy_net_wealth"]))
    with col3:
        diff = r["difference"]
        st.metric("Buying advantage vs Renting", fmt_dollar(diff),
                  delta="Buying ahead" if diff > 0 else "Renting ahead",
                  delta_color="normal" if diff > 0 else "inverse")

    if r["breakeven_year"]:
        st.info(f"Estimated breakeven: buying wins after approximately **{r['breakeven_year']} years**.")
    else:
        if rec == "Renting may be better":
            st.info(f"Buying does not appear to catch up within the {horizon}-year horizon.")

    return {"result": r, "horizon": horizon}


# ---------------------------------------------------------------------------
# Tab 4 — Mortgage Scenarios
# ---------------------------------------------------------------------------

def tab_mortgage_scenarios(p: dict, aff: dict | None):
    section_header("Mortgage Scenarios", "Compare up to 3 mortgage options side by side")

    base_price = aff["home_price"] if aff else 450_000
    base_dp = aff["down_payment"] if aff else 90_000
    base_rate = aff["mortgage_rate"] if aff else 6.75
    base_term = aff["loan_term"] if aff else 30
    base_ptax = aff["property_tax_rate"] if aff else 1.1
    base_ins = aff["annual_insurance"] if aff else 1_800
    base_hoa = aff["monthly_hoa"] if aff else 0
    base_maint = aff["maintenance_pct"] if aff else 1.0

    scenarios = []
    defaults = [
        ("Scenario A — Base", base_price, base_dp, base_rate, base_term),
        ("Scenario B — 15-yr", base_price, base_dp, base_rate - 0.5, 15),
        ("Scenario C — More Down", base_price, int(base_price * 0.2), base_rate - 0.25, base_term),
    ]

    tabs = st.tabs(["Scenario A", "Scenario B", "Scenario C"])
    for i, (tab, (dname, dprice, ddp, drate, dterm)) in enumerate(zip(tabs, defaults)):
        with tab:
            col1, col2 = st.columns(2)
            with col1:
                name = st.text_input("Scenario name", dname, key=f"sc_name_{i}")
                price = st.number_input("Home price ($)", 50_000, 5_000_000, dprice, 5_000, key=f"sc_price_{i}")
                dp = st.number_input("Down payment ($)", 0, 5_000_000, min(ddp, dprice), 1_000, key=f"sc_dp_{i}")
                rate = st.number_input("Mortgage rate (%)", 0.0, 20.0, drate, 0.05, key=f"sc_rate_{i}")
                term = st.selectbox("Loan term", [15, 20, 30],
                                    index=[15, 20, 30].index(dterm), key=f"sc_term_{i}")
            with col2:
                ptax = st.number_input("Property tax rate (%)", 0.0, 5.0, base_ptax, 0.05, key=f"sc_ptax_{i}")
                ins = st.number_input("Annual insurance ($)", 0, 20_000, base_ins, 100, key=f"sc_ins_{i}")
                hoa = st.number_input("Monthly HOA ($)", 0, 5_000, base_hoa, 25, key=f"sc_hoa_{i}")
                maint = st.number_input("Annual maintenance (%)", 0.0, 5.0, base_maint, 0.1, key=f"sc_maint_{i}")

            if dp > price:
                st.error("Down payment cannot exceed home price.")
                scenarios.append(None)
                continue

            loan = price - dp
            pi = calculate_monthly_mortgage_payment(loan, rate, term)
            monthly_tax = price * (ptax / 100) / 12
            monthly_ins = ins / 12
            monthly_maint = price * (maint / 100) / 12
            total_monthly = pi + monthly_tax + monthly_ins + hoa + monthly_maint
            total_interest = calculate_total_interest(loan, rate, term)
            closing = price * 0.025
            total_upfront = dp + closing
            housing_pct = (total_monthly / p["gross_monthly"] * 100) if p["gross_monthly"] > 0 else 0
            cash_flow = (
                p["after_tax_monthly"]
                - total_monthly
                - p["monthly_debt"]
                - p["monthly_expenses"]
                - p["monthly_retirement"]
                - p["monthly_other_savings"]
            )

            if housing_pct > 35 or cash_flow < 0:
                risk = "🔴 Risky"
            elif housing_pct > 28:
                risk = "🟡 Stretched"
            else:
                risk = "🟢 Comfortable"

            scenarios.append({
                "name": name,
                "price": price,
                "dp": dp,
                "loan": loan,
                "rate": rate,
                "term": term,
                "pi": pi,
                "total_monthly": total_monthly,
                "total_interest": total_interest,
                "total_upfront": total_upfront,
                "housing_pct": housing_pct,
                "cash_flow": cash_flow,
                "risk": risk,
            })

    # Comparison table
    valid = [s for s in scenarios if s is not None]
    if len(valid) >= 2:
        st.markdown("---")
        st.markdown("### Scenario Comparison")

        rows = {
            "Loan Amount": [fmt_dollar(s["loan"]) for s in valid],
            "Mortgage Rate": [fmt_pct(s["rate"]) for s in valid],
            "Loan Term": [f"{s['term']} yrs" for s in valid],
            "Monthly P&I": [fmt_dollar(s["pi"]) for s in valid],
            "Total Monthly Housing": [fmt_dollar(s["total_monthly"]) for s in valid],
            "Total Interest Paid": [fmt_dollar(s["total_interest"]) for s in valid],
            "Upfront Cash Needed": [fmt_dollar(s["total_upfront"]) for s in valid],
            "Housing % of Gross Income": [fmt_pct(s["housing_pct"]) for s in valid],
            "Monthly Cash Flow": [fmt_dollar(s["cash_flow"]) for s in valid],
            "Risk Label": [s["risk"] for s in valid],
        }
        df = pd.DataFrame(rows, index=[s["name"] for s in valid]).T
        st.dataframe(df, use_container_width=True)

        # Bar charts
        st.markdown("---")
        st.markdown("### Visual Comparison")
        col1, col2, col3 = st.columns(3)

        names = [s["name"].split("—")[0].strip() for s in valid]
        with col1:
            st.markdown("**Monthly Housing Payment**")
            chart_df = pd.DataFrame({"Scenario": names, "Monthly ($)": [s["total_monthly"] for s in valid]})
            st.bar_chart(chart_df.set_index("Scenario"))
        with col2:
            st.markdown("**Total Interest Over Loan**")
            chart_df2 = pd.DataFrame({"Scenario": names, "Total Interest ($)": [s["total_interest"] for s in valid]})
            st.bar_chart(chart_df2.set_index("Scenario"))
        with col3:
            st.markdown("**Upfront Cash Required**")
            chart_df3 = pd.DataFrame({"Scenario": names, "Upfront ($)": [s["total_upfront"] for s in valid]})
            st.bar_chart(chart_df3.set_index("Scenario"))


# ---------------------------------------------------------------------------
# Tab 5 — Refi Check
# ---------------------------------------------------------------------------

def tab_refi_check(aff: dict | None) -> dict | None:
    section_header("Refi Check", "Would refinancing make sense if rates fall?")

    default_balance = aff["metrics"]["loan_amount"] if aff else 350_000
    default_rate = aff["mortgage_rate"] if aff else 6.75
    default_term = aff["loan_term"] if aff else 30

    with st.expander("Refinance Inputs", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            current_balance = st.number_input("Current mortgage balance ($)", 0, 5_000_000,
                                               int(default_balance), 1_000, key="refi_bal")
            current_rate = st.number_input("Current interest rate (%)", 0.0, 20.0, default_rate, 0.05, key="refi_curr")
            current_remaining = st.number_input("Remaining term (years)", 1, 40, default_term, 1, key="refi_rem")
            expected_stay = st.number_input("How long you expect to stay (years)", 1, 40, 7, 1, key="refi_stay")
        with col2:
            new_rate = st.number_input("New refinance rate (%)", 0.0, 20.0,
                                        max(0.0, default_rate - 1.5), 0.05, key="refi_new")
            new_term = st.selectbox("New loan term (years)", [10, 15, 20, 25, 30], index=2, key="refi_newterm")
            closing_cost = st.number_input("Refinance closing costs ($)", 0, 50_000, 4_000, 250, key="refi_close")
            roll_closing = st.checkbox("Roll closing costs into new loan?", False, key="refi_roll")

    if current_balance <= 0:
        st.info("Enter your current mortgage balance to continue.")
        return None

    r = calculate_refi_breakeven(
        current_balance=current_balance,
        current_rate=current_rate,
        current_remaining_years=current_remaining,
        new_rate=new_rate,
        new_term_years=new_term,
        closing_cost=closing_cost,
        roll_closing_into_loan=roll_closing,
        expected_stay_years=expected_stay,
    )

    st.markdown("---")
    decision = r["decision"]
    if decision == "Likely Worth Considering":
        st.success(f"### Refi Decision: ✅ {decision}")
    elif decision == "Not Clearly Worth It":
        st.warning(f"### Refi Decision: ⚠️ {decision}")
    else:
        st.error(f"### Refi Decision: ❌ {decision}")

    st.markdown(r["interpretation"])
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Current Monthly Payment", fmt_dollar(r["current_payment"]))
        st.metric("New Monthly Payment", fmt_dollar(r["new_payment"]))
        st.metric("Monthly Savings", fmt_dollar(r["monthly_savings"]),
                  delta_color="normal" if r["monthly_savings"] > 0 else "inverse")
    with col2:
        if r["breakeven_months"] is not None:
            st.metric("Breakeven Period", f"{r['breakeven_months']:.0f} months ({r['breakeven_years']:.1f} yrs)")
        else:
            st.metric("Breakeven Period", "N/A")
        st.metric("Expected Stay", f"{expected_stay} years")
        st.metric("Total Savings Over Stay", fmt_dollar(r["total_savings_over_stay"]))
    with col3:
        st.metric("Total Interest (current loan)", fmt_dollar(r["total_interest_current"]))
        st.metric("Total Interest (new loan)", fmt_dollar(r["total_interest_new"]))
        interest_diff = r["total_interest_current"] - r["total_interest_new"]
        st.metric("Interest Difference", fmt_dollar(interest_diff),
                  delta="savings" if interest_diff > 0 else "cost",
                  delta_color="normal" if interest_diff > 0 else "inverse")

    return {"result": r, "current_rate": current_rate, "new_rate": new_rate}


# ---------------------------------------------------------------------------
# Tab 6 — Prepay vs Invest
# ---------------------------------------------------------------------------

def tab_prepay_vs_invest(p: dict, aff: dict | None) -> dict | None:
    section_header("Prepay vs Invest", "Should extra money go toward mortgage principal or investments?")

    default_balance = aff["metrics"]["loan_amount"] if aff else 350_000
    default_rate = aff["mortgage_rate"] if aff else 6.75
    default_term = aff["loan_term"] if aff else 30

    with st.expander("Prepay vs Invest Inputs", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            balance = st.number_input("Current mortgage balance ($)", 0, 5_000_000,
                                       int(default_balance), 1_000, key="pvi_bal")
            rate = st.number_input("Mortgage rate (%)", 0.0, 20.0, default_rate, 0.05, key="pvi_rate")
            remaining = st.number_input("Remaining loan term (years)", 1, 40, default_term, 1, key="pvi_rem")
            extra_monthly = st.number_input("Extra monthly amount available ($)", 0, 10_000, 300, 50, key="pvi_extra")
        with col2:
            inv_return = st.number_input("Expected annual investment return (%)", 0.0, 15.0,
                                          p["investment_return"], 0.1, key="pvi_inv")
            inv_tax = st.number_input("Investment tax rate estimate (%)", 0.0, 50.0, 15.0, 0.5, key="pvi_tax")
            horizon = st.slider("Time horizon (years)", 1, 30, min(p["horizon_years"], remaining), 1, key="pvi_horizon")
            risk_pref = st.selectbox("Risk preference", ["Conservative", "Balanced", "Aggressive"],
                                      index=1, key="pvi_risk")

    if balance <= 0 or extra_monthly <= 0:
        st.info("Enter your mortgage balance and extra monthly amount to continue.")
        return None

    r = calculate_prepay_vs_invest(
        current_balance=balance,
        mortgage_rate=rate,
        remaining_years=remaining,
        extra_monthly=extra_monthly,
        investment_return_pct=inv_return,
        investment_tax_rate=inv_tax,
        horizon_years=horizon,
        risk_preference=risk_pref,
    )

    st.markdown("---")
    rec = r["recommendation"]
    if rec == "Investing looks stronger":
        st.success(f"### Result: 📈 {rec}")
    elif rec == "Prepaying looks stronger":
        st.info(f"### Result: 🏠 {rec}")
    else:
        st.warning(f"### Result: ⚖️ {rec}")

    st.markdown(r["interpretation"])
    st.markdown("---")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown("#### Prepayment Path")
        st.metric("Mortgage Balance After Horizon", fmt_dollar(r["bal_with_prepay"]))
        st.metric("Balance Without Extra Payments", fmt_dollar(r["bal_without_prepay"]))
        st.metric("Extra Equity Built", fmt_dollar(r["prepay_benefit"]))
        if r["years_saved"] > 0 or r["mos_saved_remainder"] > 0:
            st.metric("Time Shaved Off Loan",
                      f"{r['years_saved']}y {r['mos_saved_remainder']}m")
    with col2:
        st.markdown("#### Investment Path")
        st.metric("FV of Invested Extra (after-tax)", fmt_dollar(r["fv_invest"]))
        st.metric("After-Tax Return Used", fmt_pct(r["after_tax_return"]))
    with col3:
        st.markdown("#### Comparison")
        diff = r["fv_invest"] - r["prepay_benefit"]
        st.metric("Investing vs Prepaying", fmt_dollar(abs(diff)),
                  delta="Investing ahead" if diff > 0 else "Prepaying ahead",
                  delta_color="normal" if diff > 0 else "inverse")
        st.metric("Guaranteed return (prepay)", fmt_pct(rate),
                  help="Prepaying provides a return equal to your mortgage rate — risk-free.")

    st.info(
        "**Note:** The investment projection is based on assumed returns and is not guaranteed. "
        "Prepaying provides a certain, risk-free return equal to your mortgage rate."
    )

    return {"result": r, "rate": rate, "horizon": horizon}


# ---------------------------------------------------------------------------
# Tab 7 — Summary Report
# ---------------------------------------------------------------------------

def tab_summary(p: dict, aff: dict | None, rvb: dict | None, refi: dict | None, pvi: dict | None):
    section_header("Summary Report", "Your HomeWise Planner decision overview")

    if aff is None:
        st.warning("Please complete the Buy Affordability tab first to see the full summary.")
        return

    m = aff["metrics"]

    # HomeWise Score
    rvb_diff = rvb["result"]["difference"] if rvb else 0
    score_result = calculate_homewise_score(
        housing_pct_gross=m["housing_pct_gross"],
        dti=m["dti"],
        emergency_fund_months_remaining=m["emergency_fund_months_remaining"],
        emergency_fund_target=p["emergency_months"],
        monthly_cash_flow=m["monthly_cash_flow"],
        after_tax_monthly_income=p["after_tax_monthly"],
        rent_vs_buy_diff=rvb_diff,
        current_monthly_rent=p["current_rent"],
        total_monthly_housing=m["total_monthly_housing"],
        total_cash_needed=m["total_cash_needed"],
        liquid_savings=p["liquid_savings"],
    )

    score = score_result["score"]
    band = score_result["band"]

    # Score display
    st.markdown("---")
    col1, col2 = st.columns([1, 2])
    with col1:
        st.metric("HomeWise Score", f"{score} / 100")
        if score >= 80:
            st.success(f"**{band}**")
        elif score >= 60:
            st.warning(f"**{band}**")
        else:
            st.error(f"**{band}**")
    with col2:
        st.markdown(score_result["interpretation"])

    st.markdown("---")
    st.markdown("### Key Metrics at a Glance")

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Affordability Status", m["status"])
        st.metric("Monthly Housing Payment", fmt_dollar(m["total_monthly_housing"]))
    with col2:
        st.metric("Cash Needed Upfront", fmt_dollar(m["total_cash_needed"]))
        st.metric("Remaining Savings", fmt_dollar(m["remaining_savings"]))
    with col3:
        st.metric("Emergency Fund After Purchase", f"{max(0.0, m['emergency_fund_months_remaining']):.1f} months")
        st.metric("Monthly Cash Flow", fmt_dollar(m["monthly_cash_flow"]))
    with col4:
        st.metric("Housing % of Gross Income", fmt_pct(m["housing_pct_gross"]))
        st.metric("Debt-to-Income Ratio", fmt_pct(m["dti"]))

    st.markdown("---")
    st.markdown("### Decision Summary")

    summary_rows = []

    summary_rows.append({"Module": "Buy Affordability", "Result": m["status"],
                          "Key Metric": f"Housing = {fmt_pct(m['housing_pct_gross'])} of gross income"})

    if rvb:
        r = rvb["result"]
        summary_rows.append({"Module": "Rent vs Buy", "Result": r["recommendation"],
                              "Key Metric": f"Buying advantage: {fmt_dollar(r['difference'])} over {rvb['horizon']} yrs"})
    else:
        summary_rows.append({"Module": "Rent vs Buy", "Result": "Not entered", "Key Metric": "—"})

    if refi:
        r = refi["result"]
        summary_rows.append({"Module": "Refi Check", "Result": r["decision"],
                              "Key Metric": f"Monthly savings: {fmt_dollar(r['monthly_savings'])}"})
    else:
        summary_rows.append({"Module": "Refi Check", "Result": "Not entered", "Key Metric": "—"})

    if pvi:
        r = pvi["result"]
        summary_rows.append({"Module": "Prepay vs Invest", "Result": r["recommendation"],
                              "Key Metric": f"Invest: {fmt_dollar(r['fv_invest'])} vs Prepay equity: {fmt_dollar(r['prepay_benefit'])}"})
    else:
        summary_rows.append({"Module": "Prepay vs Invest", "Result": "Not entered", "Key Metric": "—"})

    summary_rows.append({"Module": "HomeWise Score", "Result": f"{score}/100 — {band}", "Key Metric": "—"})

    df = pd.DataFrame(summary_rows)
    st.dataframe(df, hide_index=True, use_container_width=True)

    st.markdown("---")
    st.markdown(DISCLAIMER)

    # ---------------------------------------------------------------------------
    # Export
    # ---------------------------------------------------------------------------
    st.markdown("---")
    st.markdown("### Export")
    col1, col2 = st.columns(2)

    with col1:
        # CSV export
        csv_rows = [
            ["Section", "Metric", "Value"],
            ["Profile", "Gross Monthly Income", fmt_dollar(p["gross_monthly"])],
            ["Profile", "After-Tax Monthly Income", fmt_dollar(p["after_tax_monthly"])],
            ["Profile", "Liquid Savings", fmt_dollar(p["liquid_savings"])],
            ["Affordability", "Home Price", fmt_dollar(aff["home_price"])],
            ["Affordability", "Down Payment", fmt_dollar(aff["down_payment"])],
            ["Affordability", "Monthly Housing Cost", fmt_dollar(m["total_monthly_housing"])],
            ["Affordability", "Total Cash Needed", fmt_dollar(m["total_cash_needed"])],
            ["Affordability", "Remaining Savings", fmt_dollar(m["remaining_savings"])],
            ["Affordability", "Emergency Fund Months", f"{m['emergency_fund_months_remaining']:.1f}"],
            ["Affordability", "Housing % Gross", fmt_pct(m["housing_pct_gross"])],
            ["Affordability", "DTI", fmt_pct(m["dti"])],
            ["Affordability", "Monthly Cash Flow", fmt_dollar(m["monthly_cash_flow"])],
            ["Affordability", "Status", m["status"]],
        ]
        if rvb:
            r = rvb["result"]
            csv_rows += [
                ["Rent vs Buy", "Rent Net Wealth", fmt_dollar(r["rent_net_wealth"])],
                ["Rent vs Buy", "Buy Net Wealth", fmt_dollar(r["buy_net_wealth"])],
                ["Rent vs Buy", "Difference (Buy - Rent)", fmt_dollar(r["difference"])],
                ["Rent vs Buy", "Recommendation", r["recommendation"]],
            ]
        if refi:
            r = refi["result"]
            csv_rows += [
                ["Refi Check", "Monthly Savings", fmt_dollar(r["monthly_savings"])],
                ["Refi Check", "Breakeven Months", f"{r['breakeven_months']:.0f}" if r["breakeven_months"] else "N/A"],
                ["Refi Check", "Decision", r["decision"]],
            ]
        if pvi:
            r = pvi["result"]
            csv_rows += [
                ["Prepay vs Invest", "Invest FV", fmt_dollar(r["fv_invest"])],
                ["Prepay vs Invest", "Prepay Equity Benefit", fmt_dollar(r["prepay_benefit"])],
                ["Prepay vs Invest", "Recommendation", r["recommendation"]],
            ]
        csv_rows.append(["HomeWise Score", "Score", str(score)])
        csv_rows.append(["HomeWise Score", "Band", band])

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerows(csv_rows)
        st.download_button(
            "Download CSV Report",
            buf.getvalue(),
            file_name="homewise_planner_report.csv",
            mime="text/csv",
        )

    with col2:
        # Markdown report
        md_lines = [
            "# HomeWise Planner — Summary Report",
            "",
            "> This tool is for illustration purposes only and does not constitute financial, mortgage, tax, or investment advice.",
            "",
            "## Profile",
            f"- Gross monthly income: {fmt_dollar(p['gross_monthly'])}",
            f"- After-tax monthly income: {fmt_dollar(p['after_tax_monthly'])}",
            f"- Liquid savings: {fmt_dollar(p['liquid_savings'])}",
            f"- Planning horizon: {p['horizon_years']} years",
            "",
            "## Buy Affordability",
            f"- Home price: {fmt_dollar(aff['home_price'])}",
            f"- Down payment: {fmt_dollar(aff['down_payment'])} ({fmt_pct(m['down_payment_pct'])})",
            f"- Monthly housing cost: {fmt_dollar(m['total_monthly_housing'])}",
            f"- Total cash needed: {fmt_dollar(m['total_cash_needed'])}",
            f"- Remaining savings: {fmt_dollar(m['remaining_savings'])}",
            f"- Emergency fund remaining: {m['emergency_fund_months_remaining']:.1f} months",
            f"- Housing % gross income: {fmt_pct(m['housing_pct_gross'])}",
            f"- Debt-to-income ratio: {fmt_pct(m['dti'])}",
            f"- Monthly cash flow: {fmt_dollar(m['monthly_cash_flow'])}",
            f"- **Status: {m['status']}**",
            "",
        ]
        if rvb:
            r = rvb["result"]
            md_lines += [
                "## Rent vs Buy",
                f"- Rent net wealth: {fmt_dollar(r['rent_net_wealth'])}",
                f"- Buy net wealth: {fmt_dollar(r['buy_net_wealth'])}",
                f"- Difference: {fmt_dollar(r['difference'])}",
                f"- **Recommendation: {r['recommendation']}**",
                "",
            ]
        if refi:
            r = refi["result"]
            be = f"{r['breakeven_months']:.0f} months" if r["breakeven_months"] else "N/A"
            md_lines += [
                "## Refi Check",
                f"- Monthly savings: {fmt_dollar(r['monthly_savings'])}",
                f"- Breakeven: {be}",
                f"- **Decision: {r['decision']}**",
                "",
            ]
        if pvi:
            r = pvi["result"]
            md_lines += [
                "## Prepay vs Invest",
                f"- Investment FV: {fmt_dollar(r['fv_invest'])}",
                f"- Prepay equity benefit: {fmt_dollar(r['prepay_benefit'])}",
                f"- **Recommendation: {r['recommendation']}**",
                "",
            ]
        md_lines += [
            "## HomeWise Score",
            f"- Score: **{score} / 100**",
            f"- Band: **{band}**",
            "",
            "---",
            "> This tool is for illustration purposes only and does not constitute financial, mortgage, tax, or investment advice.",
        ]

        md_content = "\n".join(md_lines)
        st.download_button(
            "Download Markdown Report",
            md_content,
            file_name="homewise_planner_report.md",
            mime="text/markdown",
        )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    # Sidebar inputs
    profile = sidebar_inputs()

    # Title
    st.title("🏠 HomeWise Planner")
    st.markdown("**Make smarter buy, rent, refinance, and mortgage prepayment decisions.**")
    st.markdown(DISCLAIMER)
    st.markdown("")

    # Tabs
    tabs = st.tabs([
        "📋 Profile",
        "🏠 Buy Affordability",
        "⚖️ Rent vs Buy",
        "📊 Mortgage Scenarios",
        "🔄 Refi Check",
        "💰 Prepay vs Invest",
        "📄 Summary Report",
    ])

    # Use session state to pass data between tabs
    if "aff_result" not in st.session_state:
        st.session_state.aff_result = None
    if "rvb_result" not in st.session_state:
        st.session_state.rvb_result = None
    if "refi_result" not in st.session_state:
        st.session_state.refi_result = None
    if "pvi_result" not in st.session_state:
        st.session_state.pvi_result = None

    with tabs[0]:
        tab_profile(profile)

    with tabs[1]:
        result = tab_affordability(profile)
        if result is not None:
            st.session_state.aff_result = result

    with tabs[2]:
        result = tab_rent_vs_buy(profile, st.session_state.aff_result)
        if result is not None:
            st.session_state.rvb_result = result

    with tabs[3]:
        tab_mortgage_scenarios(profile, st.session_state.aff_result)

    with tabs[4]:
        result = tab_refi_check(st.session_state.aff_result)
        if result is not None:
            st.session_state.refi_result = result

    with tabs[5]:
        result = tab_prepay_vs_invest(profile, st.session_state.aff_result)
        if result is not None:
            st.session_state.pvi_result = result

    with tabs[6]:
        tab_summary(
            profile,
            st.session_state.aff_result,
            st.session_state.rvb_result,
            st.session_state.refi_result,
            st.session_state.pvi_result,
        )


if __name__ == "__main__":
    main()
