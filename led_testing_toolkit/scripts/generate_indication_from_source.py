import argparse
import asyncio
from pathlib import Path

from loguru import logger

from led_testing_toolkit.led_simulation_runner import SimulationRunner


async def generate_indication_from_source_main(args: argparse.Namespace) -> list[str]:
    runner = SimulationRunner(args, logger)
    return await runner.run()


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generator for LED indication simulations from existing data.",
        formatter_class=argparse.RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="source_type", required=True)

    log_parser = subparsers.add_parser("log", help="Use a log file as the source.")
    log_parser.add_argument("filepath", type=Path, help="Path to the log file.")

    db_parser = subparsers.add_parser("db", help="Use a database as the source.")
    db_parser.add_argument(
        "collection",
        help="Name of the collection (e.g., 'FD-CALL' or 'FD-ETALONS').",
    )
    db_parser.add_argument("-pn", "--pattern-name", help="Pattern name (_id) to use (required for etalon collections).")
    db_parser.add_argument(
        "-pa",
        "--process-all",
        action="store_true",
        help="Process all records in a measured collection instead of one random record.",
    )

    for p in [log_parser, db_parser]:
        p.add_argument(
            "-stb",
            "--save-to-db",
            help="Save the generated pattern to the specified MongoDB collection (e.g., 'DEVICE-MEASURED').",
        )
        p.add_argument(
            "-o",
            "--output-dir",
            default="generated_logs",
            type=Path,
            help="Directory to save generated logs (used if --save-to-db is not specified).",
        )
        p.add_argument(
            "-c",
            "--count",
            type=int,
            default=1,
            help="Number of fictitious records to generate per source pattern.",
        )
        p.add_argument("-n", "--noise", type=float, default=3.0, help="Sensor noise level.")
        p.add_argument("-l", "--lag", type=float, default=0.4, help="Sensor reaction lag (0.0-1.0).")
        p.add_argument(
            "-rc",
            "--reporting-chance",
            type=float,
            default=0.85,
            help="Probability of reporting a change (0.0-1.0).",
        )
        p.add_argument("-i", "--interval", default="15-40", help="Random logging interval in ms.")
        p.add_argument("-m", "--mode", choices=["simulate", "instant"], default="instant", help="Execution mode.")

    args = parser.parse_args()

    await generate_indication_from_source_main(args)


if __name__ == "__main__":
    asyncio.run(main())
