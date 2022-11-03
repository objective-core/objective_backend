import json
import logging
import sys

import uvicorn
import httpx
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Form,
)
from fastapi.responses import JSONResponse

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

app = FastAPI()


async def ipfs_add(
    file: UploadFile = File(...),
) -> str:
    files = {
        'file': (file.filename, file.file)
    }
    async with httpx.AsyncClient() as client:
        resp = await client.post("http://localhost:5001/api/v0/add", files=files)
        logger.info(f'resp[add] {resp.text}')
        return resp.text


async def ipfs_pin(
    file_hash: str,
) -> str:
    async with httpx.AsyncClient() as client:
        resp = await client.post(f'http://localhost:5001/api/v0/pin/add?arg={file_hash}')
        logger.info(f'resp[pin] {resp.text}')
        return resp.text


@app.post('/upload/')
async def upload(
    lat: int = Form(...),
    long: int = Form(...),
    start: float = Form(...),
    direction: int = Form(...),
    expected_hash: str = Form(...),
    file: UploadFile = File(...),
):
    logger.info(f'New request: lat: {lat}, long: {long}, '
                f'start: {start}, direction: {direction}, '
                f'expected hash: {expected_hash}')
    resp = await ipfs_add(file)
    resp_add = json.loads(resp)
    file_hash = resp_add['Hash']
    if file_hash != expected_hash:
        return JSONResponse(
            status_code=400,
            content={
                'code': 'unexpected_hash',
                'msg': f'expected hash: {expected_hash}, actual: {file_hash}'
            }
        )
    resp = await ipfs_pin(file_hash)
    resp_pin = json.loads(resp)
    return JSONResponse(
        content={
            'add': resp_add,
            'pin': resp_pin,
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
