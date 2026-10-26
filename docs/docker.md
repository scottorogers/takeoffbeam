# Takeoff Beam in a browser (Docker, Intel Mac)

This builds the Linux x64 desktop app and CLI from source and displays the app
through noVNC. It runs on Intel Macs with Docker Desktop; it does not run the
Apple Silicon DMG. Rendering uses Mesa's software Vulkan driver.

## Start

Start Docker Desktop, then run from the repository root:

```sh
mkdir -p drawings
docker compose up --build -d
```

The first build compiles Rust dependencies and can take a while. Allow at least
8 GB of Docker memory and sufficient free disk space for build caches.

Open <http://localhost:6080/vnc.html?autoconnect=1&resize=scale>.
The browser shows the actual desktop application, with its PDF viewer, takeoff
tools, markups and exports. The virtual desktop is 1600 by 1000 pixels; noVNC
scales it to fit the browser. Use the noVNC sidebar to send clipboard text or
special keys; Linux shortcuts use Ctrl rather than macOS Command.

## Drawings and saved work

Copy PDFs into the local `drawings/` folder. In the app choose File → Open and
select `/drawings`. Export PDFs and CSVs into `/drawings` to see them on the Mac.
Browser drag-and-drop is not a file-upload mechanism for this remote desktop.
The first file picker can take several seconds while the desktop portal starts.

The app writes `.takeoff.json` files beside the PDFs in that folder. Its settings,
model downloads and AI workspace persist in the named `takeoff-home` volume.
`docker compose down` preserves both. `docker compose down -v` deletes the home
volume, including any files saved there, so save deliverables in `/drawings`.
Back up the drawings folder and home volume before removing or replacing them.
Drawings and `.env` files are excluded from Git and the image build context.

To use a different host folder, edit the `/drawings` bind mount in `compose.yaml`.
To use another port: `TAKEOFF_PORT=6081 docker compose up -d`.

## AI options

PDF viewing and manual takeoff need no AI service. This image does not bundle a
model, llama-server, Claude Code, Codex CLI or a web browser for HTML overlays.
The native Mac's CLI sign-ins and keychain are not shared with the container.

For AI, use Models → Custom endpoint with an image-capable, tool-capable model.
A model server on the Mac is reached as `http://host.docker.internal:PORT/v1`
(it must accept connections from Docker). Cloud endpoints send drawing content
to that provider; their usage can incur charges. Cloud device sign-in may need
you to open the displayed authorization URL and code in your Mac browser.
Nothing here configures a provider or installs a model automatically.

Large local vision models are likely to be slow on an Intel Mac. The container
does not have access to macOS Metal acceleration.

## CLI and MCP

The image includes `takeoff`, usable without starting a desktop:

```sh
docker compose run --rm --no-deps takeoff takeoff info /drawings/plan.pdf
docker compose exec takeoff takeoff export /drawings/plan.pdf --csv /drawings/markups.csv --summary /drawings/quantities.csv
docker compose run --rm --no-deps -T takeoff takeoff mcp /drawings/plan.pdf
```

Use container paths such as `/drawings/plan.pdf` in MCP requests. Avoid concurrent
writes from separate app and MCP processes to the same takeoff sidecar.

## Operations and access

```sh
docker compose ps
docker compose logs --tail=100 takeoff
docker compose stop
docker compose start
```

Only `127.0.0.1:6080` is published. VNC listens on loopback inside the container
and is not published separately. There is no VNC password because this setup is
for local use: anyone with access to this Mac's local port can control the app
and its files. Do not expose the port on a LAN or the internet without adding
authentication and TLS. The app runs as an unprivileged user, with no Docker
socket or host home directory mounted.

The health check verifies the web endpoint, X display, and all five supervised
processes. If the app fails to start, inspect the container logs for Vulkan/Mesa
errors and Docker memory limits. Closing the app restarts it; stop the container
to end the desktop session. Other Docker projects can run alongside this one.

Run `python3 docker/smoke-test.py` after startup to check the web endpoint,
desktop processes, PDF rendering, text extraction, MCP and PDF/CSV exports with
a temporary synthetic drawing. It needs Python 3 on the host and leaves
project drawings untouched. Browser interaction should also be checked manually.
