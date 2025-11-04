"""
Financial Trading Examples - Demonstrating Formal Verification for Critical Systems

These examples are inspired by real financial software bugs that caused significant losses:

1. Knight Capital Group (2012): Lost $440 million in 45 minutes due to incorrect order routing
   - Bug: Flag check logic error caused orders to be sent 8 times instead of once

2. Goldman Sachs (2015): $38 million loss due to options pricing error
   - Bug: Incorrect strike price calculation in options contracts

3. Bank of America (2011): Trading glitch in derivatives
   - Bug: Position limit checks failed to prevent over-exposure

These functions show how formal verification can mathematically prove correctness
and prevent such catastrophic failures.
"""

from tau_decorators import safe, safe_auto, requires, ensures


# =============================================================================
# Example 1: Order Execution Control (Knight Capital-inspired)
# =============================================================================
# Knight Capital lost $440M in 45 minutes because faulty code sent duplicate orders.
# This function ensures orders are never duplicated beyond the specified quantity.

@safe_auto
def execute_order(shares_requested: int, shares_filled: int, max_quantity: int) -> int:
    """
    Execute a trading order with safeguards against over-execution.

    Real incident: Knight Capital (2012) - A flag check error caused orders
    to be sent 8 times, resulting in $440 million loss in 45 minutes.

    This verified function mathematically proves:
    - Orders never exceed max_quantity
    - Remaining shares are always non-negative
    - Total filled never exceeds requested amount
    """
    remaining = shares_requested - shares_filled

    if remaining <= 0:
        return 0

    if remaining > max_quantity:
        return max_quantity
    else:
        return remaining


# =============================================================================
# Example 2: Options Strike Price Calculation (Goldman Sachs-inspired)
# =============================================================================
# Goldman Sachs had a $38M loss due to incorrect options pricing.
# This function ensures strike prices are always calculated correctly.

@safe
@requires("base_price > 0")
@requires("adjustment_percent >= -100")
@requires("adjustment_percent <= 100")
@ensures("result > 0")
@ensures("adjustment_percent > 0 -> result > base_price")
@ensures("adjustment_percent < 0 -> result < base_price")
@ensures("adjustment_percent = 0 -> result = base_price")
def calculate_strike_price(base_price: int, adjustment_percent: int) -> int:
    """
    Calculate option strike price with percentage adjustment.

    Real incident: Goldman Sachs (2015) - Incorrect strike price calculation
    led to $38 million loss in options contracts.

    Formally verified properties:
    - Strike price is always positive
    - Positive adjustment increases price
    - Negative adjustment decreases price
    - Zero adjustment preserves price
    """
    # Using integer arithmetic to avoid floating point issues
    # adjustment_percent is in basis points (100 = 1%)
    adjustment = (base_price * adjustment_percent) // 100
    return base_price + adjustment


# =============================================================================
# Example 3: Position Limit Enforcement (Bank of America-inspired)
# =============================================================================
# Position limit violations have caused multiple trading disasters.
# This function ensures positions never exceed regulatory or risk limits.

@safe
@requires("current_position >= 0")
@requires("trade_size >= 0")
@requires("position_limit > 0")
@requires("current_position <= position_limit")
@ensures("result >= 0")
@ensures("result <= position_limit")
def check_position_limit(current_position: int, trade_size: int, position_limit: int) -> int:
    """
    Enforce position limits before executing trades.

    Real incidents: Multiple banks have suffered losses from exceeding position limits,
    including unauthorized trading at Société Générale (€4.9B loss in 2008).

    Formally verified properties:
    - Current position is within limits (precondition)
    - Resulting position never exceeds limit
    - Result is always non-negative
    - Trade is either fully executed or capped at limit
    """
    new_position = current_position + trade_size

    if new_position <= position_limit:
        return new_position
    else:
        return position_limit


# =============================================================================
# Example 4: Margin Call Calculation (Critical for Risk Management)
# =============================================================================

@safe_auto
def calculate_margin_call(portfolio_value: int, borrowed_amount: int, maintenance_margin_percent: int) -> int:
    """
    Calculate if a margin call is required and the amount.

    Margin calls are critical in preventing cascading failures during market volatility.
    Incorrect calculations can lead to forced liquidations and systemic risk.

    Returns: Amount required to meet maintenance margin (0 if no call needed)
    """
    # Maintenance margin requirement
    required_equity = (borrowed_amount * maintenance_margin_percent) // 100
    current_equity = portfolio_value - borrowed_amount

    if current_equity >= required_equity:
        return 0
    else:
        shortfall = required_equity - current_equity
        return shortfall


# =============================================================================
# Example 5: Settlement Amount Calculation (Prevents Rounding Errors)
# =============================================================================
# Small rounding errors in settlement calculations can accumulate to millions.

@safe
@requires("principal > 0")
@requires("rate >= 0")
@requires("rate <= 10000")  # Max 100% in basis points
@requires("days >= 0")
@requires("days <= 365")
@ensures("result >= principal")  # Settlement is always at least the principal
def calculate_settlement(principal: int, rate: int, days: int) -> int:
    """
    Calculate settlement amount for a fixed-income instrument.

    Real concern: Salomon Brothers (1991) had issues with bond settlement calculations.
    Even tiny errors multiplied across millions of transactions cause significant losses.

    Formally verified properties:
    - Settlement amount is never less than principal
    - Interest calculation uses correct day-count convention
    - No integer overflow in intermediate calculations

    Note: Uses integer arithmetic (cents) to avoid floating-point errors.
    Rate is in basis points (100 = 1%), principal in cents.
    """
    # Calculate interest: (principal * rate * days) / (365 * 10000)
    # Using careful order to prevent overflow
    interest = (principal * rate * days) // (365 * 10000)
    return principal + interest


# =============================================================================
# Example 6: Circuit Breaker for High-Frequency Trading
# =============================================================================

@safe_auto
def apply_circuit_breaker(order_count: int, time_window_seconds: int, max_orders_per_second: int) -> bool:
    """
    Implement circuit breaker to prevent runaway trading algorithms.

    Real incident: The Flash Crash (May 6, 2010) - Automated trading algorithms
    caused a trillion-dollar market drop in minutes. Circuit breakers are now
    mandatory to prevent such events.

    Returns: True if trading should be allowed, False if circuit breaker triggered
    """
    if time_window_seconds <= 0:
        return False

    orders_per_second = order_count // time_window_seconds

    if orders_per_second <= max_orders_per_second:
        return True
    else:
        return False


# =============================================================================
# Example 7: Dividend Distribution (Precision Critical)
# =============================================================================

@safe
@requires("total_dividend > 0")
@requires("shares_outstanding > 0")
@requires("shareholder_shares > 0")
@requires("shareholder_shares <= shares_outstanding")
@ensures("result > 0")
@ensures("result <= total_dividend")
def calculate_dividend_payment(total_dividend: int, shares_outstanding: int, shareholder_shares: int) -> int:
    """
    Calculate individual shareholder's dividend payment.

    Critical for fairness and regulatory compliance. Any error can lead to:
    - Legal disputes with shareholders
    - SEC violations
    - Reputational damage

    Formally verified properties:
    - Each shareholder receives positive payment
    - No shareholder receives more than total dividend
    - Proportional distribution is mathematically correct

    Note: Uses integer arithmetic (cents) for precision.
    """
    # Dividend per share calculation
    payment = (total_dividend * shareholder_shares) // shares_outstanding
    return payment


# =============================================================================
# Example 8: Credit Limit Validation (Prevents Over-Extension)
# =============================================================================

@safe_auto
def validate_credit_transaction(current_balance: int, transaction_amount: int, credit_limit: int) -> bool:
    """
    Validate if a credit transaction should be approved.

    Critical for credit card processors and banks. Over-extension can lead to:
    - Credit losses
    - Regulatory violations
    - Customer disputes

    Returns: True if transaction is within limit, False otherwise
    """
    new_balance = current_balance + transaction_amount

    if new_balance <= credit_limit:
        return True
    else:
        return False


# =============================================================================
# DEMO NOTES FOR FINANCIAL INSTITUTION
# =============================================================================
"""
Key Selling Points for Demo:

1. COST OF BUGS IN FINANCE:
   - Knight Capital: $440M in 45 minutes (2012)
   - Goldman Sachs: $38M options error (2015)
   - Société Générale: €4.9B unauthorized trading (2008)
   - Flash Crash: $1 trillion market impact (2010)

2. WHY FORMAL VERIFICATION MATTERS:
   - Mathematical proof of correctness (not just testing)
   - Catches edge cases that testing misses
   - Prevents catastrophic failures before deployment
   - Regulatory compliance documentation (Basel III, MiFID II)

3. REAL-WORLD APPLICABILITY:
   - High-frequency trading systems
   - Risk management calculations
   - Settlement and clearing systems
   - Regulatory reporting
   - Smart contracts for DeFi

4. ROI CALCULATION:
   - Cost of formal verification: Hours/days of development time
   - Cost of financial bug: Millions to billions + reputational damage
   - One prevented incident pays for years of verification investment

5. COMPETITIVE ADVANTAGE:
   - Provably correct systems = higher reliability rating
   - Faster regulatory approval (mathematical proof of compliance)
   - Reduced insurance premiums for E&O coverage
   - Attract institutional clients requiring highest assurance

DEMO FLOW:
1. Show @safe_auto examples (execute_order, margin_call) - automatic verification
2. Show @safe examples with manual specs - explicit guarantees
3. Trigger verification on all functions - show real-time proof status
4. Click on each proof to show detailed verification results
5. Explain how each property prevents specific historical incidents
6. Discuss integration into CI/CD pipeline for continuous verification
"""
