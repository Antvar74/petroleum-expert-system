import pytest
from fastapi import HTTPException
from fastapi.datastructures import UploadFile
from io import BytesIO
from utils.upload_validation import validate_upload

@pytest.mark.asyncio
async def test_rejects_oversized_file():
    content = b"x" * (10 * 1024 * 1024 + 1)  # 10MB + 1 byte
    file = UploadFile(filename="big.csv", file=BytesIO(content))
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(file, allowed_extensions=[".csv"])
    assert exc_info.value.status_code == 413

@pytest.mark.asyncio
async def test_rejects_wrong_extension():
    file = UploadFile(filename="hack.exe", file=BytesIO(b"data"))
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(file, allowed_extensions=[".csv", ".pdf"])
    assert exc_info.value.status_code == 415

@pytest.mark.asyncio
async def test_accepts_valid_file():
    file = UploadFile(filename="data.csv", file=BytesIO(b"a,b\n1,2"))
    content = await validate_upload(file, allowed_extensions=[".csv"])
    assert content == b"a,b\n1,2"

@pytest.mark.asyncio
async def test_accepts_no_extension_when_allowed():
    file = UploadFile(filename="data", file=BytesIO(b"stuff"))
    with pytest.raises(HTTPException) as exc_info:
        await validate_upload(file, allowed_extensions=[".csv"])
    assert exc_info.value.status_code == 415
