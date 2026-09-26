"""Indian-format currency and number helpers used by the templates."""


def _to_float(value, default=0.0):
    try:
        if value is None:
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def inr(value, decimals=0):
    """1234567 -> '12,34,567' (Indian grouping), prefixed by the caller."""
    n = _to_float(value)
    negative = n < 0
    n = abs(n)

    whole = int(n)
    frac = ""
    if decimals > 0:
        frac = f"{n - whole:.{decimals}f}"[1:]

    s = str(whole)
    if len(s) > 3:
        last3 = s[-3:]
        rest = s[:-3]
        parts = []
        while len(rest) > 2:
            parts.insert(0, rest[-2:])
            rest = rest[:-2]
        if rest:
            parts.insert(0, rest)
        s = ",".join(parts + [last3])

    return ("-" if negative else "") + s + frac


def inr_short(value):
    """Compact Indian notation: 1.2 Cr / 45.0 L / 12.5 K."""
    n = _to_float(value)
    sign = "-" if n < 0 else ""
    n = abs(n)
    if n >= 1_00_00_000:
        return f"{sign}{n / 1_00_00_000:.2f} Cr"
    if n >= 1_00_000:
        return f"{sign}{n / 1_00_000:.2f} L"
    if n >= 1_000:
        return f"{sign}{n / 1_000:.1f} K"
    return f"{sign}{n:,.0f}"


def compact_number(value):
    n = _to_float(value)
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return f"{n:,.0f}"
