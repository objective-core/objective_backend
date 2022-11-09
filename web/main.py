import json
import logging
import sys
from datetime import datetime
from decimal import Decimal
import os

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
    Location,
)
from ipfs import IPFSClient
from verification import get_address


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

app = FastAPI()
pg_conn_str = f"host={os.getenv('PG_HOST', 'localhost')} dbname={os.getenv('PG_DB', 'obj')} user={os.getenv('PG_USER')} password={os.getenv('PG_PASSWORD')}"

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
    ipfs_client = IPFSClient(base_url=os.getenv('IPFS_ENDPOINT', 'http://ipfs:5001'))
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
    await ipfs_client.pin(file_hash)
    uploader_address = get_address(expected_hash, signature)

    video = Video(
        uploader_address=uploader_address,
        location=Location(
            lat=lat,
            long=long,
            direction=median_direction,
            radius=0,
        ),
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
        status_code=201,
        content=json.loads(video.json()),
    )

@app.get('/requests')
def get_requests():
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    requests = video_request_manager.get_last_10_requests()
    return JSONResponse(
        status_code=200,
        content=json.loads(requests.json()),
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
        location=Location(
            lat=lat,
            long=long,
            direction=direction,
            radius=radius,
        ),
        start_time=start,
        end_time=end,
        reward=reward,
        address=address,
    )
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    await video_request_manager.add_request(
        request=video_request,
    )
    return JSONResponse(
        status_code=201,
        content=json.loads(video_request.json()),
    )

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
