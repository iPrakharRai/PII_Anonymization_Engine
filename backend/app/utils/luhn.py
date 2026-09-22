"""
Luhn Checksum Algorithm Implementation.
Used for validating credit cards, financial account tokens, and bank identifiers.
"""

def calculate_luhn(number: str) -> int:
    """Calculates the Luhn checksum for a numeric string."""
    clean = [int(c) for c in number if c.isdigit()]
    total = 0
    reverse_digits = clean[::-1]
    for i, digit in enumerate(reverse_digits):
        if i % 2 == 1:
            doubled = digit * 2
            total += doubled - 9 if doubled > 9 else doubled
        else:
            total += digit
    return total


def validate_luhn(number: str) -> bool:
    """Validates whether the string satisfies the Luhn mod 10 check."""
    digits = [c for c in number if c.isdigit()]
    if len(digits) < 2:
        return False
    return calculate_luhn(number) % 10 == 0
