## Run

```bash
python main.py
```

## Examples

### Upload a file

```bash
curl -v -F lat=12 -F long=12 -F start=123123 -F file=@requirements.txt http://127.0.0.1:8000/upload/
```

Response:
```json
{"add":{"Name":"requirements.txt","Hash":"QmPEdd5zihTbogVfBZfsRn7rMRqGPhp8sgoXAgQnNY4sE4","Size":"3343"},"pin":{"Pins":["QmPEdd5zihTbogVfBZfsRn7rMRqGPhp8sgoXAgQnNY4sE4"]}}
```

Then you can use some ipfs public gateway to retrieve the file:

For the example above it would be: 

https://cloudflare-ipfs.com/ipfs/QmXpFwJ6FHgsNNorvgPSnucEuYWQKTUrhWLuyRxWc31NK6

or 

https://ipfs.io/ipfs/QmXpFwJ6FHgsNNorvgPSnucEuYWQKTUrhWLuyRxWc31NK6