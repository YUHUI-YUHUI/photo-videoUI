#!/usr/bin/env python3
"""
PAVUI - AI Video Generation Workflow Platform

Main application entry point.
"""

import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def main():
    """Main entry point"""
    from src.ui import create_app

    app = create_app()
    app.run()


if __name__ == "__main__":
    main()
