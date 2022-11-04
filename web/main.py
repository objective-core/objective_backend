import json
import logging
import sys
from datetime import datetime
from decimal import Decimal

import uvicorn
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Form,
)
from fastapi.responses import JSONResponse

from models import (
    VideoRequestManager,
    Video,
    VideoRequest,
)
from ipfs import IPFSClient


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

app = FastAPI()
pg_conn_str = "host=localhost dbname=postgres user=postgres password=password"


@app.post('/upload/')
async def upload(
    lat: float = Form(...),
    long: float = Form(...),
    start: float = Form(...),
    end: float = Form(...),
    median_direction: int = Form(...),
    expected_hash: str = Form(...),
    signature: str = Form(...),
    request_id: str = Form(...),
    file: UploadFile = File(...),
):
    logger.info(f'New upload request: request_id: {request_id}, signature: {signature}')
    ipfs_client = IPFSClient()
    resp = await ipfs_client.add(file)
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
    resp = await ipfs_client.pin(file_hash)
    resp_pin = json.loads(resp)
    uploader_address = 'uploader-address'  # TODO: Change to the real one from auth headers.
    video = Video(
        uploader_address=uploader_address,
        location_lat=lat,
        location_long=long,
        median_direction=median_direction,
        uploaded_at=datetime.now(),
        start_time=start,
        end_time=end,
        file_hash=file_hash,
    )
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    await video_request_manager.add_video(
        request_id=request_id,
        video=video,
    )
    return JSONResponse(
        content={
            'add': resp_add,
            'pin': resp_pin,
        }
    )


@app.post('/internal/request/')
async def create_request(
    id: str = Form(...),
    lat: float = Form(...),
    long: float = Form(...),
    radius: int = Form(...),
    start: datetime = Form(...),
    end: datetime = Form(...),
    direction: int = Form(...),
    reward: Decimal = Form(...),
):
    """Internal endpoint."""
    logger.info(f'New create request: request_id: {id}')
    address = 'requestor-address'  # TODO: Change to the real one from auth headers.
    video_request = VideoRequest(
        id=id,
        lat=lat,
        long=long,
        radius=radius,
        start_time=start,
        end_time=end,
        direction=direction,
        reward=reward,
        address=address,
    )
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    await video_request_manager.add_request(
        request=video_request,
    )
    return JSONResponse(status_code=201)

if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)
