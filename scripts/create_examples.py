"""Rebuild the synthetic invoice and its linked example DTOs."""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXAMPLES = ROOT / "contracts/examples"
D, F, P, E, S, R1, R2 = [f"00000000-0000-4000-8000-{n:012d}" for n in range(1, 8)]
NOW = "2026-10-29T10:00:00Z"
# CSV is one of the supported document formats and needs no PDF generation tool.
CSV = (
    "invoiceNumber,supplier,issueDate,buyer,purchaseOrder,"
    "description,quantity,unitPriceEUR,totalEUR\n"
    "DEMO-2026-001,Demo Paper s.r.o.,2026-10-20,Demo Grant Association,,"
    "Workshop notebooks,2.00,12.50,25.00\n"
    ",,,,,Training materials,3.00,10.00,30.00\n"
    ",,,,,TOTAL,,,55.00\n"
)
(EXAMPLES / "synthetic-invoice.csv").write_text(CSV)


def write(name, value):
    (EXAMPLES / f"{name}.json").write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")


scalar = [
    ("invoice_number", "Číslo faktúry", "string", "DEMO-2026-001", True),
    ("supplier", "Dodávateľ", "string", "Demo Paper s.r.o.", True),
    ("issue_date", "Dátum vystavenia", "date", "2026-10-20", True),
    ("buyer", "Odberateľ", "string", "Demo Grant Association", True),
    ("purchase_order", "Objednávka", "string", None, False),
    ("total", "Celková suma", "money", {"amount": "55.00", "currency": "EUR"}, True),
]
columns = [
    ("description", "Popis", "string"),
    ("quantity", "Množstvo", "decimal"),
    ("unit_price", "Jednotková cena", "money"),
    ("line_total", "Suma", "money"),
]
form = {
    "id": F,
    "name": "Ukážkový grant",
    "isIllustrative": True,
    "originalJson": {"illustrative": True, "unknownConfiguration": {"preserved": True}},
    "fields": [
        {"tag": k, "label": label, "type": t, "required": required, "options": None}
        for k, label, t, value, required in scalar
    ],
    "tables": [
        {
            "tag": "items",
            "label": "Položky",
            "columns": [
                {"tag": k, "label": label, "type": t, "required": True, "options": None}
                for k, label, t in columns
            ],
        }
    ],
}
profile = {
    "id": P,
    "version": 1,
    "name": "Ukážková faktúra",
    "documentKind": "invoice",
    "formId": F,
    "scalarFields": [
        {
            "key": k,
            "label": label,
            "type": t,
            "description": label,
            "required": required,
            "targetTag": k,
        }
        for k, label, t, value, required in scalar
    ],
    "tableFields": [
        {
            "key": "items",
            "label": "Položky",
            "targetTag": "items",
            "writeMode": "append",
            "columns": [
                {
                    "key": k,
                    "label": label,
                    "type": t,
                    "description": label,
                    "required": True,
                    "targetTag": k,
                }
                for k, label, t in columns
            ],
        }
    ],
}
warning = {
    "code": "MISSING_OPTIONAL_VALUE",
    "message": "Purchase order is not provided",
    "fieldKey": "purchase_order",
    "tableKey": None,
    "rowId": None,
}
write("form", form)
write("profile", profile)
write(
    "document",
    {
        "id": D,
        "filename": "synthetic-invoice.csv",
        "mediaType": "text/csv",
        "status": "ready",
        "contentHash": hashlib.sha256(CSV.encode()).hexdigest(),
        "duplicateOf": None,
        "createdAt": NOW,
        "pageCount": None,
        "warnings": [],
        "error": None,
    },
)
units = [
    {"id": f"row-{n}", "text": line, "page": None, "sheet": "invoice", "cell": f"A{n}:I{n}"}
    for n, line in enumerate(CSV.splitlines(), 1)
]
write("normalized-document", {"documentId": D, "units": units})


def source(quote, row=2):
    return [
        {
            "documentId": D,
            "unitId": f"row-{row}",
            "quote": quote,
            "page": None,
            "sheet": "invoice",
            "cell": f"A{row}:I{row}",
        }
    ]


fields = [
    {
        "key": k,
        "type": t,
        "value": value,
        "status": "missing" if value is None else "found",
        "sources": []
        if value is None
        else source(value["amount"] if t == "money" else value, 4 if k == "total" else 2),
    }
    for k, label, t, value, required in scalar
]
rows = []
for row_id, n, description, quantity, price, total in [
    (R1, 2, "Workshop notebooks", "2.00", "12.50", "25.00"),
    (R2, 3, "Training materials", "3.00", "10.00", "30.00"),
]:
    values = [
        description,
        quantity,
        {"amount": price, "currency": "EUR"},
        {"amount": total, "currency": "EUR"},
    ]
    rows.append(
        {
            "rowId": row_id,
            "cells": [
                {
                    "key": k,
                    "type": t,
                    "value": value,
                    "status": "found",
                    "sources": source(value["amount"] if t == "money" else value, n),
                }
                for (k, label, t), value in zip(columns, values, strict=True)
            ],
        }
    )
write(
    "extraction",
    {
        "id": E,
        "documentId": D,
        "profileId": P,
        "profileVersion": 1,
        "status": "ready",
        "mode": "fixture",
        "fields": fields,
        "tables": [{"key": "items", "rows": rows}],
        "warnings": [warning],
        "error": None,
        "createdAt": NOW,
    },
)
review_fields = [{"key": f["key"], "value": f["value"]} for f in fields]
# Human correction supplies data absent from the source without altering extraction evidence.
review_fields[4]["value"] = "HUMAN-PO-001"
review_rows = [
    {
        "rowId": row["rowId"],
        "cells": [{"key": cell["key"], "value": cell["value"]} for cell in row["cells"]],
    }
    for row in rows
]
ack = hashlib.sha256(
    json.dumps(warning, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
).hexdigest()
write(
    "review",
    {
        "extractionId": E,
        "revision": 2,
        "status": "confirmed",
        "fields": review_fields,
        "tables": [{"key": "items", "rows": review_rows}],
        "acknowledgedWarnings": [ack],
        "confirmedAt": NOW,
    },
)
write(
    "submission",
    {
        "id": S,
        "reviewId": E,
        "reviewRevision": 2,
        "mode": "export",
        "targetContext": {"applicationId": None},
        "status": "prepared",
        "payload": {
            "formId": F,
            "profileId": P,
            "profileVersion": 1,
            "fields": [{"targetTag": f["key"], "value": f["value"]} for f in review_fields],
            "tables": [
                {
                    "targetTag": "items",
                    "writeMode": "append",
                    "rows": [
                        {
                            "rowId": row["rowId"],
                            "values": {c["key"]: c["value"] for c in row["cells"]},
                        }
                        for row in review_rows
                    ],
                }
            ],
        },
        "externalReceipt": None,
        "createdAt": NOW,
        "error": None,
    },
)
