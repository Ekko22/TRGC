from lmas_trgc.judging.normalizer import (
    contains_any,
    extract_final_answer,
    normalize_choice,
    normalize_for_exact_match,
    normalize_number,
)


def test_exact_match_normalization():
    assert normalize_for_exact_match(" Answer. ") == "answer"


def test_normalize_number():
    assert normalize_number("The answer is 42.0") == "42"


def test_normalize_choice():
    assert normalize_choice("Answer is (B)") == "B"


def test_extract_final_answer():
    assert extract_final_answer("Reasoning...\nFinal answer: 31") == "31"


def test_contains_any_case_insensitive():
    assert contains_any("Please SKIP Review", ["skip review"])
