## Run

```bash
python main.py
```

## Examples

### Create a request (internal endpoint)

```bash
curl -v \
-F lat=12 \
-F long=12 \
-F start=123123 \
-F end=123140 \
-F direction=12 \
-F reward=42 \
-F radius=12 \
-F id=test-request-id \
http://127.0.0.1:8000/internal/request/
```

### Upload a file

```bash
curl -v \
-F lat=12 \
-F long=12 \
-F start=123123 \
-F end=123140 \
-F median_direction=12 \
-F signature=test \
-F request_id=test-request-id \
-F expected_hash=QmNT8axScpvoXJeKaoeZcD7E9ew9eSNp4EePXjwB62mrv4 \
-F file=@requirements.in \
http://127.0.0.1:8000/upload/
```

Response:
```json
{"add":{"Name":"requirements.in","Hash":"QmbCFLdj8FfgKZDquX6zb2CB3pmfj3spKpSam9zo9ZhSiU","Size":"39"},"pin":{"Pins":["QmbCFLdj8FfgKZDquX6zb2CB3pmfj3spKpSam9zo9ZhSiU"]}}
```

Then you can use some ipfs public gateway to retrieve the file:

For the example above it would be: 

https://cloudflare-ipfs.com/ipfs/QmbCFLdj8FfgKZDquX6zb2CB3pmfj3spKpSam9zo9ZhSiU

or 

https://ipfs.io/ipfs/QmbCFLdj8FfgKZDquX6zb2CB3pmfj3spKpSam9zo9ZhSiU
