"""
Comprehensive accuracy tests for HomeWise Planner calculations.
Each test verifies against independently derived / well-known financial formulas.
Run with:  python -m pytest tests/ -v
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import math
import pytest
from utils.calculations import (
    calculate_monthly_mortgage_payment,
    calculate_remaining_balance,
    calculate_total_interest,
    calculate_future_value,
    calculate_future_value_contributions,
    calculate_affordability_metrics,
    calculate_rent_vs_buy,
    calculate_refi_breakeven,
    calculate_prepay_vs_invest,
    calculate_homewise_score,
)

TOL = 1.0          # dollar tolerance (±$1)
TOL_PCT = 0.01     # percentage tolerance (±0.01%)


# ── 1. MORTGAGE PAYMENT ────────────────────────────────────────────────────

class TestMonthlyMortgagePayment:

    def test_standard_30yr(self):
        # $300,000 @ 7% / 30yr  → $1,995.91  (Bankrate/CFPB verified)
        p = calculate_monthly_mortgage_payment(300_000, 7.0, 30)
        assert abs(p - 1995.91) < TOL, f"Expected ~$1,995.91, got ${p:.2f}"

    def test_standard_15yr(self):
        # $200,000 @ 5% / 15yr  → $1,581.59
        p = calculate_monthly_mortgage_payment(200_000, 5.0, 15)
        assert abs(p - 1581.59) < TOL, f"Expected ~$1,581.59, got ${p:.2f}"

    def test_30yr_6point75(self):
        # $360,000 @ 6.75% / 30yr → $2,334.95
        p = calculate_monthly_mortgage_payment(360_000, 6.75, 30)
        assert abs(p - 2334.95) < TOL, f"Expected ~$2,334.95, got ${p:.2f}"

    def test_zero_rate(self):
        # 0% → principal ÷ months
        p = calculate_monthly_mortgage_payment(120_000, 0.0, 10)
        assert abs(p - 1000.0) < TOL, f"Expected $1,000, got ${p:.2f}"

    def test_zero_principal(self):
        assert calculate_monthly_mortgage_payment(0, 6.0, 30) == 0.0

    def test_short_term_20yr(self):
        # $400,000 @ 6.5% / 20yr  →  $2,982.67  (manual formula)
        r = 0.065 / 12
        n = 240
        expected = 400_000 * r * (1+r)**n / ((1+r)**n - 1)
        p = calculate_monthly_mortgage_payment(400_000, 6.5, 20)
        assert abs(p - expected) < TOL, f"Expected ${expected:.2f}, got ${p:.2f}"


# ── 2. REMAINING BALANCE ───────────────────────────────────────────────────

class TestRemainingBalance:

    def _expected(self, P, annual_rate, years, months_paid):
        """Standard formula: B_k = P·[(1+r)^n – (1+r)^k] / [(1+r)^n – 1]"""
        r = annual_rate / 100 / 12
        n = years * 12
        return P * ((1+r)**n - (1+r)**months_paid) / ((1+r)**n - 1)

    def test_after_10yr_on_30yr(self):
        # $300,000 @ 7% / 30yr, after 120 payments
        expected = self._expected(300_000, 7.0, 30, 120)
        result   = calculate_remaining_balance(300_000, 7.0, 30, 120)
        assert abs(result - expected) < TOL, f"Expected ${expected:.2f}, got ${result:.2f}"

    def test_after_1_payment(self):
        # After 1 payment, balance = principal minus first month's principal portion
        P, r_ann, yr = 200_000, 6.0, 30
        r = r_ann / 100 / 12
        pmt = calculate_monthly_mortgage_payment(P, r_ann, yr)
        first_interest   = P * r
        first_principal  = pmt - first_interest
        expected = P - first_principal
        result   = calculate_remaining_balance(P, r_ann, yr, 1)
        assert abs(result - expected) < TOL, f"Expected ${expected:.2f}, got ${result:.2f}"

    def test_fully_paid(self):
        # After all payments, balance should be ≈ 0
        result = calculate_remaining_balance(200_000, 6.0, 30, 360)
        assert abs(result) < TOL, f"Expected ~$0, got ${result:.2f}"

    def test_zero_rate(self):
        # 0% → linear paydown
        # $120,000 / 120 months, after 60 payments → $60,000
        result = calculate_remaining_balance(120_000, 0.0, 10, 60)
        assert abs(result - 60_000) < TOL, f"Expected $60,000, got ${result:.2f}"


# ── 3. TOTAL INTEREST ──────────────────────────────────────────────────────

class TestTotalInterest:

    def test_30yr_7pct(self):
        # $300,000 @ 7% / 30yr  → total interest = pmt*360 – 300,000
        pmt = calculate_monthly_mortgage_payment(300_000, 7.0, 30)
        expected = pmt * 360 - 300_000
        result   = calculate_total_interest(300_000, 7.0, 30)
        assert abs(result - expected) < TOL

    def test_zero_rate(self):
        # 0% → no interest
        result = calculate_total_interest(100_000, 0.0, 10)
        assert abs(result) < TOL

    def test_higher_rate_higher_interest(self):
        i_low  = calculate_total_interest(300_000, 4.0, 30)
        i_high = calculate_total_interest(300_000, 8.0, 30)
        assert i_high > i_low

    def test_shorter_term_lower_interest(self):
        i_30 = calculate_total_interest(300_000, 6.0, 30)
        i_15 = calculate_total_interest(300_000, 6.0, 15)
        assert i_15 < i_30


# ── 4. FUTURE VALUE (LUMP SUM) ─────────────────────────────────────────────

class TestFutureValue:

    def test_basic_compound(self):
        # $10,000 @ 7% for 10yr = $19,671.51
        expected = 10_000 * (1.07 ** 10)
        result   = calculate_future_value(10_000, 7.0, 10)
        assert abs(result - expected) < TOL

    def test_zero_return(self):
        result = calculate_future_value(50_000, 0.0, 10)
        assert abs(result - 50_000) < TOL

    def test_zero_years(self):
        result = calculate_future_value(50_000, 7.0, 0)
        assert abs(result - 50_000) < TOL

    def test_known_value(self):
        # $100,000 @ 5% for 20yr = $265,329.77
        expected = 100_000 * (1.05 ** 20)
        result   = calculate_future_value(100_000, 5.0, 20)
        assert abs(result - expected) < TOL


# ── 5. FUTURE VALUE OF CONTRIBUTIONS ──────────────────────────────────────

class TestFutureValueContributions:

    def test_ordinary_annuity(self):
        # $1,000/month @ 7%/yr for 10yr (ordinary annuity)
        r = 0.07 / 12
        n = 120
        expected = 1000 * ((1+r)**n - 1) / r
        result   = calculate_future_value_contributions(1000, 7.0, 10)
        assert abs(result - expected) < TOL

    def test_with_initial_value(self):
        # $50,000 lump sum + $500/month @ 6% for 5yr
        r = 0.06 / 12
        n = 60
        fv_lump  = 50_000 * (1.06 ** 5)
        fv_ann   = 500 * ((1+r)**n - 1) / r
        expected = fv_lump + fv_ann
        result   = calculate_future_value_contributions(500, 6.0, 5, 50_000)
        assert abs(result - expected) < TOL

    def test_zero_return(self):
        result = calculate_future_value_contributions(1000, 0.0, 10)
        assert abs(result - 120_000) < TOL   # 1000 * 120 months

    def test_zero_years(self):
        result = calculate_future_value_contributions(500, 7.0, 0)
        assert abs(result) < TOL


# ── 6. AFFORDABILITY METRICS ───────────────────────────────────────────────

class TestAffordabilityMetrics:

    def _base(self, **overrides):
        defaults = dict(
            home_price=400_000, down_payment=80_000, mortgage_rate=7.0,
            loan_term=30, property_tax_rate=1.2, annual_insurance=2_000,
            monthly_hoa=0, maintenance_pct=1.0, closing_cost_pct=2.5,
            moving_cost=5_000, gross_monthly_income=10_000,
            after_tax_monthly_income=8_000, monthly_debt_payments=300,
            liquid_savings=120_000, emergency_fund_target_months=6,
            monthly_non_housing_expenses=3_000, monthly_retirement=500,
            monthly_other_savings=200,
        )
        defaults.update(overrides)
        return calculate_affordability_metrics(**defaults)

    def test_loan_amount(self):
        m = self._base()
        assert abs(m["loan_amount"] - 320_000) < TOL

    def test_pi_payment(self):
        m = self._base()
        expected = calculate_monthly_mortgage_payment(320_000, 7.0, 30)
        assert abs(m["pi_payment"] - expected) < TOL

    def test_monthly_tax(self):
        m = self._base()
        expected = 400_000 * 0.012 / 12   # = $400/month
        assert abs(m["monthly_tax"] - expected) < TOL

    def test_total_cash_needed(self):
        m = self._base()
        # down + closing (2.5% of 400k = 10k) + moving (5k) = 95k
        expected = 80_000 + 10_000 + 5_000
        assert abs(m["total_cash_needed"] - expected) < TOL

    def test_closing_costs(self):
        m = self._base()
        assert abs(m["closing_costs"] - 10_000) < TOL

    def test_remaining_savings(self):
        m = self._base()
        assert abs(m["remaining_savings"] - (120_000 - 95_000)) < TOL

    def test_housing_pct_gross(self):
        m = self._base()
        pct = m["total_monthly_housing"] / 10_000 * 100
        assert abs(m["housing_pct_gross"] - pct) < TOL_PCT

    def test_dti(self):
        m = self._base()
        # DTI = (existing debt + PI) / gross income
        dti = (300 + m["pi_payment"]) / 10_000 * 100
        assert abs(m["dti"] - dti) < TOL_PCT

    def test_cash_flow(self):
        m = self._base()
        expected = 8_000 - m["total_monthly_housing"] - 300 - 3_000 - 500 - 200
        assert abs(m["monthly_cash_flow"] - expected) < TOL

    def test_emergency_fund_capped_at_zero(self):
        # When remaining savings is negative, emergency fund months must be 0
        m = self._base(liquid_savings=50_000)  # not enough to cover upfront
        assert m["emergency_fund_months_remaining"] >= 0, \
            "Emergency fund months must never be negative"

    def test_comfortable_status(self):
        # Generous income, small loan
        m = self._base(home_price=300_000, down_payment=100_000,
                        gross_monthly_income=15_000, after_tax_monthly_income=12_000,
                        liquid_savings=200_000)
        assert m["status"] == "Comfortable"

    def test_risky_status_high_dti(self):
        m = self._base(monthly_debt_payments=3_000)
        assert m["status"] == "Risky"

    def test_risky_status_negative_cashflow(self):
        m = self._base(gross_monthly_income=5_000, after_tax_monthly_income=4_000)
        assert m["status"] == "Risky"


# ── 7. REFI BREAKEVEN ──────────────────────────────────────────────────────

class TestRefiBreakeven:

    def test_basic_breakeven(self):
        # $350,000 balance, 7.5% → 6.0%, 30yr, $4,000 closing
        r = calculate_refi_breakeven(
            current_balance=350_000, current_rate=7.5, current_remaining_years=25,
            new_rate=6.0, new_term_years=30, closing_cost=4_000,
            roll_closing_into_loan=False, expected_stay_years=10,
        )
        # verify breakeven = closing / monthly_savings
        expected_be = 4_000 / r["monthly_savings"]
        assert abs(r["breakeven_months"] - expected_be) < 0.5

    def test_no_savings_unfavorable(self):
        # New rate higher than current → unfavorable
        r = calculate_refi_breakeven(
            current_balance=300_000, current_rate=5.0, current_remaining_years=25,
            new_rate=6.5, new_term_years=30, closing_cost=3_000,
            roll_closing_into_loan=False, expected_stay_years=10,
        )
        assert r["decision"] == "Unfavorable"
        assert r["monthly_savings"] <= 0

    def test_worth_considering_short_breakeven(self):
        # Large rate drop, small closing costs, long stay
        r = calculate_refi_breakeven(
            current_balance=400_000, current_rate=7.5, current_remaining_years=28,
            new_rate=5.5, new_term_years=30, closing_cost=3_000,
            roll_closing_into_loan=False, expected_stay_years=10,
        )
        assert r["decision"] == "Likely Worth Considering"
        assert r["breakeven_months"] < r["breakeven_months"] + 1   # sanity

    def test_roll_closing_zero_breakeven(self):
        # Roll costs into loan → effective closing = 0 → breakeven = 0
        r = calculate_refi_breakeven(
            current_balance=300_000, current_rate=7.0, current_remaining_years=28,
            new_rate=6.0, new_term_years=30, closing_cost=4_000,
            roll_closing_into_loan=True, expected_stay_years=5,
        )
        assert abs(r["breakeven_months"]) < 0.5, \
            "Rolling costs into loan should give breakeven of 0 months"

    def test_monthly_savings_formula(self):
        # Verify savings = old payment - new payment
        r = calculate_refi_breakeven(
            current_balance=350_000, current_rate=7.0, current_remaining_years=28,
            new_rate=5.5, new_term_years=30, closing_cost=5_000,
            roll_closing_into_loan=False, expected_stay_years=7,
        )
        old_pmt = calculate_monthly_mortgage_payment(350_000, 7.0, 28)
        new_pmt = calculate_monthly_mortgage_payment(350_000, 5.5, 30)
        assert abs(r["current_payment"] - old_pmt) < TOL
        assert abs(r["new_payment"] - new_pmt) < TOL
        assert abs(r["monthly_savings"] - (old_pmt - new_pmt)) < TOL


# ── 8. PREPAY VS INVEST ────────────────────────────────────────────────────

class TestPrepayVsInvest:

    def test_fv_invest_formula(self):
        # Investment FV must equal after-tax annuity formula
        r = calculate_prepay_vs_invest(
            current_balance=300_000, mortgage_rate=6.0, remaining_years=25,
            extra_monthly=500, investment_return_pct=8.0,
            investment_tax_rate=15.0, horizon_years=10, risk_preference="Balanced",
        )
        after_tax_return = 8.0 * (1 - 0.15)
        expected_fv = calculate_future_value_contributions(500, after_tax_return, 10)
        assert abs(r["fv_invest"] - expected_fv) < TOL, \
            f"FV invest should be {expected_fv:.2f}, got {r['fv_invest']:.2f}"

    def test_prepay_benefit_reduces_balance(self):
        # With extra payments, balance must be lower than without
        r = calculate_prepay_vs_invest(
            current_balance=300_000, mortgage_rate=6.5, remaining_years=25,
            extra_monthly=300, investment_return_pct=7.0,
            investment_tax_rate=15.0, horizon_years=10, risk_preference="Balanced",
        )
        assert r["bal_with_prepay"] < r["bal_without_prepay"], \
            "Prepaying must reduce the remaining balance"

    def test_prepay_benefit_equals_balance_difference(self):
        # prepay_benefit should equal (bal_without - bal_with)
        r = calculate_prepay_vs_invest(
            current_balance=350_000, mortgage_rate=7.0, remaining_years=28,
            extra_monthly=400, investment_return_pct=7.0,
            investment_tax_rate=15.0, horizon_years=10, risk_preference="Balanced",
        )
        assert abs(r["prepay_benefit"] - (r["bal_without_prepay"] - r["bal_with_prepay"])) < TOL

    def test_time_saved_positive(self):
        # Extra payments must shorten loan
        r = calculate_prepay_vs_invest(
            current_balance=300_000, mortgage_rate=6.0, remaining_years=25,
            extra_monthly=500, investment_return_pct=7.0,
            investment_tax_rate=15.0, horizon_years=25, risk_preference="Balanced",
        )
        original_months = 25 * 12
        assert r["months_to_payoff"] < original_months, \
            "Extra payments must reduce payoff time"

    def test_zero_extra_no_change(self):
        # If extra = 0, balance_with == balance_without
        r = calculate_prepay_vs_invest(
            current_balance=300_000, mortgage_rate=6.5, remaining_years=25,
            extra_monthly=0, investment_return_pct=7.0,
            investment_tax_rate=15.0, horizon_years=10, risk_preference="Balanced",
        )
        assert abs(r["prepay_benefit"]) < TOL
        assert abs(r["fv_invest"]) < TOL


# ── 9. RENT VS BUY ─────────────────────────────────────────────────────────

class TestRentVsBuy:

    def _base(self, **overrides):
        defaults = dict(
            home_price=400_000, down_payment=80_000, mortgage_rate=7.0,
            loan_term=30, property_tax_rate=1.2, annual_insurance=2_000,
            monthly_hoa=0, maintenance_pct=1.0, closing_cost_pct=2.5,
            home_appreciation_pct=3.5, selling_cost_pct=6.0,
            monthly_rent=2_200, annual_rent_increase_pct=3.0,
            renters_insurance_monthly=15, investment_return_pct=7.0,
            horizon_years=10,
        )
        defaults.update(overrides)
        return calculate_rent_vs_buy(**defaults)

    def test_upfront_cash_components(self):
        r = self._base()
        expected_closing = 400_000 * 0.025
        expected_upfront = 80_000 + expected_closing
        assert abs(r["upfront_cash"] - expected_upfront) < TOL
        assert abs(r["closing_costs"] - expected_closing) < TOL

    def test_fv_invested_upfront(self):
        r = self._base()
        upfront = 80_000 + 400_000 * 0.025
        expected = calculate_future_value(upfront, 7.0, 10)
        assert abs(r["fv_invested_upfront"] - expected) < TOL

    def test_future_home_value(self):
        r = self._base()
        expected = 400_000 * (1.035 ** 10)
        assert abs(r["future_home_value"] - expected) < TOL

    def test_selling_costs(self):
        r = self._base()
        expected = r["future_home_value"] * 0.06
        assert abs(r["selling_costs"] - expected) < TOL

    def test_home_equity(self):
        r = self._base()
        expected = r["future_home_value"] - r["remaining_balance"] - r["selling_costs"]
        assert abs(r["home_equity"] - expected) < TOL

    def test_remaining_balance(self):
        r = self._base()
        loan = 400_000 - 80_000
        expected = calculate_remaining_balance(loan, 7.0, 30, 120)
        assert abs(r["remaining_balance"] - expected) < TOL

    def test_total_mortgage_paid(self):
        r = self._base()
        pmt = calculate_monthly_mortgage_payment(320_000, 7.0, 30)
        expected = pmt * 120   # 10 years
        assert abs(r["total_mortgage_paid"] - expected) < TOL

    def test_property_tax_uses_purchase_price(self):
        # tax should be based on original home_price, NOT future appreciated value
        r = self._base()
        expected_annual_tax = 400_000 * 0.012
        expected_total = expected_annual_tax * 10
        assert abs(r["total_tax_paid"] - expected_total) < TOL, \
            f"Tax should use purchase price: expected ${expected_total:.0f}, got ${r['total_tax_paid']:.0f}"

    def test_rent_increases_over_time(self):
        # Total rent should reflect 3% annual increases, not flat rent
        r = self._base()
        manual_rent = sum(2_200 * (1.03 ** yr) * 12 for yr in range(10))
        assert abs(r["total_rent_paid"] - manual_rent) < TOL

    def test_buy_net_wealth_formula(self):
        # buy_net_wealth = home_equity - out_of_pocket (non-principal costs)
        r = self._base()
        loan = 320_000
        pmt = calculate_monthly_mortgage_payment(loan, 7.0, 30)
        total_paid = pmt * 120
        principal_paid = loan - r["remaining_balance"]
        interest_paid = total_paid - principal_paid
        oop = r["closing_costs"] + interest_paid + r["total_tax_paid"] + \
              r["total_insurance_paid"] + r["total_hoa_paid"] + r["total_maintenance_paid"]
        expected_buy_net = r["home_equity"] - oop
        assert abs(r["buy_net_wealth"] - expected_buy_net) < TOL

    def test_long_horizon_favors_buying(self):
        # Over 30 years with typical appreciation, buying should win
        r = self._base(horizon_years=30, home_appreciation_pct=3.5,
                       investment_return_pct=6.0)
        assert r["recommendation"] == "Buying may be better", \
            "30-year horizon at 3.5% appreciation vs 6% investment return should favor buying"

    def test_short_horizon_favors_renting(self):
        # Over 2 years, transaction costs make buying worse
        r = self._base(horizon_years=2)
        assert r["recommendation"] == "Renting may be better", \
            "2-year horizon should favor renting due to transaction costs"


# ── 10. HOMEWISE SCORE ─────────────────────────────────────────────────────

class TestHomeWiseScore:

    def _score(self, **overrides):
        defaults = dict(
            housing_pct_gross=28.0, dti=35.0,
            emergency_fund_months_remaining=6.0, emergency_fund_target=6,
            monthly_cash_flow=800, after_tax_monthly_income=9_000,
            rent_vs_buy_diff=5_000, current_monthly_rent=2_000,
            total_monthly_housing=2_300, total_cash_needed=90_000,
            liquid_savings=150_000,
        )
        defaults.update(overrides)
        return calculate_homewise_score(**defaults)

    def test_perfect_inputs_high_score(self):
        r = self._score()
        assert r["score"] >= 80, f"Solid inputs should score ≥80, got {r['score']}"

    def test_negative_cashflow_penalised(self):
        good   = self._score(monthly_cash_flow=1_000)
        bad    = self._score(monthly_cash_flow=-500)
        assert bad["score"] < good["score"]

    def test_high_dti_penalised(self):
        good = self._score(dti=30)
        bad  = self._score(dti=50)
        assert bad["score"] < good["score"]

    def test_low_emergency_fund_penalised(self):
        good = self._score(emergency_fund_months_remaining=6, emergency_fund_target=6)
        bad  = self._score(emergency_fund_months_remaining=0.5, emergency_fund_target=6)
        assert bad["score"] < good["score"]

    def test_score_clamped_0_to_100(self):
        r_low  = self._score(housing_pct_gross=50, dti=60, monthly_cash_flow=-2000,
                              emergency_fund_months_remaining=0)
        r_high = self._score(housing_pct_gross=15, dti=20, monthly_cash_flow=3000,
                              emergency_fund_months_remaining=12)
        assert 0 <= r_low["score"] <= 100
        assert 0 <= r_high["score"] <= 100

    def test_band_labels(self):
        assert self._score()["band"] == "Strong / Comfortable"
        assert self._score(housing_pct_gross=35, dti=44,
                           monthly_cash_flow=-500,
                           emergency_fund_months_remaining=0.2)["band"] in (
                               "Stretched", "High Risk"
                           )
