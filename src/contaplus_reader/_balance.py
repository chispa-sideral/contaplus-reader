"""Trial balance (sumas y saldos) computation — BAL-02.

compute_balance() aggregates a ContaPlusJournal into a BalanceTable using
Decimal accumulation to avoid float binary representation errors (Pitfall 2).

Decision refs:
  BAL-02: Decimal(str(float)) accumulation — mandatory; never Decimal(float_value).
  D-08: saldo_deudor = max(sd - sh, 0); saldo_acreedor = max(sh - sd, 0);
        saldo = sd - sh (positive = deudor, negative = acreedor).
"""

from __future__ import annotations

import logging
from collections import defaultdict
from decimal import Decimal

from contaplus_reader.models import BalanceRow, BalanceTable, ContaPlusJournal

logger = logging.getLogger("contaplus_reader._balance")

_ZERO = Decimal("0")


def compute_balance(
    journal: ContaPlusJournal,
    *,
    by_subcuenta: bool = False,
    subcta_lookup: dict[str, str | None] | None = None,
) -> BalanceTable:
    """Compute the trial balance (sumas y saldos) from a validated journal.

    Operates on already-validated ContaPlusJournal.rows — no I/O, no error wrapping.
    Any exception propagates naturally.

    Args:
        journal: Validated ContaPlusJournal (from _read_dbf_path or read()).
        by_subcuenta: If True, group by full subcuenta code; if False (default),
                      group by 4-digit cuenta code (subcuenta[:4]).
        subcta_lookup: Optional dict mapping subcuenta code -> description.
                       Used to populate BalanceRow.descripcion when by_subcuenta=True.
                       Ignored when by_subcuenta=False.

    Returns:
        BalanceTable with rows sorted ascending by code.
        level="cuenta" when by_subcuenta=False; level="subcuenta" when True.
    """
    # BAL-02: use Decimal accumulators — never operate on raw float values
    debe_acc: dict[str, Decimal] = defaultdict(lambda: _ZERO)
    haber_acc: dict[str, Decimal] = defaultdict(lambda: _ZERO)

    for row in journal.rows:
        key = row.subcuenta if by_subcuenta else row.cuenta
        # BAL-02: Decimal(str(float)) is mandatory — Decimal(float_value) introduces
        # the same binary representation errors we are trying to avoid.
        debe_acc[key] += Decimal(str(row.debe))
        haber_acc[key] += Decimal(str(row.haber))

    all_keys = sorted(set(debe_acc.keys()) | set(haber_acc.keys()))

    result: list[BalanceRow] = []
    for key in all_keys:
        sd = debe_acc[key]
        sh = haber_acc[key]
        saldo_deudor = max(sd - sh, _ZERO)
        saldo_acreedor = max(sh - sd, _ZERO)
        saldo = sd - sh

        # Descripcion is only meaningful at subcuenta level; ignore for cuenta grouping.
        descripcion: str | None = None
        if by_subcuenta and subcta_lookup is not None:
            descripcion = subcta_lookup.get(key)

        result.append(
            BalanceRow(
                code=key,
                suma_debe=sd,
                suma_haber=sh,
                saldo_deudor=saldo_deudor,
                saldo_acreedor=saldo_acreedor,
                saldo=saldo,
                descripcion=descripcion,
            )
        )

    level = "subcuenta" if by_subcuenta else "cuenta"
    logger.debug(
        "compute_balance: %d %s rows computed from %d journal rows",
        len(result),
        level,
        len(journal.rows),
    )
    return BalanceTable(rows=tuple(result), level=level)
