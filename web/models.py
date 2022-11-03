from datetime import datetime
from decimal import Decimal

import psycopg
from pydantic import BaseModel


class Video(BaseModel):
    uploader_address: str
    actual_location_lat: float
    actual_location_long: float
    actual_median_direction: int
    uploaded_at: datetime
    actual_start_time: datetime
    actual_end_time: datetime
    file_hash: str


class VideoRequest(BaseModel):
    id: str
    location_lat: float
    location_long: float
    radius: int
    start_time: datetime
    end_time: datetime
    direction: int
    reward: Decimal
    address: str
    video: Video


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
                        request_location_lat,
                        request_location_long,
                        request_radius, 
                        request_start_time,
                        request_end_time,
                        request_direction,
                        reward,
                        requestor_address,
                    )
                    VALUES (
                        %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                    )
                    ''',
                    (
                        request.id,
                        request.location_long,
                        request.location_lat,
                        request.radius,
                        request.start_time,
                        request.end_time,
                        request.direction,
                        request.reward,
                        request.address,
                    ),
                )

    async def add_video(self, request_id: str, video: Video):
        raise NotImplementedError

    async def get_request(self, request_id: str) -> VideoRequest:
        raise NotImplementedError
