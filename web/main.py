import asyncio
import json
import logging
import sys
from datetime import datetime
from decimal import Decimal
import os

import uvicorn
from fastapi import (
    FastAPI,
    Form,
)
from fastapi.responses import JSONResponse

from eth_abi import encode
from events import pull_video_requests
from models import (
    VideoRequestManager,
    Video,
    VideoRequest,
    Location,
    RequestNotFound,
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
):
    logger.info(f'New upload request: request_id: {request_id}, signature: {signature}')
    ipfs_client = IPFSClient(base_url=os.getenv('IPFS_ENDPOINT', 'http://localhost:5001'))
    file_exists = await ipfs_client.file_exists(expected_hash)
    if file_exists:
        file_hash = expected_hash
    else:
        return JSONResponse(
            status_code=400,
            content={
                'code': 'file_not_found',
                'msg': 'file with expected_hash does not exist on the node'
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
async def get_requests():
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    last_10_requests = await video_request_manager.get_last_10_requests()
    return JSONResponse(
        status_code=200,
        content={'requests': [json.loads(r.json()) for r in last_10_requests]},
    )


@app.get('/video/{request_id}')
async def video_by_request_id(
        request_id: str,
):
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    try:
        request = await video_request_manager.get_request(
            request_id=request_id,
        )
    except RequestNotFound:
        return JSONResponse(status_code=404)
    if not request.video:
        return JSONResponse(status_code=404)
    return JSONResponse(
        status_code=200,
        content={
            'url': f'https://api.objective.camera/video/{request_id}',
            'uploader': request.video.uploader_address,
            'cid': request.video.file_hash,
            'request': request_id,
            'abi': encode(['address', 'string'], (request.video.uploader_address, request.video.file_hash)),
        }
    )


@app.get('/requests/{request_id}')
async def requests_by_id(
        request_id: str,
):
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    request = await video_request_manager.get_request(
        request_id=request_id,
    )
    return JSONResponse(
        status_code=200,
        content=json.loads(request.json()),
    )


@app.get('/requests_by_location')
async def requests_by_location(
        lat: float,
        long: float,
        radius: int,
        hide_expired: bool = False,
        since_seconds: int = 3600 * 24 * 7
):
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    requests = await video_request_manager.requests_by_location(
        lat=lat,
        long=long,
        radius=radius,
        hide_expired=hide_expired,
        since_seconds=since_seconds,
    )
    return JSONResponse(
        status_code=200,
        content={'requests': [json.loads(r.json()) for r in requests]},
    )


@app.get('/requests_by_uploader/{address}')
async def requests_by_uploader(
        address: str,
):
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    requests = await video_request_manager.requests_by_uploader_address(
        address=address,
    )
    return JSONResponse(
        status_code=200,
        content={'requests': [json.loads(r.json()) for r in requests]},
    )


@app.get('/requests_by_requestor/{address}')
async def requests_by_requestor(
        address: str,
):
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    requests = await video_request_manager.requests_by_requestor_address(
        address=address,
    )
    return JSONResponse(
        status_code=200,
        content={'requests': [json.loads(r.json()) for r in requests]},
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
        block_number=0,
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


@app.on_event("startup")
def schedule_pull_video_requests():
    loop = asyncio.get_event_loop()
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    loop.create_task(pull_video_requests(video_request_manager))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
