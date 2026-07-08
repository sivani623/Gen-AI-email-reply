"""
End-to-end entrypoint: generate replies -> evaluate them -> write a summary.

Usage:
    python src/run_pipeline.py                 # real run, needs ANTHROPIC_API_KEY
    MOCK_MODE=1 python src/run_pipeline.py      # offline smoke test, no API key needed
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import generator   # noqa: E402
import evaluator   # noqa: E402
import report       # noqa: E402


def main():
    print("=" * 60)
    print("STEP 1/3: generating replies")
    print("=" * 60)
    generator.main()

    print("\n" + "=" * 60)
    print("STEP 2/3: evaluating replies")
    print("=" * 60)
    evaluator.main()

    print("\n" + "=" * 60)
    print("STEP 3/3: writing summary report")
    print("=" * 60)
    report.main()


if __name__ == "__main__":
    main()
