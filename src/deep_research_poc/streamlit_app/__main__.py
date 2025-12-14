"""Entry point for running the Streamlit app.

Run with: python -m deep_research_poc.streamlit_app
Or: streamlit run src/deep_research_poc/streamlit_app/app.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def main() -> None:
    """Run the Streamlit application."""
    # Get the path to the app.py file
    app_path = Path(__file__).parent / "app.py"

    # Run streamlit with the app
    subprocess.run(
        [
            sys.executable,
            "-m",
            "streamlit",
            "run",
            str(app_path),
            "--server.headless",
            "true",
        ],
        check=True,
    )


if __name__ == "__main__":
    main()
