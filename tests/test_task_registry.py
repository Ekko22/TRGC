import pytest

from lmas_trgc.tasks.registry import get_dataset_spec, list_dataset_names, total_target_main_count


def test_dataset_registry_shape():
    names = list_dataset_names()
    assert len(names) == 11
    assert total_target_main_count() == 104


def test_specific_target_counts():
    assert get_dataset_spec("constraint_miniset").target_main_count == 16
    assert get_dataset_spec("local_mas_safety").target_main_count == 16
    assert get_dataset_spec("gsm8k").target_main_count == 8


def test_bad_dataset_raises():
    with pytest.raises(KeyError):
        get_dataset_spec("bad")
