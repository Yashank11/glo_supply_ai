class FinanceAgent:
    def __init__(self):
        pass

    def calculate_disruption_cost(self, units_affected: float, unit_cost: float, selling_price: float, delay_days: float, freight_increase_per_unit: float = 0.0) -> dict:
        """
        Calculates:
        - revenue_at_risk: units_affected * selling_price
        - gross_margin_impact: units_affected * (selling_price - (unit_cost + freight_increase_per_unit))
        - net_financial_loss: estimated sales lost permanently vs delayed.
          If delay is long, we assume a fraction of revenue is lost (e.g. customer cancels order).
          Typically, 1% loss of sales per day of delay exceeding safety stock buffer.
        """
        revenue_at_risk = units_affected * selling_price
        original_margin_per_unit = selling_price - unit_cost
        new_margin_per_unit = selling_price - (unit_cost + freight_increase_per_unit)
        
        # Freight premium cost
        freight_premium_total = units_affected * freight_increase_per_unit
        
        # Estimate lost sales (not just delayed)
        # Rule of thumb: if delay is > 5 days, we lose 1.5% of sales per day delayed
        lost_sales_fraction = min(1.0, max(0.0, (delay_days - 3) * 0.015)) if delay_days > 3 else 0.0
        revenue_lost = revenue_at_risk * lost_sales_fraction
        margin_lost = revenue_lost * (original_margin_per_unit / selling_price)
        
        total_loss = margin_lost + freight_premium_total
        
        original_gross_margin = (original_margin_per_unit / selling_price) * 100 if selling_price > 0 else 0
        new_gross_margin = (new_margin_per_unit / selling_price) * 100 if selling_price > 0 else 0
        margin_drop_pct = original_gross_margin - new_gross_margin
        
        return {
            "revenue_at_risk": round(revenue_at_risk, 2),
            "revenue_lost": round(revenue_lost, 2),
            "freight_premium_total": round(freight_premium_total, 2),
            "margin_lost": round(margin_lost, 2),
            "total_financial_loss": round(total_loss, 2),
            "original_margin_pct": round(original_gross_margin, 1),
            "new_margin_pct": round(new_gross_margin, 1),
            "margin_drop_pct": round(margin_drop_pct, 1)
        }

    def evaluate_commodity_price_impact(self, annual_spend: float, price_increase_pct: float, pass_through_pct: float = 0.0) -> dict:
        """
        Evaluates what happens if oil/copper/lithium rises by X%.
        annual_spend: Current annual purchase value of commodity.
        price_increase_pct: Percentage increase (e.g. 30%).
        pass_through_pct: How much of this cost is passed to customer (e.g. 50%).
        """
        gross_cost_increase = annual_spend * (price_increase_pct / 100)
        customer_reimbursement = gross_cost_increase * (pass_through_pct / 100)
        net_margin_loss = gross_cost_increase - customer_reimbursement
        
        return {
            "gross_cost_increase": round(gross_cost_increase, 2),
            "customer_pass_through_revenue": round(customer_reimbursement, 2),
            "net_margin_loss": round(net_margin_loss, 2)
        }
