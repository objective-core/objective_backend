FROM ubuntu:22.04

RUN mkdir /thumbnails
RUN apt-get update
RUN apt-get install ffmpeg pip -y

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY *.py .

ENTRYPOINT ["python3", "main.py"]
