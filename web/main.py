import json
import logging
import sys
from datetime import datetime

import psycopg
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
pg_conn_str = "host=localhost dbname=postgres user=postgres password=password"


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


async def db_add(
    file_hash: str,
    lat: float,
    long: float,
    start_time: float,
    direction: int,
    address: str,
):
    start_time = datetime.fromtimestamp(start_time)
    async with await psycopg.AsyncConnection.connect(pg_conn_str) as conn:
        async with conn.cursor() as cur:
            return await cur.execute(
                'INSERT INTO video (hash, location, direction, start_time, address) VALUES (%s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s, %s, %s)',
                (file_hash, long, lat, direction, start_time, address),
            )


@app.post('/upload/')
async def upload(
    lat: float = Form(...),
    long: float = Form(...),
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
    await db_add(file_hash, lat, long, start, direction, 'some address')
    return JSONResponse(
        content={
            'add': resp_add,
            'pin': resp_pin,
        }
    )


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
