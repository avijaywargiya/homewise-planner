"""
HomeWise Planner - Core calculation functions
"""

import numpy as np


# ---------------------------------------------------------------------------
# Mortgage / loan helpers
# ---------------------------------------------------------------------------

def calculate_monthly_mortgage_payment(principal: float, annual_rate: float, years: int) -> float:
    """Standard amortizing mortgage payment (handles 0% rate)."""
    if principal <= 0:
        return 0.0
    n = years * 12
    if annual_rate == 0:
        return principal / n
    r = annual_rate / 100 / 12
    return principal * r * (1 + r) ** n / ((1 + r) ** n - 1)


def calculate_remaining_balance(principal: float, annual_rate: float, years: int, months_paid: int) -> float:
    """Remaining loan balance after months_paid payments."""
    if principal <= 0:
        return 0.0
    n = years * 12
    if annual_rate == 0:
        return max(0.0, principal - (principal / n) * months_paid)
    r = annual_rate / 100 / 12
    return principal * ((1 + r) ** n - (1 + r) ** months_paid) / ((1 + r) ** n - 1)


def calculate_total_interest(principal: float, annual_rate: float, years: int) -> float:
    """Total interest paid over the full loan term."""
    payment = calculate_monthly_mortgage_payment(principal, annual_rate, years)
    return max(0.0, payment * years * 12 - principal)


# ---------------------------------------------------------------------------
# Time-value helpers
# ---------------------------------------------------------------------------

def calculate_future_value(present_value: float, annual_return: float, years: int) -> float:
    """FV of a lump sum."""
    if years <= 0:
        return present_value
    return present_value * (1 + annual_return / 100) ** years


def calculate_future_value_contributions(
    monthly_contribution: float,
    annual_return: float,
    years: int,
    initial_value: float = 0.0,
) -> float:
    """FV of regular monthly contributions plus an optional lump-sum starting value."""
    if years <= 0:
        return initial_value + monthly_contribution * 12 * years
    r_monthly = annual_return / 100 / 12
    n = years * 12
    if r_monthly == 0:
        fv_contributions = monthly_contribution * n
    else:
        fv_contributions = monthly_contribution * ((1 + r_monthly) ** n - 1) / r_monthly
    fv_lump = calculate_future_value(initial_value, annual_return, years)
    return fv_lump + fv_contributions


# ---------------------------------------------------------------------------
# Affordability
# ---------------------------------------------------------------------------

def calculate_affordability_metrics(
    home_price: float,
    down_payment: float,
    mortgage_rate: float,
    loan_term: int,
    property_tax_rate: float,
    annual_insurance: float,
    monthly_hoa: float,
    maintenance_pct: float,
    closing_cost_pct: float,
    moving_cost: float,
    gross_monthly_income: float,
    after_tax_monthly_income: float,
    monthly_debt_payments: float,
    liquid_savings: float,
    emergency_fund_target_months: float,
    monthly_non_housing_expenses: float,
    monthly_retirement: float,
    monthly_other_savings: float,
) -> dict:
    loan_amount = max(0.0, home_price - down_payment)
    pi_payment = calculate_monthly_mortgage_payment(loan_amount, mortgage_rate, loan_term)
    monthly_tax = home_price * (property_tax_rate / 100) / 12
    monthly_insurance = annual_insurance / 12
    monthly_maintenance = home_price * (maintenance_pct / 100) / 12

    total_monthly_housing = pi_payment + monthly_tax + monthly_insurance + monthly_hoa + monthly_maintenance

    closing_costs = home_price * (closing_cost_pct / 100)
    total_cash_needed = down_payment + closing_costs + moving_cost
    remaining_savings = liquid_savings - total_cash_needed

    emergency_fund_monthly_expenses = monthly_non_housing_expenses + total_monthly_housing
    emergency_fund_months_remaining = max(0.0, (
        remaining_savings / emergency_fund_monthly_expenses
        if emergency_fund_monthly_expenses > 0 else 0
    ))

    housing_pct_gross = (total_monthly_housing / gross_monthly_income * 100) if gross_monthly_income > 0 else 0
    housing_pct_net = (total_monthly_housing / after_tax_monthly_income * 100) if after_tax_monthly_income > 0 else 0

    total_monthly_debt = monthly_debt_payments + pi_payment
    dti = (total_monthly_debt / gross_monthly_income * 100) if gross_monthly_income > 0 else 0

    monthly_cash_flow = (
        after_tax_monthly_income
        - total_monthly_housing
        - monthly_debt_payments
        - monthly_non_housing_expenses
        - monthly_retirement
        - monthly_other_savings
    )

    # Affordability status
    issues = []
    if housing_pct_gross > 35:
        issues.append("housing cost exceeds 35% of gross income")
    elif housing_pct_gross > 28:
        issues.append("housing cost is between 28–35% of gross income")

    if dti > 43:
        issues.append("debt-to-income ratio exceeds 43%")
    elif dti > 36:
        issues.append("debt-to-income ratio is between 36–43%")

    if emergency_fund_months_remaining < emergency_fund_target_months * 0.5:
        issues.append("emergency fund would drop well below target")
    elif emergency_fund_months_remaining < emergency_fund_target_months:
        issues.append("emergency fund would be below target")

    if monthly_cash_flow < 0:
        issues.append("monthly cash flow would be negative")
    elif monthly_cash_flow < 200:
        issues.append("monthly cash flow would be very tight")

    red_conditions = (
        housing_pct_gross > 35
        or dti > 43
        or emergency_fund_months_remaining < emergency_fund_target_months * 0.5
        or monthly_cash_flow < 0
    )
    yellow_conditions = (
        housing_pct_gross > 28
        or dti > 36
        or emergency_fund_months_remaining < emergency_fund_target_months
        or monthly_cash_flow < 200
    )

    if red_conditions:
        status = "Risky"
        status_color = "red"
    elif yellow_conditions:
        status = "Stretched"
        status_color = "orange"
    else:
        status = "Comfortable"
        status_color = "green"

    if issues:
        issue_text = "; ".join(issues)
        interpretation = f"Based on your inputs, this purchase appears **{status.lower()}** because {issue_text}."
    else:
        interpretation = "Based on your inputs, this purchase appears **comfortable** across all key metrics."

    return {
        "loan_amount": loan_amount,
        "pi_payment": pi_payment,
        "monthly_tax": monthly_tax,
        "monthly_insurance": monthly_insurance,
        "monthly_hoa": monthly_hoa,
        "monthly_maintenance": monthly_maintenance,
        "total_monthly_housing": total_monthly_housing,
        "closing_costs": closing_costs,
        "total_cash_needed": total_cash_needed,
        "remaining_savings": remaining_savings,
        "emergency_fund_months_remaining": emergency_fund_months_remaining,
        "housing_pct_gross": housing_pct_gross,
        "housing_pct_net": housing_pct_net,
        "dti": dti,
        "monthly_cash_flow": monthly_cash_flow,
        "status": status,
        "status_color": status_color,
        "interpretation": interpretation,
        "down_payment_pct": (down_payment / home_price * 100) if home_price > 0 else 0,
    }


# ---------------------------------------------------------------------------
# Rent vs Buy
# ---------------------------------------------------------------------------

def calculate_rent_vs_buy(
    home_price: float,
    down_payment: float,
    mortgage_rate: float,
    loan_term: int,
    property_tax_rate: float,
    annual_insurance: float,
    monthly_hoa: float,
    maintenance_pct: float,
    closing_cost_pct: float,
    home_appreciation_pct: float,
    selling_cost_pct: float,
    monthly_rent: float,
    annual_rent_increase_pct: float,
    renters_insurance_monthly: float,
    investment_return_pct: float,
    horizon_years: int,
) -> dict:
    if horizon_years < 1:
        horizon_years = 1

    loan_amount = max(0.0, home_price - down_payment)
    closing_costs = home_price * (closing_cost_pct / 100)
    upfront_cash = down_payment + closing_costs

    pi_payment = calculate_monthly_mortgage_payment(loan_amount, mortgage_rate, loan_term)
    monthly_tax = home_price * (property_tax_rate / 100) / 12
    monthly_insurance = annual_insurance / 12
    monthly_maintenance = home_price * (maintenance_pct / 100) / 12
    total_buy_monthly = pi_payment + monthly_tax + monthly_insurance + monthly_hoa + monthly_maintenance

    # --- Buying side ---
    total_mortgage_paid = pi_payment * min(horizon_years, loan_term) * 12
    total_tax_paid = monthly_tax * 12 * horizon_years
    total_insurance_paid = monthly_insurance * 12 * horizon_years
    total_hoa_paid = monthly_hoa * 12 * horizon_years
    total_maintenance_paid = monthly_maintenance * 12 * horizon_years

    remaining_balance = calculate_remaining_balance(loan_amount, mortgage_rate, loan_term, horizon_years * 12)
    future_home_value = calculate_future_value(home_price, home_appreciation_pct, horizon_years)
    selling_costs = future_home_value * (selling_cost_pct / 100)
    home_equity = future_home_value - remaining_balance - selling_costs

    total_buy_costs = upfront_cash + total_mortgage_paid + total_tax_paid + total_insurance_paid + total_hoa_paid + total_maintenance_paid
    buy_net_position = home_equity - (total_buy_costs - upfront_cash - total_mortgage_paid + (total_mortgage_paid - (loan_amount - remaining_balance)))
    # Simplified: net position = equity gained minus out-of-pocket non-principal costs
    principal_paid = loan_amount - remaining_balance
    out_of_pocket_buy = (
        closing_costs
        + (total_mortgage_paid - principal_paid)  # interest paid
        + total_tax_paid
        + total_insurance_paid
        + total_hoa_paid
        + total_maintenance_paid
    )
    buy_net_wealth = home_equity - out_of_pocket_buy

    # --- Renting side ---
    total_rent = 0.0
    total_renters_insurance = renters_insurance_monthly * 12 * horizon_years
    rent = monthly_rent
    for y in range(horizon_years):
        total_rent += rent * 12
        rent *= 1 + annual_rent_increase_pct / 100

    fv_invested_upfront = calculate_future_value(upfront_cash, investment_return_pct, horizon_years)

    # Monthly cost difference invested (if renting is cheaper month-to-month)
    monthly_diff = total_buy_monthly - monthly_rent - renters_insurance_monthly
    fv_monthly_diff = 0.0
    if monthly_diff > 0:
        # buying costs more monthly → renter invests the difference
        fv_monthly_diff = calculate_future_value_contributions(monthly_diff, investment_return_pct, horizon_years)
    elif monthly_diff < 0:
        # renting costs more monthly → buyer has that extra to invest (negative for renter)
        fv_monthly_diff = -calculate_future_value_contributions(-monthly_diff, investment_return_pct, horizon_years)

    rent_net_wealth = fv_invested_upfront + fv_monthly_diff - total_rent - total_renters_insurance

    difference = buy_net_wealth - rent_net_wealth

    # Breakeven year approximation
    breakeven_year = None
    for y in range(1, horizon_years + 1):
        rb = calculate_remaining_balance(loan_amount, mortgage_rate, loan_term, y * 12)
        fhv = calculate_future_value(home_price, home_appreciation_pct, y)
        sc = fhv * (selling_cost_pct / 100)
        eq = fhv - rb - sc
        pp = loan_amount - rb
        mp = pi_payment * 12 * y
        oop = closing_costs + (mp - pp) + home_price * (property_tax_rate / 100) * y + monthly_insurance * 12 * y + monthly_hoa * 12 * y + monthly_maintenance * 12 * y
        b_net = eq - oop

        fv_up = calculate_future_value(upfront_cash, investment_return_pct, y)
        md = total_buy_monthly - monthly_rent - renters_insurance_monthly
        fv_md = 0.0
        if md > 0:
            fv_md = calculate_future_value_contributions(md, investment_return_pct, y)
        elif md < 0:
            fv_md = -calculate_future_value_contributions(-md, investment_return_pct, y)
        tr = sum(monthly_rent * (1 + annual_rent_increase_pct / 100) ** yr * 12 for yr in range(y))
        r_net = fv_up + fv_md - tr - renters_insurance_monthly * 12 * y

        if b_net >= r_net:
            breakeven_year = y
            break

    if difference > 5000:
        recommendation = "Buying may be better"
        rec_color = "green"
    elif difference < -5000:
        recommendation = "Renting may be better"
        rec_color = "blue"
    else:
        recommendation = "Too close to call"
        rec_color = "orange"

    if recommendation == "Buying may be better":
        if breakeven_year:
            interp = (
                f"Buying appears better after **{breakeven_year} years** mainly because projected equity growth "
                f"(${future_home_value:,.0f} home value) exceeds the flexibility and investment value of renting."
            )
        else:
            interp = "Buying appears better over this horizon due to projected home equity growth."
    elif recommendation == "Renting may be better":
        interp = (
            "Renting appears better over this horizon because the upfront cash and monthly savings "
            "have more time to compound outside the home."
        )
    else:
        interp = (
            "The financial outcome is very close over this horizon. Personal factors like flexibility, "
            "stability, and life plans may be the deciding factor."
        )

    return {
        "total_rent_paid": total_rent,
        "total_renters_insurance": total_renters_insurance,
        "fv_invested_upfront": fv_invested_upfront,
        "fv_monthly_diff": fv_monthly_diff,
        "rent_net_wealth": rent_net_wealth,
        "total_mortgage_paid": total_mortgage_paid,
        "total_tax_paid": total_tax_paid,
        "total_insurance_paid": total_insurance_paid,
        "total_hoa_paid": total_hoa_paid,
        "total_maintenance_paid": total_maintenance_paid,
        "remaining_balance": remaining_balance,
        "future_home_value": future_home_value,
        "selling_costs": selling_costs,
        "home_equity": home_equity,
        "out_of_pocket_buy": out_of_pocket_buy,
        "buy_net_wealth": buy_net_wealth,
        "difference": difference,
        "breakeven_year": breakeven_year,
        "recommendation": recommendation,
        "rec_color": rec_color,
        "interpretation": interp,
        "upfront_cash": upfront_cash,
        "closing_costs": closing_costs,
        "total_buy_monthly": total_buy_monthly,
    }


# ---------------------------------------------------------------------------
# Refi Check
# ---------------------------------------------------------------------------

def calculate_refi_breakeven(
    current_balance: float,
    current_rate: float,
    current_remaining_years: int,
    new_rate: float,
    new_term_years: int,
    closing_cost: float,
    roll_closing_into_loan: bool,
    expected_stay_years: int,
) -> dict:
    current_payment = calculate_monthly_mortgage_payment(current_balance, current_rate, current_remaining_years)

    new_principal = current_balance + (closing_cost if roll_closing_into_loan else 0)
    new_payment = calculate_monthly_mortgage_payment(new_principal, new_rate, new_term_years)

    monthly_savings = current_payment - new_payment

    if monthly_savings <= 0:
        return {
            "current_payment": current_payment,
            "new_payment": new_payment,
            "monthly_savings": monthly_savings,
            "breakeven_months": None,
            "breakeven_years": None,
            "total_savings_over_stay": monthly_savings * expected_stay_years * 12,
            "total_interest_current": calculate_total_interest(current_balance, current_rate, current_remaining_years),
            "total_interest_new": calculate_total_interest(new_principal, new_rate, new_term_years),
            "decision": "Unfavorable",
            "decision_color": "red",
            "interpretation": "Refinancing does not reduce your monthly payment. It does not make financial sense.",
        }

    effective_closing = closing_cost if not roll_closing_into_loan else 0
    breakeven_months = effective_closing / monthly_savings if monthly_savings > 0 else float("inf")
    breakeven_years = breakeven_months / 12

    total_savings = monthly_savings * expected_stay_years * 12 - (effective_closing if not roll_closing_into_loan else 0)

    if breakeven_months <= expected_stay_years * 12:
        decision = "Likely Worth Considering"
        decision_color = "green"
        interp = (
            f"Refinancing saves approximately **${monthly_savings:,.0f}/month** and breaks even in "
            f"**{breakeven_months:.0f} months ({breakeven_years:.1f} years)**. "
            f"Since you expect to stay for {expected_stay_years} years, it may be worth considering."
        )
    else:
        decision = "Not Clearly Worth It"
        decision_color = "orange"
        interp = (
            f"Refinancing saves **${monthly_savings:,.0f}/month** but the breakeven is "
            f"**{breakeven_months:.0f} months ({breakeven_years:.1f} years)**, which is longer than your "
            f"expected stay of {expected_stay_years} years. It likely does not make financial sense."
        )

    return {
        "current_payment": current_payment,
        "new_payment": new_payment,
        "monthly_savings": monthly_savings,
        "breakeven_months": breakeven_months,
        "breakeven_years": breakeven_years,
        "total_savings_over_stay": total_savings,
        "total_interest_current": calculate_total_interest(current_balance, current_rate, current_remaining_years),
        "total_interest_new": calculate_total_interest(new_principal, new_rate, new_term_years),
        "decision": decision,
        "decision_color": decision_color,
        "interpretation": interp,
        "new_principal": new_principal,
    }


# ---------------------------------------------------------------------------
# Prepay vs Invest
# ---------------------------------------------------------------------------

def calculate_prepay_vs_invest(
    current_balance: float,
    mortgage_rate: float,
    remaining_years: int,
    extra_monthly: float,
    investment_return_pct: float,
    investment_tax_rate: float,
    horizon_years: int,
    risk_preference: str,
) -> dict:
    horizon_years = min(horizon_years, remaining_years)

    # --- Prepay side: simulate month-by-month ---
    r = mortgage_rate / 100 / 12
    balance = current_balance
    base_payment = calculate_monthly_mortgage_payment(current_balance, mortgage_rate, remaining_years)
    total_payment = base_payment + extra_monthly

    interest_saved = 0.0
    months_to_payoff = 0
    for m in range(remaining_years * 12):
        if balance <= 0:
            break
        interest = balance * r if r > 0 else 0
        principal_paid = total_payment - interest
        if principal_paid >= balance:
            interest_saved_this = 0  # final payment
            balance = 0
            months_to_payoff = m + 1
            break
        balance -= principal_paid
        months_to_payoff = m + 1

    # Interest saved vs base scenario
    base_total_interest = calculate_total_interest(current_balance, mortgage_rate, remaining_years)
    # Balance after horizon years with extra payment
    bal_with_prepay = current_balance
    total_interest_with_prepay = 0.0
    for m in range(horizon_years * 12):
        if bal_with_prepay <= 0:
            break
        interest = bal_with_prepay * r if r > 0 else 0
        total_interest_with_prepay += interest
        pp = total_payment - interest
        bal_with_prepay = max(0, bal_with_prepay - pp)

    bal_without_prepay = calculate_remaining_balance(current_balance, mortgage_rate, remaining_years, horizon_years * 12)
    interest_saved = (bal_without_prepay - bal_with_prepay)  # equity difference
    prepay_benefit = interest_saved  # extra equity built up

    # --- Invest side ---
    after_tax_return = investment_return_pct * (1 - investment_tax_rate / 100)
    fv_invest = calculate_future_value_contributions(extra_monthly, after_tax_return, horizon_years)

    difference = fv_invest - prepay_benefit

    # Adjust recommendation based on risk preference
    threshold = {"Conservative": 0.10, "Balanced": 0.15, "Aggressive": 0.20}.get(risk_preference, 0.15)
    relative_diff = abs(difference) / max(prepay_benefit, fv_invest, 1)

    if difference > 0 and relative_diff > threshold:
        recommendation = "Investing looks stronger"
        rec_color = "green"
        interp = (
            f"Investing has a higher projected value (${fv_invest:,.0f} vs ${prepay_benefit:,.0f} in equity). "
            "However, prepaying provides a **more certain return** equal to your mortgage rate, reducing debt risk."
        )
    elif difference < 0 and relative_diff > threshold:
        recommendation = "Prepaying looks stronger"
        rec_color = "blue"
        interp = (
            f"Prepaying appears stronger in this scenario because your mortgage rate is high relative to "
            f"your assumed after-tax investment return. You'd build **${prepay_benefit:,.0f}** in extra equity "
            f"vs **${fv_invest:,.0f}** from investing."
        )
    else:
        recommendation = "Close call"
        rec_color = "orange"
        interp = (
            "The projected outcomes are similar. Consider your risk tolerance: prepaying offers a "
            "**guaranteed return** equal to your mortgage rate, while investing has higher potential but more uncertainty."
        )

    original_payoff_months = remaining_years * 12
    months_saved = original_payoff_months - months_to_payoff
    years_saved = months_saved // 12
    mos_saved_remainder = months_saved % 12

    return {
        "base_payment": base_payment,
        "total_payment_with_extra": total_payment,
        "bal_with_prepay": bal_with_prepay,
        "bal_without_prepay": bal_without_prepay,
        "prepay_benefit": prepay_benefit,
        "fv_invest": fv_invest,
        "after_tax_return": after_tax_return,
        "difference": difference,
        "recommendation": recommendation,
        "rec_color": rec_color,
        "interpretation": interp,
        "months_to_payoff": months_to_payoff,
        "years_saved": years_saved,
        "mos_saved_remainder": mos_saved_remainder,
        "base_total_interest": base_total_interest,
    }


# ---------------------------------------------------------------------------
# HomeWise Score
# ---------------------------------------------------------------------------

def calculate_homewise_score(
    housing_pct_gross: float,
    dti: float,
    emergency_fund_months_remaining: float,
    emergency_fund_target: float,
    monthly_cash_flow: float,
    after_tax_monthly_income: float,
    rent_vs_buy_diff: float,
    current_monthly_rent: float,
    total_monthly_housing: float,
    total_cash_needed: float,
    liquid_savings: float,
) -> dict:
    score = 100

    # Housing to income ratio (max -25)
    if housing_pct_gross > 35:
        score -= 25
    elif housing_pct_gross > 30:
        score -= 15
    elif housing_pct_gross > 28:
        score -= 8

    # DTI (max -20)
    if dti > 43:
        score -= 20
    elif dti > 36:
        score -= 10
    elif dti > 28:
        score -= 4

    # Emergency fund (max -20)
    ef_ratio = emergency_fund_months_remaining / emergency_fund_target if emergency_fund_target > 0 else 1
    if ef_ratio < 0.25:
        score -= 20
    elif ef_ratio < 0.5:
        score -= 12
    elif ef_ratio < 0.75:
        score -= 6
    elif ef_ratio < 1.0:
        score -= 3

    # Cash flow (max -20)
    if monthly_cash_flow < 0:
        score -= 20
    elif monthly_cash_flow < 200:
        score -= 12
    elif monthly_cash_flow < 500:
        score -= 5
    elif after_tax_monthly_income > 0 and monthly_cash_flow / after_tax_monthly_income < 0.05:
        score -= 3

    # Rent vs buy (max -10)
    if rent_vs_buy_diff < -20000:
        score -= 10
    elif rent_vs_buy_diff < -5000:
        score -= 5

    # Payment shock vs current rent (max -10)
    if current_monthly_rent > 0:
        shock_pct = (total_monthly_housing - current_monthly_rent) / current_monthly_rent * 100
        if shock_pct > 75:
            score -= 10
        elif shock_pct > 50:
            score -= 6
        elif shock_pct > 30:
            score -= 3

    # Upfront cash usage (max -5)
    if liquid_savings > 0:
        cash_used_pct = total_cash_needed / liquid_savings * 100
        if cash_used_pct > 90:
            score -= 5
        elif cash_used_pct > 75:
            score -= 3

    score = max(0, min(100, score))

    if score >= 80:
        band = "Strong / Comfortable"
        band_color = "green"
    elif score >= 60:
        band = "Manageable — watch carefully"
        band_color = "orange"
    elif score >= 40:
        band = "Stretched"
        band_color = "red"
    else:
        band = "High Risk"
        band_color = "red"

    if score >= 80:
        interp = f"Your HomeWise Score is **{score}**. The purchase looks financially solid across key metrics."
    elif score >= 60:
        interp = (
            f"Your HomeWise Score is **{score}**. The purchase may be manageable, but your cash cushion "
            "and monthly payment burden should be reviewed carefully before committing."
        )
    elif score >= 40:
        interp = (
            f"Your HomeWise Score is **{score}**. This purchase puts significant strain on your finances. "
            "Consider a lower price, larger down payment, or waiting to build more savings."
        )
    else:
        interp = (
            f"Your HomeWise Score is **{score}**. This purchase carries high financial risk based on your inputs. "
            "Strongly consider reassessing the home price, down payment, or timeline."
        )

    return {"score": score, "band": band, "band_color": band_color, "interpretation": interp}
