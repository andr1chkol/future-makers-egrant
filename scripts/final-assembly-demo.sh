#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
: "${TEST_DATABASE_URL:?Set an isolated egrant_test PostgreSQL URL}"
: "${FULL_PRODUCT_E2E_DATABASE_URL:?Set the dedicated egrant_test_full_product_e2e PostgreSQL URL}"
UV="${UV:-uv}"
"$UV" run pytest tests/integrations/test_full_product.py -q
make e2e-full-product
