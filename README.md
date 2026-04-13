# EMERALDS + TOMATOES Trading Strategy

A lightweight, rule-based market-making strategy for **EMERALDS** and **TOMATOES**.

This implementation combines:
- **fixed-fair market making** for EMERALDS,
- **EMA-based mean reversion** for TOMATOES,
- **inventory-aware quote skewing**, and
- **hard/soft position limits** for risk control.


## Overview

The strategy follows the same core pattern in both products:

1. **Aggressively take mispriced liquidity** when the market is clearly away from fair value.
2. **Passively quote inside the spread** when spreads are wide enough.
3. **Skew quotes based on inventory** so the strategy naturally leans toward flattening risk.

Only two products are traded:
- **EMERALDS**
- **TOMATOES**

All other products are ignored.

---

## Strategy Logic

## 1) EMERALDS: fixed fair-value market making

EMERALDS is treated as a product with a **known constant fair value**:

```python
fair = 10000
```

### Trading rules

**Take liquidity**
- Buy when the best ask is **at or below 10000**.
- Sell when the best bid is **at or above 10000**.

**Make liquidity**
- If the spread is wide enough, place passive bid/ask quotes inside the market.
- Shift quotes using an inventory-based skew so the strategy becomes less aggressive when already long and more aggressive when short, or vice versa.

### Why this works

EMERALDS behaves like a product with a stable anchor price, so the edge comes from:
- buying below fair,
- selling above fair,
- and collecting spread while controlling inventory.

---

## 2) TOMATOES: EMA mean-reversion market making

TOMATOES does **not** use a fixed fair value.
Instead, it estimates fair using an **exponential moving average of midprice**:

```python
ema = alpha * mid + (1 - alpha) * prev_ema
```

with:

```python
alpha = 0.08
```

### Trading rules

**Take liquidity**
- Buy when the best ask is at least **2 ticks below fair**.
- Sell when the best bid is at least **2 ticks above fair**.

**Make liquidity**
- If the spread is wide enough, quote around the EMA fair value.
- Apply a simple inventory skew so quotes help reduce oversized positions.

### Why this works

The assumption is that TOMATOES is **mean reverting around a moving center**, not anchored to a constant price.
So the strategy tries to:
- fade temporary deviations from the EMA,
- earn spread through passive quoting,
- and avoid carrying too much inventory.

---

## Risk Management

The strategy uses both **hard limits** and **soft limits**.

### EMERALDS
- Hard position limit: **80**
- Soft limit: **60**
- Quote size: **12**
- Take size: **6**

### TOMATOES
- Hard position limit: **40**
- Soft limit: **30**
- Quote size: **8**
- Take size: **8**
- Take threshold: **2.0**
- EMA alpha: **0.08**

### Spread filters
Passive quoting only happens when the market is wide enough:
- EMERALDS: quote only if spread is at least **8**
- TOMATOES: quote only if spread is at least **6**

This prevents getting trapped quoting too tightly in compressed markets.

---

## Inventory Skew

A key part of the strategy is **inventory-aware pricing**.

Instead of quoting symmetrically at all times, the strategy shifts quotes depending on current position.

### Intuition
- If the strategy is **too long**, it should bias toward selling.
- If the strategy is **too short**, it should bias toward buying.

That is what the skew term is doing: it nudges quotes so the book naturally works inventory back toward neutral.

---

## Key Design Choices

This version is deliberately simplified and tuned around a more profitable reference implementation.

### Notable choices
- **Only EMERALDS and TOMATOES are traded**
- **No ML model**
- **Pure EMA mean reversion for TOMATOES**
- **Simplified inventory skew**
- **Symmetric take threshold for TOMATOES**
- **Larger TOMATOES limits than the earlier version**

This makes the strategy easier to reason about, easier to debug, and often more robust than a more complicated model-heavy version.

---

## Strengths

- Simple and interpretable
- Fast to execute
- Easy to tune
- Good inventory discipline
- Suitable for stable or mildly mean-reverting markets
- Passive + aggressive logic combined in one framework

---

## Weaknesses

- **TOMATOES can get run over in strong trends** because the EMA fair value lags.
- **EMERALDS depends on the fixed fair-value assumption** being correct.
- When spreads are tight, the strategy steps back and may miss some flow.
- No volatility regime detection, no adaptive sizing, and no richer order book modeling.

---

## High-Level Summary

In one sentence:

> This is an inventory-skewed market-making strategy that trades EMERALDS against a fixed fair value and TOMATOES against an EMA-based moving fair value.

Or even shorter:

> Buy cheap, sell expensive, quote the spread, and let inventory control shape the aggressiveness.

---

## File Structure

The `Trader` class contains:
- `run(...)` — dispatches product-specific logic
- `trade_emeralds(...)` — fixed-fair market-making logic
- `trade_tomatoes(...)` — EMA mean-reversion logic


