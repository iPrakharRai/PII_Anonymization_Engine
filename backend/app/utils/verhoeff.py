"""
Verhoeff Checksum Algorithm Implementation.
Used for validating 12-digit Indian Aadhaar Numbers (UIDAI).
Detects 100% of single-digit substitution errors and 95.3% of adjacent transposition errors.
"""

# The multiplication table (d table) based on dihedral group D5
_MULTIPLICATION_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 2, 3, 4, 0, 6, 7, 8, 9, 5],
    [2, 3, 4, 0, 1, 7, 8, 9, 5, 6],
    [3, 4, 0, 1, 2, 8, 9, 5, 6, 7],
    [4, 0, 1, 2, 3, 9, 5, 6, 7, 8],
    [5, 9, 8, 7, 6, 0, 4, 3, 2, 1],
    [6, 5, 9, 8, 7, 1, 0, 4, 3, 2],
    [7, 6, 5, 9, 8, 2, 1, 0, 4, 3],
    [8, 7, 6, 5, 9, 3, 2, 1, 0, 4],
    [9, 8, 7, 6, 5, 4, 3, 2, 1, 0]
]

# The permutation table (p table)
_PERMUTATION_TABLE = [
    [0, 1, 2, 3, 4, 5, 6, 7, 8, 9],
    [1, 5, 7, 6, 2, 8, 3, 0, 9, 4],
    [5, 8, 0, 3, 7, 9, 6, 1, 4, 2],
    [8, 9, 1, 6, 0, 4, 3, 5, 2, 7],
    [9, 4, 5, 3, 1, 2, 6, 8, 7, 0],
    [4, 2, 8, 6, 5, 7, 3, 9, 0, 1],
    [2, 7, 9, 3, 8, 0, 6, 4, 1, 5],
    [7, 0, 4, 6, 9, 1, 3, 2, 5, 8]
]

# The inverse table (inv table)
_INVERSE_TABLE = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]


def generate_verhoeff(num_str: str) -> str:
    """Generates the Verhoeff check digit for a given numerical string."""
    clean_digits = [int(c) for c in num_str if c.isdigit()]
    c = 0
    reversed_digits = list(reversed(clean_digits))
    for i, digit in enumerate(reversed_digits):
        c = _MULTIPLICATION_TABLE[c][_PERMUTATION_TABLE[(i + 1) % 8][digit]]
    return str(_INVERSE_TABLE[c])


def validate_verhoeff(num_str: str) -> bool:
    """
    Validates a number string using the Verhoeff algorithm.
    Returns True if valid (including check digit), False otherwise.
    """
    digits = [int(c) for c in num_str if c.isdigit()]
    if not digits:
        return False
    c = 0
    reversed_digits = list(reversed(digits))
    for i, digit in enumerate(reversed_digits):
        c = _MULTIPLICATION_TABLE[c][_PERMUTATION_TABLE[i % 8][digit]]
    return c == 0
