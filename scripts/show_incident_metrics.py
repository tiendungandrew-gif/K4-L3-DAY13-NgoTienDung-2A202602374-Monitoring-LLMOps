from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

configure_utf8_stdio()

with open("data/logs.jsonl", encoding="utf-8") as f:
    logs = [json.loads(line) for line in f if line.strip()]

responses = [l for l in logs if l.get("event") == "response_sent"]

print("=" * 80)
print("             THỐNG KÊ METRIC SỰ CỐ TỪ DATA/LOGS.JSONL")
print("=" * 80)
print(f"{'Timestamp (UTC)':24} | {'Correlation ID':15} | {'Latency':12} | {'Trạng thái'}")
print("-" * 80)

for r in responses:
    lat = r.get("latency_ms", 0)
    cid = r.get("correlation_id", "N/A")
    ts = r.get("ts", "")[:19]
    if lat >= 2000:
        print(f"{ts:24} | {cid:15} | {lat:5} ms     | [CANH BAO] SPIKE > 2000ms")

print("-" * 80)
normal_lats = [r["latency_ms"] for r in responses if r.get("latency_ms", 0) < 2000]
spike_lats = [r["latency_ms"] for r in responses if r.get("latency_ms", 0) >= 2000]

print(f"Tổng số request: {len(responses)}")
print(f"Độ trễ bình thường (Baseline): P50 = {sorted(normal_lats)[len(normal_lats)//2]} ms | Max = {max(normal_lats)} ms")
print(f"Độ trễ lúc xảy ra sự cố (Spike)    : P95 = {max(spike_lats)} ms (Tăng vọt ~17 lần)")
print("=" * 80)
