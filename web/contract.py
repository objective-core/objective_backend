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

VIDEO_REQUESTER_CONTRACT_ADDR = '0xC6ea1442139Fd2938098E638213302b05DDD6CC6'
VIDEO_REQUESTS_PULL_INTERVAL = 5

CONTRACT_CALLER_ADDR = os.getenv('CONTRACT_CALLER_ADDR')
CONTRACT_CALLER_PRIVATE_KEY = os.getenv('CONTRACT_CALLER_PRIVATE_KEY')

logging.basicConfig(stream=sys.stdout, level=logging.INFO)
logger = logging.getLogger()


def w3_instance():
    return Web3(Web3.HTTPProvider(WEB3_HTTP_PROVIDER_URL))


def contract_instance(w3: Web3):
    logger.info('Loading VideoRequester contract')
    # WebsocketProvider doesn't work with the following error:
    # TypeError: As of 3.10, the *loop* parameter was removed from Lock() since it is no longer necessary
    # It is possible to get contract ABI from the blockchain instead
    with open('VideoRequester.json') as f:
        contract_abi = json.load(f)
    return w3.eth.contract(address=VIDEO_REQUESTER_CONTRACT_ADDR, abi=contract_abi)


async def pull_video_requests(video_request_manager: VideoRequestManager):
    contract = contract_instance(w3_instance())
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
                id=str(event.args.requestId),
                tx_hash=event_id,
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


def call_check_request(request_id: str):
    w3 = w3_instance()
    nonce = w3.eth.get_transaction_count(CONTRACT_CALLER_ADDR)
    contract = contract_instance(w3)

    # Doesn't seem like a good idea to store the private key on the backend.
    # It's a quick and dirty implementation for PoC.
    # For production we must rethink the flow so that the backend doesn't transact any funds.
    tx = contract.functions.checkRequest(int(request_id)).build_transaction({'nonce': nonce})
    signed_tx = w3.eth.account.sign_transaction(tx, private_key=CONTRACT_CALLER_PRIVATE_KEY)
    tx_hash = w3.eth.send_raw_transaction(signed_tx.rawTransaction)

    logger.info(f'Attempted to call checkRequest of contract {VIDEO_REQUESTER_CONTRACT_ADDR} for request {request_id}: {tx_hash}')
