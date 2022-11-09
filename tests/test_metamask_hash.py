from web.verification import get_address

def test_signature_verification():
    signature = '0x5049f171bfec251cc7ebdda8a80704df2d582cca2ef1347810285626bbc35f0d33df86414197814265c7c313752ff619bdcd8dd5b3c4800915020a402a5c3b271c'

    address = get_address(
        '22c3754bd41827a484f397ba3d60a9beb36657253a0d09603729361611a47b27',
        signature,
    )

    assert address == '0x7DB4C793cECE6f1e586B8bc82ad5E6C0355AbB7E'
