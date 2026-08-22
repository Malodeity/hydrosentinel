"""
Admins currently have no way to get WSA or report data out of the app except
by reading the UI table by table. A CSV export lets them hand data to
compliance, government partners, or a spreadsheet without scraping the page.
"""
import csv
import io


def test_wsa_csv_export_requires_admin(client):
    resp = client.get("/wsa/export.csv")
    assert resp.status_code == 401


def test_wsa_csv_export_returns_csv(client, auth_headers, sample_wsa):
    resp = client.get("/wsa/export.csv", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    rows = list(csv.reader(io.StringIO(resp.text)))
    header = rows[0]
    assert "name" in header
    assert "province" in header
    assert "risk_level" in header

    name_col = header.index("name")
    names = [row[name_col] for row in rows[1:]]
    assert sample_wsa.name in names


def test_reports_csv_export_requires_admin(client):
    resp = client.get("/reports/export.csv")
    assert resp.status_code == 401


def test_reports_csv_export_returns_csv(client, auth_headers, sample_wsa):
    client.post(
        "/reports",
        data={"wsa_id": str(sample_wsa.id), "issue_type": "leak", "description": "Test leak", "lat": "-26.2", "lng": "28.1"},
    )

    resp = client.get("/reports/export.csv", headers=auth_headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]

    rows = list(csv.reader(io.StringIO(resp.text)))
    header = rows[0]
    assert "reference_code" in header
    assert "issue_type" in header
    assert "case_status" in header
    assert len(rows) >= 2
