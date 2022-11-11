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
from fastapi.responses import StreamingResponse


logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()

base_url = 'https://ipfs.objective.camera/{}'

app = FastAPI()


async def is_path_exists(path: str) -> bool:
    try:
        await aiofiles.os.stat(path)
    except OSError as e:
        return False
    except ValueError:
        return False
    return True


async def get_original_video(url):
    async with httpx.AsyncClient() as client:
        return await client.get(url)


def iterfile(thumbnail_path):
    with open(thumbnail_path, mode="rb") as file_like:
        yield from file_like


def generate_thumbnail(original_file_path: str, thumbnail_path: str):
    result = (
        ffmpeg
        .input(original_file_path)
        .filter('scale', 128, -1)
        .output(thumbnail_path, vframes=1)
        .overwrite_output()
        .run(capture_stdout=True, capture_stderr=True)
    )
    return result


@app.get('/thumbnails/{cid}.png')
async def thumbnail(cid: str):
    thumbnail_path = f'/thumbnails/{cid}.png'
    if await is_path_exists(thumbnail_path):
        return StreamingResponse(iterfile(thumbnail_path), media_type="image/png")
    resp = await get_original_video(base_url.format(cid))
    original_file_path = f'/tmp/{cid}.mp4'
    async with aiofiles.open(original_file_path, 'wb') as out_file:
        await out_file.write(resp.content)
    loop = asyncio.get_running_loop()
    await loop.run_in_executor(None, partial(generate_thumbnail, original_file_path, thumbnail_path))
    await aiofiles.os.remove(original_file_path)
    return StreamingResponse(iterfile(thumbnail_path), media_type="image/png")


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
