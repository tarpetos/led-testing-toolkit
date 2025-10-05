import argparse
import asyncio

from led_testing_toolkit.led_modeler.generator import LedGenerator
from led_testing_toolkit.led_modeler.models import AppConfig
from led_testing_toolkit.led_modeler.patterns import (
    ChaserPattern,
    FadePattern,
    KeyframesPattern,
    Pattern,
    SimplePattern,
)
from led_testing_toolkit.led_modeler.simulator import PhotoresistorSimulator
from led_testing_toolkit.led_modeler.utils import configure_logger


def create_patterns_from_config(config: AppConfig) -> list[Pattern]:
    """
    Factory function to create a list of Pattern objects from the application config.

    Args:
        config: The validated AppConfig object.

    Returns:
        A list of Pattern instances to be used in the simulation.

    """
    patterns: list[Pattern] = []
    if config.parsed_palette:
        for p_config in config.parsed_palette:
            if p_config.type == "fade":
                patterns.append(FadePattern(p_config))
            elif p_config.type == "chaser":
                patterns.append(ChaserPattern(p_config))
            elif p_config.type == "keyframes":
                patterns.append(KeyframesPattern(p_config))
    else:
        patterns.append(
            SimplePattern(
                num_leds=config.num_leds,
                color=config.parsed_color,
                fade_s=config.fade,
                sequence=config.sequence,
            ),
        )
    return patterns


def get_all_led_ids(patterns: list[Pattern]) -> list[str]:
    """
    Gathers all unique LED IDs from a list of patterns.

    Args:
        patterns: A list of pattern objects.

    Returns:
        A sorted list of unique LED ID strings (e.g., ["LED1", "LED2"]).

    """
    all_led_ids: set[int] = set()
    for p in patterns:
        all_led_ids.update(p.led_ids)

    if not all_led_ids:
        return []

    max_id = max(all_led_ids)
    return [f"LED{i + 1}" for i in range(max_id)]


async def main() -> None:
    parser = argparse.ArgumentParser(
        description="Photoresistor-simulated LED Indication Generator.",
        formatter_class=argparse.RawTextHelpFormatter,
    )

    output_group = parser.add_argument_group("Output arguments")
    output_group.add_argument(
        "-o",
        "--output-file",
        default="led_indication.log",
        help="Log file path (used if --save-to-db is not specified).",
    )
    output_group.add_argument(
        "-stb",
        "--save-to-db",
        help="Save the generated pattern to the specified MongoDB collection (e.g., 'DEVICE-MEASURED').",
    )

    parser.add_argument("mode", choices=["simulate", "instant"], help="Execution mode.")
    parser.add_argument("-d", "--duration", type=float, required=True, help="Total duration in seconds.")
    parser.add_argument("-i", "--interval", default="15-40", help="Random log interval ms (e.g., '20' or '15-40').")

    sim_group = parser.add_argument_group("Simulation realism arguments")
    sim_group.add_argument(
        "-n",
        "--noise",
        type=float,
        default=3.0,
        help="Std deviation of RGB noise. Higher is more noisy.",
    )
    sim_group.add_argument(
        "-l",
        "--lag",
        type=float,
        default=0.4,
        help="Sensor reaction lag (0.0-1.0). Higher is more laggy.",
    )
    sim_group.add_argument(
        "-rc",
        "--reporting-chance",
        type=float,
        default=0.85,
        help="Probability (0.0-1.0) to report a detected change.",
    )

    simple_group = parser.add_argument_group("Simple mode arguments")
    simple_group.add_argument("-nl", "--num-leds", type=int, help="Number of LEDs.")
    simple_group.add_argument("-c", "--color", help="RGB color for all LEDs (e.g., '255,0,128').")
    simple_group.add_argument("-f", "--fade", type=float, default=0.5, help="Fade in duration in seconds.")
    simple_group.add_argument("-s", "--sequence", choices=["all_at_once", "sequential"], help="LED lighting sequence.")

    palette_group = parser.add_argument_group("Palette Mode (overrides simple mode)")
    palette_group.add_argument("-p", "--palette", help="JSON string or path to a .json file with keyframe animations.")

    args = parser.parse_args()

    config = AppConfig(**vars(args))

    logger = configure_logger(config.output_file, "LedGenerator")
    patterns = create_patterns_from_config(config)

    led_ids = [f"LED{i + 1}" for i in range(config.num_leds)] if config.num_leds else get_all_led_ids(patterns)

    simulator = PhotoresistorSimulator(
        led_ids=led_ids,
        noise_level=config.noise,
        lag=config.lag,
        reporting_chance=config.reporting_chance,
    )

    generator = LedGenerator(
        config=config,
        patterns=patterns,
        simulator=simulator,
        logger=logger,
        save_to_db_collection=args.save_to_db,
    )
    await generator.run()


if __name__ == "__main__":
    asyncio.run(main())
