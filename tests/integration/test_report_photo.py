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
