import asyncio
import hashlib
import re
from datetime import datetime
from pathlib import Path

import aiofiles
from loguru import logger


class LogsSplitter:
    """A class for splitting large log files into smaller chunks based on start/end regex patterns."""

    def __init__(
        self,
        output_dir: Path,
        max_patterns_per_file: int,
        start_pattern: str,
        end_pattern: str,
    ) -> None:
        """
        Initialize the LogsSplitter.

        Args:
            output_dir: Directory where split logs will be saved.
            max_patterns_per_file: Max patterns allowed in a single split file.
            start_pattern: Regex pattern indicating the start of a log section.
            end_pattern: Regex pattern indicating the end of a log section.

        Raises:
            ValueError: If max_patterns_per_file is less than or equal to 0.

        """
        if max_patterns_per_file <= 0:
            raise ValueError("Max patterns per file must be a positive number!")

        self.output_dir = output_dir
        self.max_patterns_per_file = max_patterns_per_file
        self.pattern_regex = re.compile(
            f"({start_pattern}.*?{end_pattern})",
            re.DOTALL,
        )

    async def _calculate_file_hash(self, file_path: Path, block_size: int = 65536) -> str:
        """
        Calculate the SHA256 hash of a file.

        Args:
            file_path: Path to the file.
            block_size: Size of chunks to read.

        Returns:
            The SHA256 hash string, or "hash_error" if reading fails.

        """
        sha256 = hashlib.sha256()
        try:
            async with aiofiles.open(file_path, "rb") as f:
                while chunk := await f.read(block_size):
                    sha256.update(chunk)
            return sha256.hexdigest()
        except OSError as e:
            logger.error(f"Could not read file `{file_path}` for hashing: {e!s}")
            return "hash_error"

    async def _find_patterns(self, content: str) -> list[str]:
        """
        Find matching log patterns within the content using regex.

        Args:
            content: The entire string content of the log file.

        Returns:
            A list of pattern strings found.

        """
        loop = asyncio.get_running_loop()
        matches = list(await loop.run_in_executor(None, self.pattern_regex.finditer, content))

        if not matches:
            return []

        all_patterns = []
        for i, match in enumerate(matches):
            match_start, match_end = match.span()

            true_start = content.rfind("\n", 0, match_start) + 1

            if i > 0:
                previous_match_end = matches[i - 1].end()
                inter_content = content[previous_match_end:true_start]
                if all_patterns:
                    all_patterns[-1] += inter_content

            pattern_content = content[true_start:match_end]
            all_patterns.append(pattern_content)

        if all_patterns:
            first_match_start_pos = content.rfind("\n", 0, matches[0].start()) + 1
            orphan_logs = content[:first_match_start_pos]
            all_patterns[0] = orphan_logs + all_patterns[0]

        return [p.strip() for p in all_patterns if p.strip()]

    async def _write_chunk(self, output_path: Path, pattern_chunk: list[str]) -> None:
        """
        Write a chunk of patterns to a file.

        Args:
            output_path: Path to write the chunk to.
            pattern_chunk: List of patterns to write.

        """
        content_to_write = "\n\n---\n\n".join(pattern_chunk)
        try:
            async with aiofiles.open(output_path, "w", encoding="utf-8") as f:
                await f.write(content_to_write)
            logger.success(f"Wrote `{len(pattern_chunk)}` patterns to `{output_path}`")
        except OSError as e:
            logger.error(f"Error writing to file `{output_path}`: {e!s}")

    async def _process_single_file(self, input_file: Path) -> list[Path]:
        """
        Process a single log file by splitting it into smaller chunks.

        Args:
            input_file: Path to the log file.

        Returns:
            A list of output file paths generated.

        """
        logger.info(f"Starting processing for: `{input_file}`")

        file_hash = await self._calculate_file_hash(input_file)
        if "error" in file_hash:
            return []

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        unique_output_dir = self.output_dir / f"{input_file.stem}_{timestamp}"
        unique_output_dir.mkdir(parents=True, exist_ok=True)

        logger.debug(f"[{input_file.name}] Outputting to sub-directory: {unique_output_dir}")

        try:
            async with aiofiles.open(input_file, encoding="utf-8", errors="ignore") as f:
                content = await f.read()
        except (OSError, FileNotFoundError) as e:
            logger.error(f"Could not read file `{input_file}`: {e}")
            return []

        patterns = await self._find_patterns(content)
        if not patterns:
            logger.warning(f"No patterns found in `{input_file}`.")
            return []

        logger.info(f"Found {len(patterns)} patterns in `{input_file}`. Splitting...")

        write_tasks = []
        output_paths = []
        for file_index, i in enumerate(range(0, len(patterns), self.max_patterns_per_file)):
            chunk = patterns[i : i + self.max_patterns_per_file]
            output_path = unique_output_dir / f"{input_file.stem}_{file_hash[:8]}_{file_index + 1}.log"
            output_paths.append(output_path)
            task = self._write_chunk(output_path, chunk)
            write_tasks.append(task)

        if write_tasks:
            await asyncio.gather(*write_tasks)
            logger.success(f"Finished processing `{input_file}`.")

        return output_paths

    async def process_batch(self, input_files: list[Path]) -> list[Path]:
        """
        Process a batch of log files concurrently.

        Args:
            input_files: A list of paths to log files.

        Returns:
            A combined list of all generated output file paths.

        """
        logger.info(f"Initializing batch processing for {len(input_files)} file(s).")
        processing_tasks = [self._process_single_file(file) for file in input_files]
        results = await asyncio.gather(*processing_tasks)
        return [path for sublist in results for path in sublist]
