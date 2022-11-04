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
-F id=test-request-id-7 \
http://127.0.0.1:8000/internal/request/
```

Response:

```json
{"id":"test-request-id-7","location":{"lat":12.0,"long":12.0,"direction":12,"radius":12},"start_time":"1970-01-02T10:12:03+00:00","end_time":"1970-01-02T10:12:20+00:00","reward":42,"address":"requestor-address","video":null}
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
-F request_id=test-request-id-7 \
-F expected_hash=QmNT8axScpvoXJeKaoeZcD7E9ew9eSNp4EePXjwB62mrv4 \
-F file=@requirements.in \
http://127.0.0.1:8000/upload/
```

Response:
```json
{"uploader_address":"uploader-address","location":{"lat":12.0,"long":12.0,"direction":12,"radius":0},"uploaded_at":"2022-11-04T12:54:51.998862","start_time":"1970-01-02T10:12:03+00:00","end_time":"1970-01-02T10:12:20+00:00","file_hash":"QmNT8axScpvoXJeKaoeZcD7E9ew9eSNp4EePXjwB62mrv4"}
```

Then you can use some ipfs public gateway to retrieve the file:

For the example above it would be: 

https://cloudflare-ipfs.com/ipfs/QmbCFLdj8FfgKZDquX6zb2CB3pmfj3spKpSam9zo9ZhSiU

or 

https://ipfs.io/ipfs/QmbCFLdj8FfgKZDquX6zb2CB3pmfj3spKpSam9zo9ZhSiU
