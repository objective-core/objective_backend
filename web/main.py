import random
import asyncio
import json
import logging
import sys
from datetime import datetime
from decimal import Decimal
import os
import httpx
import hashlib

import uvicorn
from fastapi import (
    BackgroundTasks,
    FastAPI,
    Form,
    UploadFile,
    File,
)
from fastapi.responses import JSONResponse


from contract import (
    call_check_request,
    pull_video_requests,
)
from eth_abi import encode
from contract import pull_video_requests
from models import (
    VideoRequestManager,
    Video,
    VideoRequest,
    Location,
    RequestNotFound,
)
from verification import get_address


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

app = FastAPI()
pg_conn_str = f"host={os.getenv('PG_HOST', 'localhost')} dbname={os.getenv('PG_DB', 'obj')} user={os.getenv('PG_USER')} password={os.getenv('PG_PASSWORD')}"


async def verify_request_video(cid, request):
    url = f'http://localhost:8002/verify/{cid}/{request.location.direction}/{request.second_direction}'

    async with httpx.AsyncClient() as client:
        return await client.get(url)


@app.post('/upload/')
async def upload(
    background_tasks: BackgroundTasks,
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

    # check if file exists in /root/videos folder, name of file - expected_hash
    file_exists = os.path.isfile(f'/videos/{expected_hash}')

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

    uploader_address = get_address(expected_hash, signature)

    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    try:
        request = await video_request_manager.get_request(
            request_id=request_id,
        )
    except RequestNotFound:
        return JSONResponse(status_code=404)

    try:
        result = await verify_request_video(expected_hash, request)
        if(not result.json()['is_verified']):
            return JSONResponse(status_code=400, content={'is_verified': False})
    except Exception as e:
        logger.exception(e)
        return JSONResponse(status_code=400, content={'is_verified': False})

    # This is a very unreliable way to call a function of a smart contract.
    # It's a quick and dirty implementation for PoC.
    background_tasks.add_task(call_check_request, request_id)

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
            'abi': '0x' + encode(['address', 'string'], (request.video.uploader_address, request.video.file_hash)).hex(),
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


# handler uploads file to directory /root/videos, assignes hash, and returns it in Hash field
@app.post('/api/v0/add')
async def add_file(file: UploadFile = File(...)):
    contents = await file.read()
    file_hash = hashlib.sha256(contents).hexdigest()

    with open(f'/videos/{file_hash}', 'wb') as f:
        f.write(contents)

    return JSONResponse(
        status_code=200,
        content={'Hash': file_hash},
    )


@app.on_event("startup")
def schedule_pull_video_requests():
    loop = asyncio.get_event_loop()
    video_request_manager = VideoRequestManager(pg_conn_str=pg_conn_str)
    loop.create_task(pull_video_requests(video_request_manager))


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
