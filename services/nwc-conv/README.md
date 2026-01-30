# NWC-CONV service

Docker, for running nwc-conv.py containerized in the cloud.

## Base folder

Use cmd or bash and navigate to folder `/services/nwc-conv/`, and run
the below docker commands from there.

### 1. Build its image

*use `--no-cache` for fresh*

`docker build -t nwc-conv .`

### 2. Run its container

To expose it on e.g. port 8002:

`docker run -p 8002:8000 nwc-conv`

### 3. Send a request to its webapi

Make a request to the container:

`curl -X GET http://localhost:8002/health`
