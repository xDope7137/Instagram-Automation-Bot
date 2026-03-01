from pathlib import Path

from GramAddict.core.interaction import _load_and_clean_txt_file

_THIS_DIR = Path(__file__).parent


def test_load_txt_ok(mocker):
    mocker.patch(
        "GramAddict.core.interaction.os.path.join",
        return_value=str(_THIS_DIR / "txt" / "txt_ok.txt"),
    )
    message = _load_and_clean_txt_file("test_user", "txt_filename")
    assert message is not None
    assert message == [
        "Hello, test_user! How are you today?",
        "Hello everyone!",
        "Goodbye, test_user! Have a great day!",
    ]


def test_load_txt_empty(mocker):
    mocker.patch(
        "GramAddict.core.interaction.os.path.join",
        return_value=str(_THIS_DIR / "txt" / "txt_empty.txt"),
    )
    message = _load_and_clean_txt_file("test_user", "txt_filename")
    assert message is None


def test_load_txt_not_exists(mocker):
    mocker.patch(
        "GramAddict.core.interaction.os.path.join",
        return_value=str(_THIS_DIR / "txt" / "txt_not_exists.txt"),
    )
    message = _load_and_clean_txt_file("test_user", "txt_filename")
    assert message is None
