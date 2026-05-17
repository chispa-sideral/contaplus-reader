"""Trial balance (sumas y saldos) computation tests for contaplus-reader (BAL-02).

Covers:
- Decimal accumulation avoids float binary representation errors (Pitfall 2)
- Saldo deudor / saldo acreedor derivation from summed debe/haber
- Grouping by cuenta (4-digit) vs. subcuenta (full)
- Descripcion from subcta_lookup on subcuenta-level output
- BalanceTable and BalanceRow return types
- Sorted output (ascending by code)

All tests in this file are RED: they will fail with ImportError until
Plan 03 implements _balance.py and models.py gains BalanceRow/BalanceTable.

Requirements: BAL-02
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from contaplus_reader._balance import compute_balance
from contaplus_reader.models import BalanceRow, BalanceTable, ContaPlusJournal, JournalRow


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_row(subcuenta: str, debe: float, haber: float) -> JournalRow:
    """Build a minimal JournalRow with the given subcuenta and amounts."""
    return JournalRow(
        fecha=datetime.date(2025, 1, 1),
        cuenta=subcuenta[:4],
        subcuenta=subcuenta,
        debe=debe,
        haber=haber,
        concepto=None,
    )


def _make_journal(*rows: JournalRow) -> ContaPlusJournal:
    """Wrap JournalRows in a ContaPlusJournal."""
    return ContaPlusJournal(rows=rows, skipped_memo=0)


# ---------------------------------------------------------------------------
# BAL-02: Decimal precision (Pitfall 2 — mandatory str() conversion)
# ---------------------------------------------------------------------------

def test_decimal_precision() -> None:
    """BAL-02: Decimal accumulation avoids float binary representation errors.

    0.1 + 0.2 in float = 0.30000000000000004.
    compute_balance must return Decimal('0.3') not the float approximation.
    """
    rows = [_make_row("4300000", 0.1, 0.0), _make_row("4300000", 0.2, 0.0)]
    journal = _make_journal(*rows)
    table = compute_balance(journal, by_subcuenta=True)
    assert table.rows[0].suma_debe == Decimal("0.3")


# ---------------------------------------------------------------------------
# BAL-02: Saldo deudor / saldo acreedor / signed saldo
# ---------------------------------------------------------------------------

def test_saldo_deudor_when_debe_exceeds_haber() -> None:
    """BAL-02: When suma_debe > suma_haber, saldo_deudor = diff, saldo_acreedor = 0."""
    rows = [_make_row("1000000", 100.0, 60.0)]
    journal = _make_journal(*rows)
    table = compute_balance(journal, by_subcuenta=False)
    assert len(table.rows) == 1
    br = table.rows[0]
    assert br.suma_debe == Decimal("100")
    assert br.suma_haber == Decimal("60")
    assert br.saldo_deudor == Decimal("40")
    assert br.saldo_acreedor == Decimal("0")
    assert br.saldo == Decimal("40")  # positive = deudor


def test_saldo_acreedor_when_haber_exceeds_debe() -> None:
    """BAL-02: When suma_haber > suma_debe, saldo_acreedor = diff, saldo_deudor = 0."""
    rows = [_make_row("4000000", 30.0, 80.0)]
    journal = _make_journal(*rows)
    table = compute_balance(journal, by_subcuenta=False)
    assert len(table.rows) == 1
    br = table.rows[0]
    assert br.saldo_deudor == Decimal("0")
    assert br.saldo_acreedor == Decimal("50")
    assert br.saldo == Decimal("-50")  # negative = acreedor


# ---------------------------------------------------------------------------
# BAL-02: Grouping by cuenta vs. subcuenta
# ---------------------------------------------------------------------------

def test_cuenta_level_grouping() -> None:
    """BAL-02: Two subcuentas with the same 4-digit prefix group to one cuenta row."""
    rows = [
        _make_row("4300000", 100.0, 0.0),
        _make_row("4300001", 50.0, 0.0),
    ]
    journal = _make_journal(*rows)
    table = compute_balance(journal, by_subcuenta=False)
    # Both subcuentas share cuenta "4300"
    assert len(table.rows) == 1
    assert table.rows[0].code == "4300"
    assert table.rows[0].suma_debe == Decimal("150")


def test_subcuenta_level_grouping() -> None:
    """BAL-02: In by_subcuenta=True mode, each subcuenta produces a separate row."""
    rows = [
        _make_row("4300000", 100.0, 0.0),
        _make_row("4300001", 50.0, 0.0),
    ]
    journal = _make_journal(*rows)
    table = compute_balance(journal, by_subcuenta=True)
    assert len(table.rows) == 2
    codes = {r.code for r in table.rows}
    assert "4300000" in codes
    assert "4300001" in codes


def test_by_subcuenta_descripcion() -> None:
    """BAL-02: subcuenta-level row has descripcion from subcta_lookup."""
    rows = [_make_row("4300000", 100.0, 0.0)]
    journal = _make_journal(*rows)
    subcta_lookup = {"4300000": "Clientes"}
    table = compute_balance(journal, by_subcuenta=True, subcta_lookup=subcta_lookup)
    assert len(table.rows) == 1
    assert table.rows[0].descripcion == "Clientes"


# ---------------------------------------------------------------------------
# BAL-02: Return type and level attribute
# ---------------------------------------------------------------------------

def test_returns_balance_table_type() -> None:
    """BAL-02: compute_balance returns a BalanceTable with correct level attribute."""
    journal = _make_journal(_make_row("4300000", 100.0, 0.0))
    table_cuenta = compute_balance(journal, by_subcuenta=False)
    assert isinstance(table_cuenta, BalanceTable)
    assert table_cuenta.level == "cuenta"

    table_sub = compute_balance(journal, by_subcuenta=True)
    assert isinstance(table_sub, BalanceTable)
    assert table_sub.level == "subcuenta"


# ---------------------------------------------------------------------------
# BAL-02: Sorted output
# ---------------------------------------------------------------------------

def test_sorted_output() -> None:
    """BAL-02: BalanceRows are sorted ascending by code."""
    rows = [
        _make_row("7000000", 0.0, 100.0),
        _make_row("1000000", 50.0, 0.0),
        _make_row("4300000", 100.0, 0.0),
    ]
    journal = _make_journal(*rows)
    table = compute_balance(journal, by_subcuenta=True)
    codes = [r.code for r in table.rows]
    assert codes == sorted(codes)
