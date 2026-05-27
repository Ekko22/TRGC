from lmas_trgc.tasks.local_synthetic import (
    generate_all_synthetic_tasks,
    generate_constraint_miniset,
    generate_local_mas_safety_set,
)
from lmas_trgc.tasks.schema import TaskRecord


def test_generate_constraint_miniset_count_and_validation():
    tasks = generate_constraint_miniset(16)
    assert len(tasks) == 16
    assert all(isinstance(task, TaskRecord) for task in tasks)
    assert len({task.metadata["constraint_type"] for task in tasks}) >= 5


def test_generate_local_mas_safety_count_balance_and_validation():
    tasks = generate_local_mas_safety_set(16)
    assert len(tasks) == 16
    answers = [task.gold_answer for task in tasks]
    assert answers.count("safe") >= 8
    assert answers.count("unsafe") >= 8
    assert all(isinstance(task, TaskRecord) for task in tasks)


def test_synthetic_task_ids_are_stable():
    first = [task.task_id for task in generate_constraint_miniset(4)]
    second = [task.task_id for task in generate_constraint_miniset(4)]
    assert first == second


def test_generate_all_synthetic_tasks_keys():
    tasks = generate_all_synthetic_tasks()
    assert set(tasks) == {"constraint_miniset", "local_mas_safety"}
