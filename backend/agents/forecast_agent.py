import numpy as np
import math
from datetime import datetime, timedelta
import random

class ForecastAgent:
    def __init__(self):
        pass

    def forecast_inventory(self, current_stock: float, daily_demand: float, safety_stock: float, lead_time_days: int, horizon_days: int = 30) -> dict:
        """
        Forecasts daily inventory levels and predicts stockout event windows.
        Calculates:
        - depletion_days: Number of days until stock reaches 0.
        - stockout_date: Date when stock hits 0.
        - stockout_probability: Probability of stockout before replacement inventory arrives.
        """
        daily_levels = []
        stock = current_stock
        depletion_day = -1
        
        # Add slight randomness to daily demand to represent real-world volatility
        demand_std = daily_demand * 0.15
        
        for d in range(horizon_days):
            daily_levels.append({
                "day": d,
                "date": (datetime.now() + timedelta(days=d)).strftime("%Y-%m-%d"),
                "stock": max(0.0, round(stock, 1))
            })
            if stock <= 0 and depletion_day == -1:
                depletion_day = d
            
            # Substract random demand
            actual_demand = max(0.0, random.normalvariate(daily_demand, demand_std))
            stock -= actual_demand
        
        # Calculate Stockout Probability
        # If lead time is longer than the time it takes to reach reorder point or 0
        days_to_deplete = current_stock / daily_demand if daily_demand > 0 else 999
        
        # stockout probability before shipment arrives (Lead time vs Depletion days)
        # Using normal distribution approximation: P(Demand during Lead Time > Current Stock)
        if daily_demand > 0:
            mean_demand_lead_time = daily_demand * lead_time_days
            variance_lead_time = (demand_std ** 2) * lead_time_days
            std_lead_time = np.sqrt(variance_lead_time)
            
            if std_lead_time > 0:
                z_score = (current_stock - mean_demand_lead_time) / std_lead_time
                # Approximation of CDF for normal distribution
                stockout_prob = 1.0 - (0.5 * (1.0 + math.erf(z_score / np.sqrt(2.0))))
            else:
                stockout_prob = 1.0 if mean_demand_lead_time > current_stock else 0.0
        else:
            stockout_prob = 0.0

        stockout_prob = round(stockout_prob * 100, 1)

        return {
            "current_stock": current_stock,
            "daily_demand": daily_demand,
            "safety_stock": safety_stock,
            "horizon_days": horizon_days,
            "depletion_days": round(days_to_deplete, 1) if days_to_deplete < 999 else -1,
            "stockout_probability": min(max(stockout_prob, 0.0), 100.0),
            "forecast_series": daily_levels
        }

    def forecast_commodity_price(self, commodity_name: str, historical_prices: list, forecast_months: int = 6) -> dict:
        """
        Uses numpy least-squares polynomial regression (linear) to predict future prices.
        historical_prices: list of floats representing monthly prices.
        """
        n = len(historical_prices)
        if n < 2:
            return {"error": "Not enough historical data to generate trend forecast."}
            
        x = np.array(range(n))
        y = np.array(historical_prices)
        
        # Fit a 1st degree polynomial (y = m*x + c)
        slope, intercept = np.polyfit(x, y, 1)
        
        forecast_series = []
        last_price = historical_prices[-1]
        
        # Generate future months
        for m in range(1, forecast_months + 1):
            future_x = n + m - 1
            predicted_price = slope * future_x + intercept
            # Ensure price doesn't go negative
            predicted_price = max(predicted_price, last_price * 0.2)
            
            forecast_series.append({
                "month": m,
                "price": round(predicted_price, 2)
            })

        percentage_change = ((forecast_series[-1]["price"] - last_price) / last_price) * 100
        
        return {
            "commodity": commodity_name,
            "current_price": round(last_price, 2),
            "predicted_price_next_month": forecast_series[0]["price"],
            "predicted_price_six_months": forecast_series[-1]["price"],
            "expected_change_pct": round(percentage_change, 1),
            "forecast_series": [{"month": "Current", "price": round(last_price, 2)}] + forecast_series
        }
