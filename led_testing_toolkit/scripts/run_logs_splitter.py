import argparse
import asyncio
from pathlib import Path

from loguru import logger

from led_testing_toolkit.utils.logs_splitter import LogsSplitter


async def split_logs_main(
    input_files: list[Path], max_patterns: int, output_dir: Path, start_pattern: str, end_pattern: str
) -> list[Path]:
    logger.info(f"Log splitter configured. Processing {len(input_files)} file(s).")

    try:
        splitter = LogsSplitter(
            output_dir=Path(output_dir),
            max_patterns_per_file=max_patterns,
            start_pattern=start_pattern,
            end_pattern=end_pattern,
        )

        processed_files = await splitter.process_batch(input_files)
    except ValueError as e:
        logger.critical(f"Configuration error: {e}")
        raise
    except Exception:
        logger.exception("A critical error occurred during batch processing.")
        raise

    logger.success("Batch processing complete.")
    return processed_files


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
        default=r"(?:--- START INDICATION PATTERN \w+ ---|LED\d+=)",
        help="Regex pattern that marks the beginning of a log block.",
    )

    parser.add_argument(
        "--end-pattern",
        type=str,
        default=r"(?:Indication absence time exceeded limit|"
        r"Expected pattern \w+ is detected!|--- END INDICATION PATTERN \w+ ---)",
        help="Regex pattern that marks the end of a log block.",
    )

    args = parser.parse_args()

    await split_logs_main(
        input_files=args.input_files,
        max_patterns=args.max_patterns,
        output_dir=args.output_dir,
        start_pattern=args.start_pattern,
        end_pattern=args.end_pattern,
    )


if __name__ == "__main__":
    asyncio.run(main())
