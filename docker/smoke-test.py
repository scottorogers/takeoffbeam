#!/usr/bin/env python3
"""Exercise the running container using a synthetic PDF, never project drawings."""
import csv
import json
import os
from pathlib import Path
import struct
import subprocess
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parent.parent


def run(*args, input=None):
    return subprocess.run(
        ["docker", "compose", "exec", "-T", "takeoff", *args],
        cwd=ROOT, input=input, text=True, capture_output=True, check=True,
        timeout=90,
    ).stdout


def pdf_bytes():
    content = b"BT /F1 18 Tf 72 700 Td (Docker takeoff smoke test) Tj ET\n72 600 m 360 600 l S\n"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"endstream",
    ]
    data = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(data))
        data.extend(f"{number} 0 obj\n".encode() + obj + b"\nendobj\n")
    xref = len(data)
    data.extend(f"xref\n0 {len(offsets)}\n0000000000 65535 f \n".encode())
    for offset in offsets[1:]:
        data.extend(f"{offset:010d} 00000 n \n".encode())
    data.extend(f"trailer\n<< /Size {len(offsets)} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return data


def main():
    port = os.environ.get("TAKEOFF_PORT", "6080")
    with urllib.request.urlopen(f"http://127.0.0.1:{port}/vnc.html", timeout=5) as response:
        assert response.status == 200
    run("/opt/takeoff/healthcheck.sh")
    assert run("id", "-u").strip() == "1000", "Desktop must run unprivileged"
    with tempfile.TemporaryDirectory(prefix="smoke-", dir=ROOT / "drawings") as temporary:
        folder = Path(temporary)
        # Only this synthetic test folder: allow the container's uid 1000 to
        # write outputs even when a Linux CI runner has a different uid.
        folder.chmod(0o777)
        pdf = folder / "test.pdf"
        pdf.write_bytes(pdf_bytes())
        Path(str(pdf) + ".takeoff.json").write_text(json.dumps({
            "version": 1, "reviewType": "takeoff",
            "categories": [{"id": "outlets", "name": "Data outlets",
                            "color": "#0088ff", "kind": "count", "unitCost": 12.5}],
            "marks": [{"id": f"mark-{i}", "categoryId": "outlets", "page": 1,
                       "x": 0.2 + i * 0.1, "y": 0.3, "w": 0.02, "h": 0.02,
                       "source": "user", "status": "confirmed"} for i in range(2)],
        }))
        path = f"/drawings/{folder.name}/test.pdf"
        assert "1 pages" in run("takeoff", "info", path)
        assert "Docker takeoff smoke test" in run("takeoff", "text", path)
        run("takeoff", "render", path, "--dpi", "72", "-o", path + ".png")
        png = pdf.with_suffix(".pdf.png").read_bytes()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert struct.unpack(">II", png[16:24]) == (612, 792)
        requests = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2024-11-05", "capabilities": {},
                "clientInfo": {"name": "docker-smoke", "version": "1"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
        ]
        replies = [json.loads(line) for line in run(
            "takeoff", "mcp", path,
            input="".join(json.dumps(request) + "\n" for request in requests),
        ).splitlines()]
        assert all("error" not in reply for reply in replies), replies
        tools = next(reply["result"]["tools"] for reply in replies if reply.get("id") == 2)
        assert any(tool["name"] == "open_drawing" for tool in tools)
        run("takeoff", "export", path, "--pdf-out", path + ".export.pdf",
            "--csv", path + ".csv", "--summary", path + ".summary.csv")
        assert Path(str(pdf) + ".export.pdf").read_bytes().startswith(b"%PDF")
        assert Path(str(pdf) + ".csv").stat().st_size > 0
        with Path(str(pdf) + ".summary.csv").open(newline="") as summary:
            rows = list(csv.DictReader(summary))
        row = next(row for row in rows if row["Item"] == "Data outlets")
        assert float(row["Quantity"]) == 2, row
        assert float(row["Cost"]) == 25, row
    print("PASS: web endpoint, desktop processes, non-root user, PDF open/text/render, MCP, PDF/CSV export and host file writes")


if __name__ == "__main__":
    main()
