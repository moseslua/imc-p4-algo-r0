#!/usr/bin/env python3
"""
Rewritten TOMATOES strategy matching the profitable 64791 reference.
Key changes:
- TOMATOES limit doubled to 40 (was 20)
- Soft limit raised to 30 (was 17) 
- Symmetric 2.0 take threshold (was asymmetric 3.0/1.75)
- No ML model - pure EMA mean reversion
- Simplified skew without complex book state detection
- Only EMERALDS + TOMATOES trading (like reference)
"""

try:
    from datamodel import Order, TradingState
except ImportError:
    from prosperity3bt.datamodel import Order, TradingState


class Trader:
    def __init__(self):
        # EMERALDS - fixed fair, inventory-skewed market making
        self.emerald_fair = 10000
        self.emerald_limit = 80
        self.emerald_soft_limit = 60
        self.emerald_quote_size = 12
        self.emerald_take_size = 6

        # TOMATOES - simplified EMA mean reversion (matching 64791)
        self.tomato_limit = 40          # was 20 - doubled!
        self.tomato_soft_limit = 30     # was 17 - raised!
        self.tomato_quote_size = 8
        self.tomato_take_size = 8
        self.tomato_take_threshold = 2.0  # symmetric (was 3.0/1.75)
        self.tomato_ema_alpha = 0.08
        self.tomato_ema = None

    def run(self, state: TradingState):
        result = {}
        for product in state.order_depths:
            if product == "EMERALDS":
                result[product] = self.trade_emeralds(state, product)
            elif product == "TOMATOES":
                result[product] = self.trade_tomatoes(state, product)
            else:
                result[product] = []
        return result, 0, ""

    def trade_emeralds(self, state: TradingState, product: str):
        order_depth = state.order_depths[product]
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        position = state.position.get(product, 0)
        best_bid = max(order_depth.buy_orders)
        best_ask = min(order_depth.sell_orders)
        spread = best_ask - best_bid
        skew_ticks = int(round(position / 20))

        orders = []
        buy_room = max(0, self.emerald_limit - position)
        sell_room = max(0, self.emerald_limit + position)

        # Take: buy if ask at or below fair
        if best_ask <= self.emerald_fair and buy_room > 0:
            take_qty = min(self.emerald_take_size, buy_room, abs(order_depth.sell_orders[best_ask]))
            if take_qty > 0:
                orders.append(Order(product, best_ask, int(take_qty)))

        # Take: sell if bid at or above fair
        if best_bid >= self.emerald_fair and sell_room > 0:
            take_qty = min(self.emerald_take_size, sell_room, order_depth.buy_orders[best_bid])
            if take_qty > 0:
                orders.append(Order(product, best_bid, -int(take_qty)))

        if spread < 8:
            return orders

        # Quote with skew
        quote_bid = min(best_bid + 1, self.emerald_fair - 1 - skew_ticks)
        quote_ask = max(best_ask - 1, self.emerald_fair + 1 - skew_ticks)

        if position < self.emerald_soft_limit:
            quote_qty = min(self.emerald_quote_size, buy_room)
            if quote_qty > 0 and quote_bid < best_ask:
                orders.append(Order(product, int(quote_bid), int(quote_qty)))

        if position > -self.emerald_soft_limit:
            quote_qty = min(self.emerald_quote_size, sell_room)
            if quote_qty > 0 and quote_ask > best_bid:
                orders.append(Order(product, int(quote_ask), -int(quote_qty)))

        return orders

    def trade_tomatoes(self, state: TradingState, product: str):
        order_depth = state.order_depths[product]
        if not order_depth.buy_orders or not order_depth.sell_orders:
            return []

        position = state.position.get(product, 0)
        best_bid = max(order_depth.buy_orders)
        best_ask = min(order_depth.sell_orders)
        mid = (best_bid + best_ask) / 2
        spread = best_ask - best_bid

        # Update EMA
        if self.tomato_ema is None:
            self.tomato_ema = mid
        else:
            self.tomato_ema = (self.tomato_ema_alpha * mid) + ((1 - self.tomato_ema_alpha) * self.tomato_ema)

        fair = self.tomato_ema
        skew_ticks = int(round((2 * position) / self.tomato_limit))

        orders = []
        buy_room = max(0, self.tomato_limit - position)
        sell_room = max(0, self.tomato_limit + position)

        # Take: buy if ask well below fair
        if best_ask <= fair - self.tomato_take_threshold and buy_room > 0:
            take_qty = min(self.tomato_take_size, buy_room, abs(order_depth.sell_orders[best_ask]))
            if take_qty > 0:
                orders.append(Order(product, best_ask, int(take_qty)))

        # Take: sell if bid well above fair
        if best_bid >= fair + self.tomato_take_threshold and sell_room > 0:
            take_qty = min(self.tomato_take_size, sell_room, order_depth.buy_orders[best_bid])
            if take_qty > 0:
                orders.append(Order(product, best_bid, -int(take_qty)))

        if spread < 6:
            return orders

        # Quote with skew (simple, no complex book state)
        quote_bid = min(best_bid + 1, int(fair - 1 - skew_ticks))
        quote_ask = max(best_ask - 1, int(fair + 1 - skew_ticks))

        if position < self.tomato_soft_limit:
            quote_qty = min(self.tomato_quote_size, buy_room)
            if quote_qty > 0 and quote_bid < best_ask:
                orders.append(Order(product, int(quote_bid), int(quote_qty)))

        if position > -self.tomato_soft_limit:
            quote_qty = min(self.tomato_quote_size, sell_room)
            if quote_qty > 0 and quote_ask > best_bid:
                orders.append(Order(product, int(quote_ask), -int(quote_qty)))

        return orders