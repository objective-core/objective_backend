#!/bin/sh

start_time=`date +%s`;
end_time=$(($start_time + 3600));
curl -v -F lat=41.7078004 -F long=44.7628534 -F start=$start_time -F end=$end_time -F direction=45 -F reward=1000000000000000 -F radius=10 -F id=$start_time http://127.0.0.1:8000/internal/request/
