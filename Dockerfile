# syntax=docker/dockerfile:1
FROM rust:bookworm AS build
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl pkg-config libgtk-3-dev libxkbcommon-dev \
    libwayland-dev libxcb1-dev libdbus-1-dev \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /src
COPY Cargo.toml Cargo.lock ./
COPY crates ./crates
COPY assets ./assets
COPY scripts/fetch-pdfium.sh ./scripts/fetch-pdfium.sh
RUN bash scripts/fetch-pdfium.sh
# Keep the first build within Docker Desktop's usual memory allocation.
ENV CARGO_BUILD_JOBS=2
RUN --mount=type=cache,target=/usr/local/cargo/registry \
    --mount=type=cache,target=/src/target \
    cargo build --locked --release -p takeoff-app -p takeoff-cli && \
    install -Dm755 target/release/takeoff-desk /out/takeoff-desk && \
    install -Dm755 target/release/takeoff /out/takeoff

FROM debian:bookworm-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl python3 supervisor xvfb x11-utils x11vnc \
    novnc websockify openbox dbus-x11 xdg-utils fonts-dejavu-core \
    libgtk-3-0 libxkbcommon0 libvulkan1 mesa-vulkan-drivers libgl1-mesa-dri \
    procps \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 --shell /bin/bash takeoff \
    && mkdir -p /drawings /tmp/runtime-takeoff \
    && chown takeoff:takeoff /drawings /tmp/runtime-takeoff \
    && chmod 700 /tmp/runtime-takeoff \
    && ln -s /usr/share/novnc/vnc.html /usr/share/novnc/index.html
# rfd's Linux file picker uses the desktop portal over the app's session bus.
RUN apt-get update && apt-get install -y --no-install-recommends \
    xdg-desktop-portal xdg-desktop-portal-gtk libxkbcommon-x11-0 \
    && rm -rf /var/lib/apt/lists/*
COPY --from=build /out/ /usr/local/bin/
COPY --from=build /src/vendor/pdfium/lib/libpdfium.so /opt/takeoff/lib/libpdfium.so
COPY LICENSE NOTICE /opt/takeoff/
COPY docker/entrypoint.sh docker/wait-for-display.sh docker/healthcheck.sh /opt/takeoff/
COPY docker/supervisord.conf /etc/takeoff-supervisord.conf
RUN chmod 755 /opt/takeoff/*.sh
ENV HOME=/home/takeoff \
    DISPLAY=:99 \
    XDG_RUNTIME_DIR=/tmp/runtime-takeoff \
    TAKEOFF_PDFIUM_DIR=/opt/takeoff/lib \
    LIBGL_ALWAYS_SOFTWARE=1 \
    WGPU_BACKEND=vulkan \
    XDG_CURRENT_DESKTOP=GNOME \
    XDG_SESSION_TYPE=x11 \
    GDK_CORE_DEVICE_EVENTS=1 \
    NO_AT_BRIDGE=1
USER takeoff
WORKDIR /drawings
EXPOSE 6080
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD ["/opt/takeoff/healthcheck.sh"]
ENTRYPOINT ["/opt/takeoff/entrypoint.sh"]
