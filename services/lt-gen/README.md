# LT-GEN service

Docker, for running lt-generate.py containerized in the cloud.

## Base folder

Use cmd or bash and navigate to folder `/services/lt-gen/`, and run
the below docker commands from there.

### 1. Build its image

*use `--no-cache` for fresh*

`docker build -t lt-gen .`

### 2. Run its container

To expose it on e.g. port 8001:

`docker run -p 8001:8000 lt-gen`

### 3. Send a request to its webapi

Make a request to the container:

`curl -X GET http://localhost:8001/health`
