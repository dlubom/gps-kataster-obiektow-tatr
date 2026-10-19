"""Temporary probe for the required CI merge check."""


def test_required_ci_merge_gate_probe() -> None:
    expected_ci_success = False
    assert expected_ci_success, "Intentional failure to verify required CI blocks merges."
