from datetime import datetime
from decimal import Decimal

import psycopg
from pydantic import BaseModel


class Video(BaseModel):
    uploader_address: str
    location_lat: float
    location_long: float
    median_direction: int
    uploaded_at: datetime
    start_time: datetime
    end_time: datetime
    file_hash: str


class VideoRequest(BaseModel):
    id: str
    lat: float
    long: float
    radius: int
    start_time: datetime
    end_time: datetime
    direction: int
    reward: Decimal
    address: str
    video: Video = None


class VideoRequestManager:
    def __init__(self, pg_conn_str: str):
        self.pg_conn_str = pg_conn_str

    async def add_request(self, request: VideoRequest):
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str) as conn:
            async with conn.cursor() as cur:
                return await cur.execute('''
                    INSERT INTO video_request 
                    (
                        request_id,
                        request_location,
                        request_radius, 
                        request_start_time,
                        request_end_time,
                        request_direction,
                        reward,
                        requestor_address
                    ) VALUES (
                        %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    );
                ''', (
                        request.id,
                        request.long,
                        request.lat,
                        request.radius,
                        request.start_time,
                        request.end_time,
                        request.direction,
                        request.reward,
                        request.address,
                    )
                )

    async def add_video(self, request_id: str, video: Video):
        print(f'R:{request_id}')
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    UPDATE video_request
                    SET uploader_address = %s,
                        actual_location = ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        actual_median_direction = %s,
                        uploaded_at = %s,
                        actual_start_time = %s,
                        actual_end_time = %s,
                        file_hash = %s
                    WHERE request_id = %s AND file_hash is NULL
                ''', (
                        video.uploader_address,
                        video.location_lat,
                        video.location_long,
                        video.median_direction,
                        video.uploaded_at,
                        video.start_time,
                        video.end_time,
                        video.file_hash,
                        request_id,
                    )
                )
                if cur.rowcount != 1:
                    raise Exception(
                        'this request is already fulfilled or does not exist'
                    )

    async def get_request(self, request_id: str) -> VideoRequest:
        raise NotImplementedError
