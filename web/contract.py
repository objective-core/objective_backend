import asyncio
import json
import logging
import os
import sys
import psycopg

from web3 import Web3

from models import (
    VideoRequestManager,
    VideoRequest,
    Location,
)

WEB3_HTTP_PROVIDER_URL = os.getenv('WEB3_HTTP_PROVIDER_URL')

VIDEO_REQUESTER_CONTRACT_ADDR = '0xa8cbF99c7eA18a8E6a2Ea34619609A0aA9E77211'
VIDEO_REQUESTS_PULL_INTERVAL = 5

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()


def contract_instance():
    logger.info('Loading VideoRequester contract')
    # WebsocketProvider doesn't work with the following error:
    # TypeError: As of 3.10, the *loop* parameter was removed from Lock() since it is no longer necessary
    w3 = Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER_URL))
    # It is possible to get contract ABI from the blockchain instead
    with open('VideoRequester.json') as f:
        contract_abi = json.load(f)
    return w3.eth.contract(address=VIDEO_REQUESTER_CONTRACT_ADDR, abi=contract_abi)


async def pull_video_requests(video_request_manager: VideoRequestManager):
    contract = contract_instance()
    # We start pulling from the next block after the highest one to avoid duplicates
    from_block = (await video_request_manager.max_request_block_number())[0] or 0
    from_block += 1
    while True:
        logger.info(f'Pulling VideoRequested events from block {from_block}')

        event_filter = contract.events.VideoRequested.createFilter(fromBlock=from_block)
        for event in event_filter.get_all_entries():
            logger.info(f'Retrieved VideoRequested event: {event}')

            event_id = event.transactionHash.hex()
            video_request = VideoRequest(
                id=event_id,
                block_number=event.blockNumber,
                location=Location(
                    lat=event.args.lat / 10000000 - 180,
                    long=event.args.long / 10000000 - 180,
                    direction=event.args.direction,
                    radius=0,
                ),
                start_time=event.args.start,
                end_time=event.args.end,
                reward=event.args.reward,
                address=event.args.requester,
            )
            try:
                await video_request_manager.add_request(video_request)
            except psycopg.errors.UniqueViolation:
                logger.info(f'Ignoring duplicate VideoRequested event {event_id}')

            from_block = max(event.blockNumber + 1, from_block)
        await asyncio.sleep(VIDEO_REQUESTS_PULL_INTERVAL)
