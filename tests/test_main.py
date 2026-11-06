"""Unit tests for the main entry point."""

from src.main import PROJECT_NAME, SETUP_MESSAGE, get_project_status, main


def test_get_project_status():
    """Verify that get_project_status returns expected project metadata."""
    status_info = get_project_status()
    assert status_info["project_name"] == PROJECT_NAME
    assert status_info["status"] == SETUP_MESSAGE
    assert "ready" in status_info["status"].lower()


def test_main_output(capsys):
    """Verify that main() prints the project name and confirmation message."""
    main()
    captured = capsys.readouterr()
    assert PROJECT_NAME in captured.out
    assert SETUP_MESSAGE in captured.out
