import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger

from led_testing_toolkit.utils.logs_splitter import LogsSplitter


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Asynchronously splits one or more log files into smaller chunks based on patterns.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    parser.add_argument(
        "input_files",
        type=Path,
        nargs="+",
        help="Path(s) to the source log file(s) to be processed in parallel.",
    )

    parser.add_argument(
        "-mp",
        "--max-patterns",
        type=int,
        default=1,
        help="The maximum number of patterns to write into each output file.",
    )

    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        default=Path("./split_logs"),
        help="The directory to save the split log files.\n(default: ./split_logs)",
    )

    parser.add_argument(
        "--start-pattern",
        type=str,
        default=r"LED(\d+)=\w+",
        help='Regex pattern that marks the beginning of a log block.\n(default: "LED(\\d+)=\\w+")',
    )

    parser.add_argument(
        "--end-pattern",
        type=str,
        default=r"Indication absence time exceeded limit: (\d+.\d+) seconds|--- END INDICATION PATTERN \w+ ---",
        help="Regex pattern that marks the end of a log block.\n(default: "
        '"Indication absence time exceeded limit: (\\d+.\\d+) seconds|--- END INDICATION PATTERN \\w+ ---")',
    )

    args = parser.parse_args()

    logger.info(f"Log splitter configured. Processing {len(args.input_files)} file(s).")

    try:
        splitter = LogsSplitter(
            output_dir=args.output_dir,
            max_patterns_per_file=args.max_patterns,
            start_pattern=args.start_pattern,
            end_pattern=args.end_pattern,
        )

        await splitter.process_batch(args.input_files)
    except ValueError as e:
        logger.critical(f"Configuration error: {e}")
        sys.exit(1)
    except Exception:
        logger.exception("A critical error occurred during batch processing.")
        sys.exit(1)

    logger.success("Batch processing complete.")


if __name__ == "__main__":
    asyncio.run(main())
