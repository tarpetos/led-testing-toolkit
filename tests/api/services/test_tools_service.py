import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi import UploadFile

from api.services.tools_service import ToolsService


@pytest.fixture
def service():
    return ToolsService()


@pytest.mark.asyncio
async def test_split_logs_success(service):
    with patch("api.services.tools_service.split_logs_main", new_callable=AsyncMock) as mock_split:
        mock_split.return_value = ["file1.txt"]

        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.log"
        mock_file.read = AsyncMock(return_value=b"content")

        with patch("api.services.tools_service.zipfile.ZipFile") as mock_zip:
            result = await service.split_logs([mock_file], 1, "start", "end")
            assert hasattr(result, "media_type")
            assert result.media_type == "application/zip"


@pytest.mark.asyncio
async def test_split_logs_no_files(service):
    with patch("api.services.tools_service.split_logs_main", new_callable=AsyncMock) as mock_split:
        mock_split.return_value = []

        result = await service.split_logs([], 1, "start", "end")
        assert result == {"status": "error", "message": "No patterns found in the log file(s)."}


@pytest.mark.asyncio
async def test_split_logs_exception(service):
    with patch("api.services.tools_service.split_logs_main", new_callable=AsyncMock) as mock_split:
        mock_split.side_effect = Exception("error")

        result = await service.split_logs([], 1, "start", "end")
        assert result == {"status": "error", "message": "error"}


@pytest.mark.asyncio
async def test_compare_patterns_success(service):
    with (
        patch("api.services.tools_service.read_measured", new_callable=AsyncMock) as mock_read,
        patch("api.services.tools_service.make_indication_comparison_results", new_callable=AsyncMock) as mock_compare,
    ):
        mock_read.return_value = {"data": 1}
        mock_compare.return_value = {"res": 1}

        result = await service.compare_patterns("col", "rec", "dev", "pat")
        assert result == {"results": {"res": 1}}


@pytest.mark.asyncio
async def test_compare_patterns_exception(service):
    with patch("api.services.tools_service.read_measured", new_callable=AsyncMock) as mock_read:
        mock_read.side_effect = Exception("error")

        result = await service.compare_patterns("col", "rec", "dev", "pat")
        assert result == {"status": "error", "message": "error"}


@pytest.mark.asyncio
async def test_compare_log_pattern_success(service):
    with (
        patch("api.services.tools_service.log_parser_service.get_pattern_by_index") as mock_get,
        patch("api.services.tools_service.make_indication_comparison_results", new_callable=AsyncMock) as mock_compare,
    ):
        mock_get.return_value = {"data": 1}
        mock_compare.return_value = {"res": 1}

        result = await service.compare_log_pattern(0, "dev", "pat")
        assert result == {"results": {"res": 1}}


@pytest.mark.asyncio
async def test_compare_log_pattern_exception(service):
    with patch("api.services.tools_service.log_parser_service.get_pattern_by_index") as mock_get:
        mock_get.return_value = None

        result = await service.compare_log_pattern(0, "dev", "pat")
        assert result == {"status": "error", "message": "Invalid pattern index!"}


@pytest.mark.asyncio
async def test_generate_etalons_success(service):
    with patch("api.services.tools_service.generate_etalons_main", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = (["path/to/file"], ["plot1"])

        result = await service.generate_etalons("dev", "pat")
        assert result["status"] == "success"
        assert result["plots"] == ["plot1"]


@pytest.mark.asyncio
async def test_generate_etalons_exception(service):
    with patch("api.services.tools_service.generate_etalons_main", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = Exception("error")

        result = await service.generate_etalons("dev", "pat")
        assert result == {"status": "error", "message": "error"}


@pytest.mark.asyncio
async def test_generate_from_parameters_success_db(service):
    with patch(
        "api.services.tools_service.generate_indication_from_parameters_main", new_callable=AsyncMock
    ) as mock_gen:
        result = await service.generate_from_parameters(save_to_db=True, palette="[1,2,3]")
        assert result["status"] == "success"


@pytest.mark.asyncio
async def test_generate_from_parameters_success_file(service):
    with patch(
        "api.services.tools_service.generate_indication_from_parameters_main", new_callable=AsyncMock
    ) as mock_gen:
        mock_gen.return_value = "dummy.log"

        with patch("api.services.tools_service.FileResponse") as mock_fr:
            mock_fr.return_value = "file_response"
            result = await service.generate_from_parameters(save_to_db=False)
            assert result == "file_response"


@pytest.mark.asyncio
async def test_generate_from_parameters_exception(service):
    with patch(
        "api.services.tools_service.generate_indication_from_parameters_main", new_callable=AsyncMock
    ) as mock_gen:
        mock_gen.side_effect = Exception("error")
        result = await service.generate_from_parameters()
        assert result == {"status": "error", "message": "error"}


@pytest.mark.asyncio
async def test_generate_from_source_db(service):
    with patch("api.services.tools_service.generate_indication_from_source_main", new_callable=AsyncMock) as mock_gen:
        mock_file = MagicMock(spec=UploadFile)
        mock_file.filename = "test.txt"
        mock_file.read = AsyncMock(return_value=b"content")

        result = await service.generate_from_source(save_to_db=True, file=mock_file)
        assert result["status"] == "success"


@pytest.mark.asyncio
async def test_generate_from_source_zip(service):
    with patch("api.services.tools_service.generate_indication_from_source_main", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = ["out1.log"]

        with patch("api.services.tools_service.zipfile.ZipFile"):
            result = await service.generate_from_source(save_to_db=False)
            assert hasattr(result, "media_type")


@pytest.mark.asyncio
async def test_generate_from_source_zip_no_files(service):
    with patch("api.services.tools_service.generate_indication_from_source_main", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = []
        result = await service.generate_from_source(save_to_db=False)
        assert result == {"status": "error", "message": "No files were generated."}


@pytest.mark.asyncio
async def test_generate_from_source_exception(service):
    with patch("api.services.tools_service.generate_indication_from_source_main", new_callable=AsyncMock) as mock_gen:
        mock_gen.side_effect = Exception("error")
        result = await service.generate_from_source()
        assert result == {"status": "error", "message": "error"}
