import pytest
from unittest import mock
from pathlib import Path
from led_testing_toolkit.utils.logs_splitter import LogsSplitter

def test_init():
    with pytest.raises(ValueError, match="Max patterns per file must be a positive number!"):
        LogsSplitter(Path("out"), 0, "start", "end")
        
    splitter = LogsSplitter(Path("out"), 1, "start", "end")
    assert splitter.max_patterns_per_file == 1

class AsyncContextManagerMock:
    def __init__(self, obj):
        self.obj = obj
    async def __aenter__(self):
        return self.obj
    async def __aexit__(self, exc_type, exc, tb):
        pass

@pytest.mark.asyncio
async def test_calculate_file_hash():
    splitter = LogsSplitter(Path("out"), 1, "start", "end")
    
    m_file = mock.AsyncMock()
    m_file.read.side_effect = [b"chunk", b""]
    with mock.patch("aiofiles.open", mock.Mock(return_value=AsyncContextManagerMock(m_file))):
        res = await splitter._calculate_file_hash(Path("f"))
        assert len(res) == 64
        
    with mock.patch("aiofiles.open", side_effect=OSError("test")):
        res = await splitter._calculate_file_hash(Path("f"))
        assert res == "hash_error"

@pytest.mark.asyncio
async def test_find_patterns():
    splitter = LogsSplitter(Path("out"), 1, "START", "END")
    
    content = """
some garbage
START test 1 END
some middle
START test 2 END
more garbage
    """
    
    res = await splitter._find_patterns(content)
    assert len(res) == 2
    assert "START test 1 END" in res[0]
    assert "START test 2 END" in res[1]
    
    res_empty = await splitter._find_patterns("no match")
    assert res_empty == []

@pytest.mark.asyncio
async def test_write_chunk():
    splitter = LogsSplitter(Path("out"), 1, "start", "end")
    
    m_file = mock.AsyncMock()
    with mock.patch("aiofiles.open", return_value=AsyncContextManagerMock(m_file)):
        await splitter._write_chunk(Path("out.log"), ["p1", "p2"])
        m_file.write.assert_called_with("p1\n\n---\n\np2")
        
    with mock.patch("aiofiles.open", side_effect=OSError("test")), \
         mock.patch("led_testing_toolkit.utils.logs_splitter.logger") as mock_log:
        await splitter._write_chunk(Path("out.log"), ["p1", "p2"])
        mock_log.error.assert_called()

@pytest.mark.asyncio
async def test_process_single_file():
    splitter = LogsSplitter(Path("out"), 1, "start", "end")
    
    m_file = mock.AsyncMock()
    m_file.read.return_value = "START END"
    with mock.patch.object(splitter, "_calculate_file_hash", return_value="abc"), \
         mock.patch("aiofiles.open", return_value=AsyncContextManagerMock(m_file)), \
         mock.patch.object(splitter, "_find_patterns", return_value=["p1", "p2"]), \
         mock.patch.object(splitter, "_write_chunk") as mock_write, \
         mock.patch("pathlib.Path.mkdir"):
             
        res = await splitter._process_single_file(Path("in.log"))
        assert len(res) == 2
        mock_write.assert_called()
        
    # test file hash error
    with mock.patch.object(splitter, "_calculate_file_hash", return_value="hash_error"):
        res = await splitter._process_single_file(Path("in.log"))
        assert res == []
        
    # test read error
    with mock.patch.object(splitter, "_calculate_file_hash", return_value="abc"), \
         mock.patch("aiofiles.open", side_effect=OSError("test")), \
         mock.patch("pathlib.Path.mkdir"):
        res = await splitter._process_single_file(Path("in.log"))
        assert res == []
        
    # test empty patterns
    with mock.patch.object(splitter, "_calculate_file_hash", return_value="abc"), \
         mock.patch("aiofiles.open", return_value=AsyncContextManagerMock(m_file)), \
         mock.patch.object(splitter, "_find_patterns", return_value=[]), \
         mock.patch("pathlib.Path.mkdir"):
        res = await splitter._process_single_file(Path("in.log"))
        assert res == []

@pytest.mark.asyncio
async def test_process_batch():
    splitter = LogsSplitter(Path("out"), 1, "start", "end")
    with mock.patch.object(splitter, "_process_single_file", return_value=[Path("out.log")]):
        res = await splitter.process_batch([Path("in.log")])
        assert res == [Path("out.log")]
