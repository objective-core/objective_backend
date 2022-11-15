import logging
import sys
from functools import partial

import asyncio
import aiofiles
import aiofiles.os
import ffmpeg
import httpx
import uvicorn
from fastapi import (
    FastAPI,
)
from fastapi.responses import JSONResponse

from verifier import verify_video


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

base_url = 'https://ipfs.objective.camera/{}'

app = FastAPI()


async def get_original_video(url):
    async with httpx.AsyncClient() as client:
        return await client.get(url)


@app.get('/verify/{cid}/{direction}/{second_direction}')
async def verify(cid: str, direction: int, second_direction: int):
    resp = await get_original_video(base_url.format(cid))
    original_file_path = f'/tmp/{cid}.mp4'
    async with aiofiles.open(original_file_path, 'wb') as out_file:
        await out_file.write(resp.content)
    loop = asyncio.get_running_loop()
    is_verified, direction_time, second_direction_time, rotateCode = verify_video(original_file_path, direction, second_direction)
    await aiofiles.os.remove(original_file_path)

    return JSONResponse(
        status_code=200,
        content={
            'is_verified': is_verified,
            'direction_time': direction_time,
            'second_direction_time': second_direction_time,
            'rotate_code': rotateCode,
        },
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)
