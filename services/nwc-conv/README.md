# NWC-CONV service

Docker, for running nwc-conv.py containerized in the cloud.

## STATUS

<div style="background-color:maroon;color:red;">
The container and its webapi run successfully, but not once deployed to scaleway.
I even filed a support ticket to scaleway: #1564293. I now stop development (6 Feb 2026) since it takes too much time. <br><br>
The current recurrent error I get is: "Application could not be started, or no application associated with the specified file.\nShellExecuteEx failed: "
<br><br>
Some background: I'm running an (old) 32bit windows commandline tool 'nwc-conv.exe'
on linux, using wine. As said, this works on my machine. So the cause must reside
in the difference between my local container environment and the one on scaleway.
I experimented a lot, using AI, where ai kept on suggesting solutions that ignored
the fact that it runs locally successfully, quite frustrating. At the same time,
I have stuff to do, which I list here:
<ul>
    <li> is nwc-conv.exe really 32bit? Since it's a later addition to Noteworthy software it might be 64 after all.
</ul>
</div>

## Important

`/app/nwc_convert.py` is a copy of `nwc-convert.py` that resides in the root.
Renamed with underscore, so it can be imported.

`/app/nwc_utiles.py` idem (no renaming).

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

Realistic request, run it from the folder where the nwctxt file resides:

`curl -X POST http://localhost:8002/convert -F 'nwctxt_file=@"Angry Money (3).nwctxt"' -F 'staff_names=Zang Bass' -OJ`

`curl -X POST http://localhost:8002/convert -F 'nwctxt_file=@"Angry Money (3).nwctxt"' -F 'staff_names=Bass Ritme' --output STEREOSCOPISCH.ZIP`
