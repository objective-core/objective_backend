from datetime import datetime, timedelta
from decimal import Decimal

import psycopg
from psycopg.rows import Row
from pydantic import BaseModel
from typing import List


class RequestNotFound(Exception):
    pass


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
    tx_hash: str = None
    block_number: int
    location: Location
    second_direction: int
    start_time: datetime
    end_time: datetime
    reward: Decimal
    address: str
    video: Video = None


class VideoRequestManager:
    def __init__(self, pg_conn_str: str):
        self.pg_conn_str = pg_conn_str

    @classmethod
    def to_video_request(cls, row: Row) -> VideoRequest:
        request_id, request_tx_hash, request_block_number, lat, long, radius, start_time, end_time, \
        direction, second_direction, reward, requestor_address, uploader_address, \
        actual_lat, actual_long, actual_median_direction, \
        uploaded_at, actual_start_time, actual_end_time, file_hash = row
        video_request = VideoRequest(
            id=request_id,
            tx_hash=request_tx_hash,
            block_number=request_block_number,
            location=Location(
                lat=lat,
                long=long,
                direction=direction,
                radius=radius,
            ),
            second_direction=second_direction,
            start_time=start_time,
            end_time=end_time,
            reward=reward,
            address=requestor_address,
        )
        if uploader_address:
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
        return video_request

    async def add_request(self, request: VideoRequest):
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str, autocommit=True) as conn:
            async with conn.cursor() as cur:
                return await cur.execute('''
                    INSERT INTO video_request 
                    (
                        request_id,
                        request_tx_hash,
                        request_block_number,
                        request_location,
                        request_radius, 
                        request_start_time,
                        request_end_time,
                        request_direction,
                        request_second_direction,
                        reward,
                        requestor_address
                    ) VALUES (
                        %s,
                        %s,
                        %s,
                        ST_SetSRID(ST_MakePoint(%s, %s), 4326),
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    );
                ''', (
                        request.id,
                        request.tx_hash,
                        request.block_number,
                        request.location.lat,
                        request.location.long,
                        request.location.radius,
                        request.start_time,
                        request.end_time,
                        request.location.direction,
                        request.second_direction,
                        request.reward,
                        request.address,
                    )
                )

    async def add_video(self, request_id: str, video: Video):
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str, autocommit=True) as conn:
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
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    SELECT
                        request_id,
                        request_tx_hash,
                        request_block_number,
                        ST_x(request_location),
                        ST_y(request_location),
                        request_radius,
                        request_start_time,
                        request_end_time,
                        request_direction,
                        request_second_direction,
                        reward,
                        requestor_address,
                        uploader_address,
                        ST_x(actual_location),
                        ST_y(actual_location),
                        actual_median_direction,
                        uploaded_at,
                        actual_start_time,
                        actual_end_time,
                        file_hash
                    FROM video_request
                    WHERE request_id = %s
                    ORDER BY request_end_time DESC
                    LIMIT 10
                ''', (request_id,)
                )
                row = await cur.fetchone()
                if not row:
                    raise RequestNotFound
                return self.to_video_request(row)

    async def get_last_10_requests(self) -> List[VideoRequest]:
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    SELECT
                        request_id,
                        request_tx_hash,
                        request_block_number,
                        ST_x(request_location),
                        ST_y(request_location),
                        request_radius,
                        request_start_time,
                        request_end_time,
                        request_direction,
                        request_second_direction,
                        reward,
                        requestor_address,
                        uploader_address,
                        ST_x(actual_location),
                        ST_y(actual_location),
                        actual_median_direction,
                        uploaded_at,
                        actual_start_time,
                        actual_end_time,
                        file_hash
                    FROM video_request
                    ORDER BY request_end_time DESC
                    LIMIT 10
                '''
                )
                results = []
                rows = await cur.fetchall()
                for row in rows:
                    results.append(self.to_video_request(row))
                return results

    async def requests_by_location(
            self,
            lat: float,
            long: float,
            radius: int,
            hide_expired: bool,
            since_seconds: int,
    ) -> List[VideoRequest]:
        end_time = datetime.utcnow() if hide_expired else datetime(1970, 1, 1)
        since = datetime.utcnow() - timedelta(seconds=since_seconds)
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    SELECT
                        request_id,
                        request_tx_hash,
                        request_block_number,
                        ST_x(request_location),
                        ST_y(request_location),
                        request_radius,
                        request_start_time,
                        request_end_time,
                        request_direction,
                        request_second_direction,
                        reward,
                        requestor_address,
                        uploader_address,
                        ST_x(actual_location),
                        ST_y(actual_location),
                        actual_median_direction,
                        uploaded_at,
                        actual_start_time,
                        actual_end_time,
                        file_hash
                    FROM video_request
                    WHERE
                        (
                            ST_DistanceSphere(request_location, ST_MakePoint(%s,%s)) <= %s
                            AND (
                                request_end_time > %s
                                OR file_hash IS NOT NULL
                            )
                            AND request_start_time > %s
                        ) OR (
                            request_id in ('2', '3', '5', '22', '23', '24', '27', '30', '31', '52', '53', '54', '55', '56', '57', '58')
                        )
                    ORDER BY request_end_time DESC
                ''', (lat, long, radius, end_time, since)
                )
                results = []
                rows = await cur.fetchall()
                for row in rows:
                    results.append(self.to_video_request(row))
                return results

    async def requests_by_uploader_address(
            self,
            address: str,
    ) -> List[VideoRequest]:
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    SELECT
                        request_id,
                        request_tx_hash,
                        request_block_number,
                        ST_x(request_location),
                        ST_y(request_location),
                        request_radius,
                        request_start_time,
                        request_end_time,
                        request_direction,
                        request_second_direction,
                        reward,
                        requestor_address,
                        uploader_address,
                        ST_x(actual_location),
                        ST_y(actual_location),
                        actual_median_direction,
                        uploaded_at,
                        actual_start_time,
                        actual_end_time,
                        file_hash
                    FROM video_request
                    WHERE uploader_address = %s
                    ORDER BY request_end_time DESC
                ''', (address,)
                )
                results = []
                rows = await cur.fetchall()
                for row in rows:
                    results.append(self.to_video_request(row))
                return results

    async def requests_by_requestor_address(
            self,
            address: str,
    ) -> List[VideoRequest]:
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    SELECT
                        request_id,
                        request_tx_hash,
                        request_block_number,
                        ST_x(request_location),
                        ST_y(request_location),
                        request_radius,
                        request_start_time,
                        request_end_time,
                        request_direction,
                        request_second_direction,
                        reward,
                        requestor_address,
                        uploader_address,
                        ST_x(actual_location),
                        ST_y(actual_location),
                        actual_median_direction,
                        uploaded_at,
                        actual_start_time,
                        actual_end_time,
                        file_hash
                    FROM video_request
                    WHERE requestor_address = %s
                    ORDER BY request_end_time DESC
                ''', (address,)
                )
                results = []
                rows = await cur.fetchall()
                for row in rows:
                    results.append(self.to_video_request(row))
                return results

    async def max_request_block_number(self):
        async with await psycopg.AsyncConnection.connect(self.pg_conn_str) as conn:
            async with conn.cursor() as cur:
                await cur.execute('''
                    SELECT MAX(request_block_number)
                    FROM video_request;
                ''')
                return await cur.fetchone()
