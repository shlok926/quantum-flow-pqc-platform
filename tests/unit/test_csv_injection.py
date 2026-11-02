"""Quantum Flow Technologies — CSV Formula Injection Neutralization Unit Tests.

Verifies:
Leading characters '=', '+', '-', '@', '\\t', '\\r' are escaped with a leading single quote (')
to neutralize formula execution in spreadsheet applications.
"""

from packages.reports.exporter import export_assets_csv, sanitize_csv_field
from services.api.app.db.models.cryptographic_asset import CryptographicAsset


def test_sanitize_csv_cell_escapes_formula_prefixes() -> None:
    """Verify dangerous formula prefix characters are neutralized."""
    assert sanitize_csv_field("=CMD('calc')") == "'=CMD('calc')"
    assert sanitize_csv_field("+1+1") == "'+1+1"
    assert sanitize_csv_field("-5*2") == "'-5*2"
    assert sanitize_csv_field("@SUM(A1:A10)") == "'@SUM(A1:A10)"
    assert sanitize_csv_field("\tTABBED") == "'\tTABBED"
    assert sanitize_csv_field("\rRETURN") == "'\rRETURN"

    # Leading whitespace before formula triggers
    assert sanitize_csv_field("   =cmd|' /C calc'!A0") == "'   =cmd|' /C calc'!A0"
    assert sanitize_csv_field(" \t +1+1") == "' \t +1+1"
    assert sanitize_csv_field("  -2+5") == "'  -2+5"
    assert sanitize_csv_field(" \r @SUM(1)") == "' \r @SUM(1)"
    assert sanitize_csv_field("|cmd.exe") == "'|cmd.exe"
    assert sanitize_csv_field("   |cmd.exe") == "'   |cmd.exe"
    assert sanitize_csv_field("%username%") == "'%username%"

    # Benign string unchanged
    assert sanitize_csv_field("RSA-2048") == "RSA-2048"
    assert sanitize_csv_field("  benign text") == "  benign text"
    assert sanitize_csv_field(None) == ""
    assert sanitize_csv_field(2048) == "2048"


def test_export_assets_csv_neutralizes_injection() -> None:
    """Verify CSV exporter applies formula injection neutralization across columns."""
    malicious_asset = CryptographicAsset(
        asset_key="cert:sha256:test",
        asset_type="certificate",
        display_name="=HYPERLINK('http://evil.com')",
        algorithm_name="+AES-256",
        algorithm_family="-RSA",
    )

    csv_output = export_assets_csv([malicious_asset])
    lines = csv_output.strip().split("\n")

    assert len(lines) == 2  # header + row
    row = lines[1]
    # Check escaped cells
    assert "'=HYPERLINK" in row
    assert "'+AES-256" in row
    assert "'-RSA" in row
