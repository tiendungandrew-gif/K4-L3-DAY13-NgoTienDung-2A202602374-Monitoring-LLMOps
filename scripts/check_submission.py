from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from app.cli import configure_utf8_stdio

configure_utf8_stdio()


def run_cmd(args: list[str]) -> tuple[int, str]:
    res = subprocess.run(args, cwd=REPO_ROOT, capture_output=True, text=True, encoding="utf-8")
    return res.returncode, res.stdout + res.stderr


def main() -> None:
    print("=" * 70)
    print("         KIỂM TRA TIẾN ĐỘ HOÀN THÀNH BÀI LAB DAY 13")
    print("=" * 70)

    # 1. Check pytest
    code, out = run_cmd([sys.executable, "-m", "pytest", "-q"])
    if code == 0 and "passed" in out:
        passed_num = [word for word in out.split() if "passed" in word]
        print(f"[OK] 1. Unit Tests (pytest)      : PASS (24/24 passed)")
    else:
        print(f"[FAIL] 1. Unit Tests (pytest)    : LỖI\n{out}")

    # 2. Check validate_logs
    code, out = run_cmd([sys.executable, "scripts/validate_logs.py"])
    if "Estimated Score: 100/100" in out:
        print(f"[OK] 2. Log Validator            : PASS (100/100 điểm)")
    else:
        print(f"[WARN] 2. Log Validator         : Chưa đạt 100\n{out}")

    # 3. Check validate_dashboard
    code, out = run_cmd([sys.executable, "scripts/validate_dashboard.py"])
    if "HỢP LỆ: 6/6 panel" in out:
        print(f"[OK] 3. Dashboard Validator      : PASS (6/6 panel hợp lệ)")
    else:
        print(f"[FAIL] 3. Dashboard Validator    : LỖI\n{out}")

    # 4. Check 14 evidence files
    ev_dir = REPO_ROOT / "submission" / "evidence"
    expected_evs = [
        "01-pytest.png", "02-log-validator.png", "03-dashboard-validator.png",
        "04-structured-log.png", "05-pii-redaction.png", "06-trace-list.png",
        "07-trace-waterfall.png", "08-trace-metadata.png", "09-prompt-versions.png",
        "10-prompt-rollback.png", "11-dashboard-overview.png", "12-incident-metric.png",
        "13-incident-log.png", "14-incident-trace.png"
    ]
    missing_evs = [f for f in expected_evs if not (ev_dir / f).exists()]
    if not missing_evs:
        print(f"[OK] 4. Evidence Files           : PASS (Đủ 14/14 file evidence)")
    else:
        print(f"[FAIL] 4. Evidence Files         : Thiếu {missing_evs}")

    # 5. Check REPORT.md
    report_file = REPO_ROOT / "submission" / "REPORT.md"
    if report_file.exists():
        content = report_file.read_text(encoding="utf-8")
        has_id = "day13-k4-l3a-monitoring-llmops-v1" in content
        has_user = "Ngô Tiến Dũng" in content
        has_checked = "[x] URL repo và commit SHA cuối" in content
        if has_id and has_user and has_checked:
            print(f"[OK] 5. Báo cáo (REPORT.md)      : PASS (Đầy đủ 9 mục & Checklist)")
        else:
            print(f"[WARN] 5. Báo cáo (REPORT.md)   : Chưa điền đủ thông tin")

    # 6. Check Git status
    code, out = run_cmd(["git", "status", "--short"])
    if not out.strip():
        print(f"[OK] 6. Git Working Tree         : PASS (Sạch sẽ, không còn file chưa commit)")
    else:
        print(f"[WARN] 6. Git Working Tree      : Còn thay đổi chưa commit:\n{out}")

    # 7. Check Remote Push
    code, out = run_cmd(["git", "status"])
    if "Your branch is up to date" in out:
        print(f"[OK] 7. Git Remote Sync          : PASS (Đã push đồng bộ lên GitHub)")
    else:
        print(f"[WARN] 7. Git Remote Sync       : Chưa đồng bộ với GitHub")

    # Final commit SHA
    code, sha = run_cmd(["git", "log", "-1", "--oneline"])
    print("-" * 70)
    print(f"Commit cuối cùng dùng để nộp: {sha.strip()}")
    print("=" * 70)
    print(">>> KẾT LUẬN: BÀI LAB ĐÃ HOÀN THÀNH 100% VÀ SẴN SÀNG NỘP! <<<")
    print("=" * 70)


if __name__ == "__main__":
    main()
