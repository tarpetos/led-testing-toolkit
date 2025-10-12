import asyncio
import hashlib
import re
from datetime import datetime
from pathlib import Path

import aiofiles
from loguru import logger


class LogsSplitter:
    """
    An asynchronous, parallel batch processor for splitting log files based on patterns.

    This class is designed to be instantiated once with a configuration and then
    used to process multiple log files concurrently.
    """

    def __init__(
        self,
        output_dir: Path,
        max_patterns_per_file: int,
        start_pattern: str,
        end_pattern: str,
    ) -> None:
        if max_patterns_per_file <= 0:
            raise ValueError("Max patterns per file must be a positive number.")

        self.output_dir = output_dir
        self.max_patterns_per_file = max_patterns_per_file
        self.pattern_regex = re.compile(
            f"(?:^.*?{start_pattern}.*?$.*?^.*?{end_pattern}.*?$)",
            re.DOTALL | re.MULTILINE,
        )

    async def _calculate_file_hash(self, file_path: Path, block_size: int = 65536) -> str:
        """
        Asynchronously calculates the SHA256 hash of a file.

        Args:
            file_path (Path): The path to the file to be hashed.
            block_size (int): The size of chunks to read from the file.

        Returns:
            str: The hexadecimal representation of the file's SHA256 hash.

        """
        sha256 = hashlib.sha256()
        try:
            async with aiofiles.open(file_path, "rb") as f:
                while chunk := await f.read(block_size):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except OSError as e:
            logger.error(f"Could not read file {file_path} for hashing: {e}")
            return "hash_error"

    async def _find_patterns(self, content: str) -> list[str]:
        """
        Finds all pattern blocks in the given text content using regex.

        Args:
            content (str): The string content of a log file.

        Returns:
            list[str]: A list of all non-overlapping pattern blocks found in the content.

        """
        loop = asyncio.get_running_loop()
        matches_iterator = await loop.run_in_executor(None, self.pattern_regex.finditer, content)
        return [match.group(0) for match in matches_iterator]

    async def _write_chunk(self, output_path: Path, pattern_chunk: list[str]) -> None:
        """
        Writes a single chunk of patterns to a destination file.

        Args:
            output_path (Path): The full path of the file to be written.
            pattern_chunk (list[str]): A list of pattern strings to write.

        """
        content_to_write = "\n\n---\n\n".join(pattern_chunk)
        try:
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(content_to_write)
            logger.success(f"Wrote {len(pattern_chunk)} patterns to {output_path}")
        except OSError as e:
            logger.error(f"Error writing to file {output_path}: {e}")

    async def _process_single_file(self, input_file: Path) -> None:
        """
        The core processing logic for one log file.

        This coroutine handles reading, hashing, pattern matching, and orchestrating
        the asynchronous writing of split files for a single source file.

        Args:
            input_file (Path): The path to the log file to process.

        """
        logger.info(f"Starting processing for: '{input_file}'")

        file_hash = await self._calculate_file_hash(input_file)
        if "error" in file_hash:
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        unique_output_dir = self.output_dir / f"{input_file.stem}_{timestamp}"
        unique_output_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"[{input_file.name}] Outputting to sub-directory: {unique_output_dir}")

        try:
            async with aiofiles.open(input_file, encoding="utf-8") as f:
                content = await f.read()
        except (OSError, FileNotFoundError) as e:
            logger.error(f"Could not read file '{input_file}': {e}")
            return

        patterns = await self._find_patterns(content)
        if not patterns:
            logger.warning(f"No patterns found in '{input_file}'.")
            return

        logger.info(f"Found {len(patterns)} patterns in '{input_file}'. Splitting...")

        write_tasks = []
        for file_index, i in enumerate(range(0, len(patterns), self.max_patterns_per_file)):
            chunk = patterns[i : i + self.max_patterns_per_file]
            output_path = unique_output_dir / f"{input_file.stem}_{file_hash[:8]}_{file_index + 1}.log"
            task = self._write_chunk(output_path, chunk)
            write_tasks.append(task)

        if write_tasks:
            await asyncio.gather(*write_tasks)
            logger.success(f"Finished processing '{input_file}'.")

    async def process_batch(self, input_files: list[Path]) -> None:
        """
        Concurrently processes a list of log files using the instance's configuration.

        Args:
            input_files (list[Path]): A list of Path objects pointing to the log files to process.

        """
        logger.info(f"Initializing batch processing for {len(input_files)} file(s).")
        processing_tasks = [self._process_single_file(file) for file in input_files]
        await asyncio.gather(*processing_tasks)
