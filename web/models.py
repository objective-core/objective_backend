from datetime import datetime
from decimal import Decimal

import psycopg
from pydantic import BaseModel, List


class Location(BaseModel):
    lat: float
    long: float
    direction: int
    radius: int


class Video(BaseModel):
    uploader_address: str
    location: Location
    uploaded_at: datetime
    start_time: datetime
    end_time: datetime
    file_hash: str


class VideoRequest(BaseModel):
    id: str
    location: Location
    start_time: datetime
    end_time: datetime
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
                        request.location.long,
                        request.location.lat,
                        request.location.radius,
                        request.start_time,
                        request.end_time,
                        request.location.direction,
                        request.reward,
                        request.address,
                    )
                )

    async def add_video(self, request_id: str, video: Video):
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
                        video.location.lat,
                        video.location.long,
                        video.location.direction,
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

    async def get_last_10_requests(self, limit: int) -> List[VideoRequest]:
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    SELECT
                        request_id,
                        ST_x(request_location),
                        ST_y(request_location)
                        request_radius,
                        request_start_time,
                        request_end_time,
                        request_direction,
                        reward,
                        requestor_address,
                        uploader_address,
                        ST_x(actual_location),
                        ST_y(actual_location)
                        actual_median_direction,
                        uploaded_at,
                        actual_start_time,
                        actual_end_time,
                        file_hash
                    FROM video_request
                    ORDER BY end_time DESC
                    LIMIT 10
                '''
                )
                result = List[VideoRequest]()
                for record in cur:
                    request_id, lat, long, radius, start_time, end_time,\
                    direction, reward, requestor_address, uploader_address,\
                        actual_lat, actual_long, actual_median_direction,\
                        uploaded_at, actual_start_time, actual_end_time, file_hash = record
                    video_request = VideoRequest(
                        id=request_id,
                        location=Location(
                            lat=lat,
                            long=long,
                            direction=direction,
                            radius=radius,
                        ),
                        start_time=start_time,
                        end_time=end_time,
                        reward=reward,
                        address=requestor_address,
                    )
                    if not uploader_address:
                        video_request.video = Video(
                            uploader_address=uploader_address,
                            location=Location(
                                lat=actual_lat,
                                long=actual_long,
                                direction=actual_median_direction,
                                radius=radius,
                            ),
                            uploaded_at=uploaded_at,
                            start_time=actual_start_time,
                            end_time=actual_end_time,
                            file_hash=file_hash,
                        )
                    result.append(video_request)
                return result
