import sys
import logging

import httpx
from fastapi import (
    File,
    UploadFile,
)

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()


class IPFSClient:
    def __init__(self, base_url):
        self.base_url = base_url

    async def add(
        self,
        file: UploadFile = File(...),
    ) -> str:
        files = {
            'file': (file.filename, file.file)
        }
        async with httpx.AsyncClient() as client:
            resp = await client.post(f'{self.base_url}/api/v0/add', files=files)
            logger.info(f'resp[add] {resp.text}')
            return resp.text

    async def pin(
        self,
        file_hash: str,
    ) -> str:
        async with httpx.AsyncClient() as client:
            resp = await client.post(f'{self.base_url}/api/v0/pin/add?arg={file_hash}')
            logger.info(f'resp[pin] {resp.text}')
            return resp.text
