import pytest

from music_upgrader import parsers

@pytest.mark.parametrize(
    "start_value,expected_result",
    [
        ("Zero [Explicit Version]", "Zero"),
        ("Now You've Got Something to Die For [Explicit]", "Now You've Got Something to Die For"),
        ("Forgotten (Lost Angels) (Album Version)", "Forgotten (Lost Angels)"),
        ("Territory (Album version) [Explicit]", "Territory"),
    ],
)
def test_remove_extra_notations(start_value, expected_result):
    assert parsers.remove_extra_notations(start_value) == expected_result


@pytest.mark.parametrize(
    "start_value,expected_result",
    [
        ("Zero [Explicit Version]", "Zero"),
        ("Now You've Got Something to Die For [Explicit]", "Now You've Got Something to Die For"),
        ("Forgotten (Lost Angels) (Album Version)", "Forgotten"),
        ("Territory (Album version) [Explicit]", "Territory (Album version)"),
        ("Territory (Album version) (Explicit Version)", "Territory"),
        ("(Remember) Walking in the Sand", "(Remember) Walking in the Sand"),
    ],
)
def test_remove_last_bracketed_string(start_value, expected_result):
    assert parsers.remove_last_bracketed_string(start_value) == expected_result
