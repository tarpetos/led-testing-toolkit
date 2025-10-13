import argparse
import contextlib
import io
import tempfile
import zipfile
from pathlib import Path

from fastapi import UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from api.services.log_parser_service import log_parser_service
from led_testing_toolkit.scripts.generate_etalons import generate_etalons_main
from led_testing_toolkit.scripts.generate_indication_from_parameters import (
    generate_indication_from_parameters_main,
)
from led_testing_toolkit.scripts.generate_indication_from_source import (
    generate_indication_from_source_main,
)
from led_testing_toolkit.scripts.run_logs_splitter import split_logs_main
from led_testing_toolkit.utils.data_processing import read_measured
from led_testing_toolkit.utils.make_indication_comparison import (
    make_indication_comparison_results,
)


class ToolsService:
    async def split_logs(
        self,
        files: list[UploadFile],
        max_patterns: int,
        start_pattern: str,
        end_pattern: str,
    ) -> dict[str, str] | StreamingResponse:
        with tempfile.TemporaryDirectory() as temp_dir:
            input_files = []
            for file in files:
                file_path = Path(temp_dir) / file.filename
                with file_path.open("wb") as buffer:
                    buffer.write(await file.read())
                input_files.append(file_path)

            output_path = Path(temp_dir) / "output"
            output_path.mkdir(exist_ok=True)

            try:
                processed_files = await split_logs_main(
                    input_files=input_files,
                    max_patterns=max_patterns,
                    output_dir=Path(output_path),
                    start_pattern=start_pattern,
                    end_pattern=end_pattern,
                )

                if not processed_files:
                    return {"status": "error", "message": "No patterns found in the log file(s)."}

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for file_path in processed_files:
                        zip_file.write(file_path, Path(file_path).name)

                zip_buffer.seek(0)
                return StreamingResponse(
                    zip_buffer,
                    media_type="application/zip",
                    headers={"Content-Disposition": "attachment; filename=split_logs.zip"},
                )

            except Exception as e:
                return {"status": "error", "message": str(e)}

    async def compare_patterns(
        self, measured_collection: str, measured_record: str, etalon_device: str, etalon_pattern: str
    ) -> dict[str, dict] | dict[str, str]:
        try:
            normalized_measured_data = await read_measured(measured_collection, record_id=measured_record)
            results = await make_indication_comparison_results(
                normalized_measured_data,
                etalon_device,
                etalon_pattern,
            )
        except Exception as e:
            return {"status": "error", "message": str(e)}
        else:
            return {"results": results}

    async def compare_log_pattern(
        self, pattern_index: int, etalon_device: str, etalon_pattern: str
    ) -> dict[str, dict] | dict[str, str]:
        try:
            normalized_measured_data = log_parser_service.get_pattern_by_index(pattern_index)
            if not normalized_measured_data:
                raise ValueError("Invalid pattern index!")  # noqa: TRY301

            results = await make_indication_comparison_results(
                normalized_measured_data,
                etalon_device,
                etalon_pattern,
            )
        except Exception as e:
            return {"status": "error", "message": str(e)}
        else:
            return {"results": results}

    async def generate_etalons(
        self, device_name: str, pattern_name: str
    ) -> dict[str, str | dict[str, dict[str, str]]] | dict[str, str]:
        try:
            log_capture_buffer = io.StringIO()
            with contextlib.redirect_stdout(log_capture_buffer):
                generated_etalons, plots = await generate_etalons_main(device_name, pattern_name, True)
        except Exception as e:
            return {"status": "error", "message": str(e)}
        else:
            return {
                "status": "success",
                "message": f"Pattern `{pattern_name.upper()}` stored in `{generated_etalons[0]}`",
                "plots": plots,
            }

    async def generate_from_parameters(self, **kwargs) -> dict[str, str] | FileResponse | StreamingResponse:
        temp_palette_file_path = None
        try:
            palette_content = kwargs.get("palette")
            if palette_content and (palette_content.strip().startswith("[") or palette_content.strip().startswith("{")):
                with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".json") as tpf:
                    tpf.write(palette_content)
                    kwargs["palette"] = tpf.name
                    temp_palette_file_path = tpf.name

            if kwargs.get("save_to_db"):
                await generate_indication_from_parameters_main(argparse.Namespace(**kwargs))
                return {"status": "success", "message": "Indication generated and saved to the database."}
            with tempfile.NamedTemporaryFile(mode="w", delete=False, suffix=".log") as tof:
                kwargs["output_file"] = tof.name

            output_path_str = await generate_indication_from_parameters_main(argparse.Namespace(**kwargs))

            cleanup_task = BackgroundTask(Path(output_path_str).unlink, missing_ok=True)

            return FileResponse(
                output_path_str, media_type="text/plain", filename=Path(output_path_str).name, background=cleanup_task
            )
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            if temp_palette_file_path:
                Path(temp_palette_file_path).unlink(missing_ok=True)

    async def generate_from_source(self, **kwargs) -> dict[str, str] | StreamingResponse:
        temp_source_file_path = None
        try:
            if kwargs.get("file"):
                source_file = kwargs["file"]
                with tempfile.NamedTemporaryFile(delete=False, suffix=Path(source_file.filename).suffix) as temp_file:
                    temp_file.write(await source_file.read())
                    kwargs["filepath"] = Path(temp_file.name)
                    temp_source_file_path = temp_file.name

            if not kwargs.get("save_to_db"):
                with tempfile.TemporaryDirectory() as temp_dir:
                    kwargs["output_dir"] = Path(temp_dir)

                    output_files = await generate_indication_from_source_main(argparse.Namespace(**kwargs))

                    if not output_files:
                        return {"status": "error", "message": "No files were generated."}

                    zip_buffer = io.BytesIO()
                    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                        for file_path in output_files:
                            zip_file.write(file_path, Path(file_path).name)

                    zip_buffer.seek(0)
                    return StreamingResponse(
                        zip_buffer,
                        media_type="application/zip",
                        headers={"Content-Disposition": "attachment; filename=generated_logs.zip"},
                    )
            else:
                await generate_indication_from_source_main(argparse.Namespace(**kwargs))
                return {"status": "success", "message": "Indication generated and saved to the database."}
        except Exception as e:
            return {"status": "error", "message": str(e)}
        finally:
            if temp_source_file_path:
                Path(temp_source_file_path).unlink(missing_ok=True)


tools_service = ToolsService()
