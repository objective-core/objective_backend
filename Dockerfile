# Web3 Python package doesn't support 3.11 yet
FROM python:3.10

EXPOSE 8000
WORKDIR /obj

RUN pip install pip -U
COPY requirements.txt ./
RUN pip install -r requirements.txt

COPY contracts/VideoRequester.json ./
COPY web/*.py ./

ENTRYPOINT ["python", "main.py"]
