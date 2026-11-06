"""Main entry point for Project.

AI-Powered Discovery Engine for First-Time Mutual Fund SIP Retention & Churn.
"""

PROJECT_NAME = "Project"
SETUP_MESSAGE = "Project setup is ready and initialized successfully."


def get_project_status() -> dict[str, str]:
    """Return basic project status information."""
    return {
        "project_name": PROJECT_NAME,
        "status": SETUP_MESSAGE,
    }


def main() -> None:
    """Print project name and confirmation message."""
    info = get_project_status()
    print("=" * 60)
    print(f"Project Name : {info['project_name']}")
    print(f"Status       : {info['status']}")
    print("=" * 60)


if __name__ == "__main__":
    main()
