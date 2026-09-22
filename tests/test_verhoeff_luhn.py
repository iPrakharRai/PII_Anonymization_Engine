"""
Unit tests for Verhoeff (D5 Dihedral Group) and Luhn (Mod-10) checksum algorithms.
Verifies error detection capabilities for Indian national identification numbers.
"""
import pytest
from backend.app.utils.verhoeff import generate_verhoeff, validate_verhoeff
from backend.app.utils.luhn import calculate_luhn, validate_luhn


class TestVerhoeffAlgorithm:
    """Test suite for Verhoeff dihedral group D_5 checksum validation."""

    def test_verhoeff_checksum_generation_and_validation(self):
        # Generate checksum for arbitrary 11-digit prefixes
        test_prefixes = ["98765432109", "12345678901", "54321098765", "23456789012"]
        for prefix in test_prefixes:
            checksum_char = generate_verhoeff(prefix)
            assert checksum_char is not None
            full_aadhaar = prefix + checksum_char
            assert len(full_aadhaar) == 12
            assert validate_verhoeff(full_aadhaar) is True

    def test_verhoeff_detects_single_digit_substitution(self):
        prefix = "99887766554"
        checksum = generate_verhoeff(prefix)
        valid_aadhaar = prefix + checksum
        assert validate_verhoeff(valid_aadhaar) is True

        # Mutate any single digit
        for i in range(12):
            orig_char = valid_aadhaar[i]
            mutated_char = str((int(orig_char) + 1) % 10)
            mutated_aadhaar = valid_aadhaar[:i] + mutated_char + valid_aadhaar[i+1:]
            assert validate_verhoeff(mutated_aadhaar) is False

    def test_verhoeff_detects_adjacent_transpositions(self):
        prefix = "87654321098"
        checksum = generate_verhoeff(prefix)
        valid_aadhaar = prefix + checksum
        assert validate_verhoeff(valid_aadhaar) is True

        # Transpose adjacent digits (unless they are identical)
        for i in range(11):
            if valid_aadhaar[i] != valid_aadhaar[i+1]:
                transposed = (
                    valid_aadhaar[:i]
                    + valid_aadhaar[i+1]
                    + valid_aadhaar[i]
                    + valid_aadhaar[i+2:]
                )
                assert validate_verhoeff(transposed) is False

    def test_verhoeff_invalid_inputs(self):
        assert validate_verhoeff("") is False
        assert validate_verhoeff("abc") is False


class TestLuhnAlgorithm:
    """Test suite for Mod-10 Luhn checksum validation."""

    def test_luhn_valid_numbers(self):
        # Standard known valid Luhn numbers
        valid_numbers = [
            "49927398716",
            "79927398713",
            "1234567812345670",
        ]
        for num in valid_numbers:
            assert validate_luhn(num) is True

    def test_luhn_detects_single_digit_mutation(self):
        valid_number = "79927398713"
        assert validate_luhn(valid_number) is True

        # Mutate the last digit
        mutated = valid_number[:-1] + "4"
        assert validate_luhn(mutated) is False

    def test_luhn_invalid_inputs(self):
        assert validate_luhn("") is False
        assert validate_luhn("1") is False
        assert validate_luhn("abc") is False
