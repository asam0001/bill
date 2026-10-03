from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from typing import Union, Dict, Any

# ==============================================================================
# MediTrack Centralized Financial & Money Utility (Section 4 & 16)
# Eliminates binary floating-point inaccuracies using Python Decimal
# ==============================================================================

# Standard currency quantization (2 decimal places: paise/cents)
CURRENCY_PLACES = Decimal("0.01")
# Unit pricing quantization (4 decimal places for accurate fractional tablet math)
UNIT_PRICE_PLACES = Decimal("0.0001")


def to_decimal(value: Union[int, float, str, Decimal, None]) -> Decimal:
    """
    Safely converts any numeric value or string to a Decimal.
    Safeguards against float conversion representation errors by casting via str.
    """
    if value is None:
        return Decimal("0.00")
    if isinstance(value, Decimal):
        return value
    try:
        # Convert float/int via string to avoid float binary representation artifacts
        val_str = str(value).strip()
        if not val_str:
            return Decimal("0.00")
        return Decimal(val_str)
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.00")


def quantize_money(value: Union[int, float, str, Decimal], places: Decimal = CURRENCY_PLACES) -> Decimal:
    """
    Quantizes a monetary value using standard commercial ROUND_HALF_UP rounding.
    Defaults to 2 decimal places (0.01).
    """
    dec_val = to_decimal(value)
    return dec_val.quantize(places, rounding=ROUND_HALF_UP)


def calculate_tablet_price(strip_price: Union[int, float, str, Decimal], tablets_per_strip: int) -> Decimal:
    """
    Computes per-tablet price with 4 decimal places of precision.
    Formula: strip_price / tablets_per_strip
    """
    t_count = max(1, int(tablets_per_strip))
    dec_strip_price = to_decimal(strip_price)
    return (dec_strip_price / Decimal(str(t_count))).quantize(UNIT_PRICE_PLACES, rounding=ROUND_HALF_UP)


def calculate_discount(gross_amount: Union[int, float, str, Decimal], discount_percent: Union[int, float, str, Decimal]) -> Decimal:
    """
    Computes discount amount: gross_amount * (discount_percent / 100).
    Bounded between 0.00 and gross_amount.
    """
    gross = quantize_money(gross_amount)
    pct = to_decimal(discount_percent)
    
    if pct <= Decimal("0.0"):
        return Decimal("0.00")
    if pct >= Decimal("100.0"):
        return gross
        
    discount = (gross * pct / Decimal("100.0")).quantize(CURRENCY_PLACES, rounding=ROUND_HALF_UP)
    return min(gross, discount)


def calculate_tax(net_amount: Union[int, float, str, Decimal], gst_percent: Union[int, float, str, Decimal]) -> Dict[str, Decimal]:
    """
    Computes taxable base and GST tax breakdown from a tax-inclusive net amount.
    Formula:
        taxable_value = net_amount / (1 + (gst_rate / 100))
        gst_amount = net_amount - taxable_value
    Returns:
        {'taxable_amount': Decimal, 'tax_amount': Decimal, 'cgst': Decimal, 'sgst': Decimal}
    """
    net = quantize_money(net_amount)
    rate = to_decimal(gst_percent)

    if rate <= Decimal("0.0"):
        return {
            "taxable_amount": net,
            "tax_amount": Decimal("0.00"),
            "cgst": Decimal("0.00"),
            "sgst": Decimal("0.00")
        }

    divisor = Decimal("1.0") + (rate / Decimal("100.0"))
    taxable = (net / divisor).quantize(CURRENCY_PLACES, rounding=ROUND_HALF_UP)
    tax_total = net - taxable
    
    half_tax = (tax_total / Decimal("2.0")).quantize(CURRENCY_PLACES, rounding=ROUND_HALF_UP)
    cgst = half_tax
    sgst = tax_total - cgst  # Ensures cgst + sgst strictly equals tax_total

    return {
        "taxable_amount": taxable,
        "tax_amount": tax_total,
        "cgst": cgst,
        "sgst": sgst
    }


def calculate_line_item(
    quantity_tablets: int,
    price_per_tablet: Union[int, float, str, Decimal],
    discount_percent: Union[int, float, str, Decimal] = 0.0,
    cost_per_tablet: Union[int, float, str, Decimal] = 0.0,
    gst_percent: Union[int, float, str, Decimal] = 12.0
) -> Dict[str, Any]:
    """
    Computes complete financial breakdown for a single bill line item.
    Returns exact Decimals and convenient float equivalents for SQLite storage.
    """
    qty = Decimal(str(max(0, int(quantity_tablets))))
    selling_price = to_decimal(price_per_tablet)
    cost_price = to_decimal(cost_per_tablet)

    gross = quantize_money(qty * selling_price)
    discount_amount = calculate_discount(gross, discount_percent)
    net_subtotal = gross - discount_amount
    cost_total = quantize_money(qty * cost_price)
    profit = quantize_money(net_subtotal - cost_total)

    tax_info = calculate_tax(net_subtotal, gst_percent)

    return {
        "quantity": int(quantity_tablets),
        "gross": gross,
        "discount_amount": discount_amount,
        "subtotal": net_subtotal,
        "cost": cost_total,
        "profit": profit,
        "taxable_amount": tax_info["taxable_amount"],
        "tax_amount": tax_info["tax_amount"],
        "cgst": tax_info["cgst"],
        "sgst": tax_info["sgst"],
        # Float conversions for direct SQLite insertion
        "float_gross": float(gross),
        "float_discount_amount": float(discount_amount),
        "float_subtotal": float(net_subtotal),
        "float_cost": float(cost_total),
        "float_profit": float(profit),
        "float_tax_amount": float(tax_info["tax_amount"])
    }


def format_currency(value: Union[int, float, str, Decimal], symbol: str = "₹") -> str:
    """Formats a decimal/float into standard currency display string (e.g. '₹1,240.50')."""
    dec_val = quantize_money(value)
    return f"{symbol}{dec_val:,.2f}"
