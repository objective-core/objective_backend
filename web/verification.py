from web3.auto import w3
from eth_account.messages import encode_defunct


def get_address(video_hash, signature):
    message = f'video hash: {video_hash}'
    print(message)

    return w3.eth.account.recover_message(
        encode_defunct(text=message),
        signature=signature,
    )
