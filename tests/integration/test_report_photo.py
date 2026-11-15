import json
import re
import shutil
import subprocess

import pytest
from fastapi.testclient import TestClient


def test_text_reader_files_are_served_and_unknown_files_are_not(api_client: TestClient) -> None:
    script = api_client.get("/ocr/tesseract.min.js")
    assert script.status_code == 200 and "javascript" in script.headers["content-type"]
    assert api_client.get("/ocr/worker.min.js").status_code == 200
    assert api_client.get("/ocr/eng.traineddata.gz").status_code == 200
    assert api_client.get("/ocr/..%2Findex.html").status_code == 404
    assert api_client.get("/ocr/missing.js").status_code == 404


def test_dashboard_allows_the_text_reader_to_run_without_external_resources(api_client: TestClient) -> None:
    response = api_client.get("/")
    assert "wasm-unsafe-eval" in response.headers["content-security-policy"]
    assert "https://" not in response.text
    for text in ('id="ocrFile"', "extractReadings", "Nothing is saved until you check the numbers"):
        assert text in response.text


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_values_are_found_in_report_text(api_client: TestClient) -> None:
    page = api_client.get("/").text
    ranges = re.search(r"const REPORT_RANGES=.*?;\nconst REPORT_LABELS=.*?;\n", page, re.S)
    function = re.search(r"function extractReadings\(text\)\{.*?\n return out\}", page, re.S)
    assert ranges and function
    report = (
        "Heart rate: 72 bpm\nBlood pressure: 118/76 mmHg\nGlucose 5.1 mmol/L\nTemp 98.6 F\nSleep 6.5 h\nDose 0.62 mSv\n"
    )
    script = (
        f"{ranges.group(0)}{function.group(0)}\nconsole.log(JSON.stringify(extractReadings({json.dumps(report)})));"
    )
    found = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    values = {item["ind"]: item["value"] for item in found}
    assert values["heart_rate"] == 72
    assert (values["systolic_blood_pressure"], values["diastolic_blood_pressure"]) == (118, 76)
    assert values["blood_glucose"] == 91.8 and values["body_temperature"] == 37 and values["radiation_dose"] == 0.62


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_implausible_numbers_are_ignored(api_client: TestClient) -> None:
    page = api_client.get("/").text
    ranges = re.search(r"const REPORT_RANGES=.*?;\nconst REPORT_LABELS=.*?;\n", page, re.S)
    function = re.search(r"function extractReadings\(text\)\{.*?\n return out\}", page, re.S)
    assert ranges and function
    call = "extractReadings('Heart rate 9\\nBP 300/20\\nTemp 12')"
    script = f"{ranges.group(0)}{function.group(0)}\nconsole.log(JSON.stringify({call}));"
    found = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert found == []


def _page_functions(api_client: TestClient, names: list[str]) -> str:
    page = api_client.get("/").text
    pieces = []
    for name in names:
        found = re.search(
            rf"function {name}\(.*?\n(?=function |let |const |async function |\$\(|/\*|\(\(\)|$)", page, re.S
        )
        assert found, name
        pieces.append(found.group(0))
    return "\n".join(pieces)


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_pulse_is_worked_out_from_taps(api_client: TestClient) -> None:
    code = _page_functions(api_client, ["bpmFromTaps"])
    steady = [round(i * 833.0) for i in range(14)]
    uneven = [0, 300, 1500, 1700, 3200, 3300, 5200, 5300, 7600, 7700]
    script = f"{code}\nconsole.log(JSON.stringify([bpmFromTaps({steady}),bpmFromTaps({uneven}),bpmFromTaps([1,2,3])]));"
    steady_result, uneven_result, short_result = json.loads(
        subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout
    )
    assert steady_result == {"ok": True, "bpm": 72}
    assert uneven_result["ok"] is False and short_result["ok"] is False


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_career_radiation_total_counts_each_day_once(api_client: TestClient) -> None:
    code = _page_functions(api_client, ["careerDose"])
    rows = [
        {"measured_at": "2026-11-01T08:00:00Z", "measured_value": 0.5},
        {"measured_at": "2026-11-01T20:00:00Z", "measured_value": 0.7},
        {"measured_at": "2026-11-02T08:00:00Z", "measured_value": 1.0},
    ]
    script = f"{code}\nconsole.log(JSON.stringify(careerDose({rows})));"
    result = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert result == {"total": 1.7, "days": 2}


def test_dashboard_has_tap_counter_and_radiation_estimate(api_client: TestClient) -> None:
    page = api_client.get("/").text
    for text in ('id="tapBtn"', 'id="radEnv"', "Estimated from mission environment, not measured", "CAREER_LIMIT_MSV"):
        assert text in page


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_bluetooth_heart_rate_messages_are_decoded_and_summarised(api_client: TestClient) -> None:
    code = _page_functions(api_client, ["parseHeartRateMeasurement", "bleSummary"])
    script = f"""{code}
const eight = new DataView(new ArrayBuffer(2)); eight.setUint8(1, 64);
const sixteen = new DataView(new ArrayBuffer(3)); sixteen.setUint8(0, 1); sixteen.setUint16(1, 310, true);
console.log(JSON.stringify([parseHeartRateMeasurement(eight), parseHeartRateMeasurement(sixteen),
  parseHeartRateMeasurement(new DataView(new ArrayBuffer(1))),
  bleSummary([70, 71, 72, 73, 74, 72]), bleSummary([70, 0, 300])]));"""
    decoded = json.loads(subprocess.run(["node", "-e", script], capture_output=True, text=True, check=True).stdout)
    assert decoded[:3] == [64, 310, None]
    assert decoded[3] == {"ok": True, "bpm": 72} and decoded[4]["ok"] is False


def test_dashboard_has_bluetooth_option(api_client: TestClient) -> None:
    page = api_client.get("/").text
    for text in ('id="bleStart"', "requestDevice", "heart_rate_measurement", "wearable_device"):
        assert text in page
