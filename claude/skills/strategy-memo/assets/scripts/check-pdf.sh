#!/usr/bin/env bash
# Scan rendered PDF for unrendered Python inline code.
# Quarto inline expressions like `{python} var_name` that fail to render
# appear literally in the PDF as "{python} var_name". This catches them.
#
# Usage: ./scripts/check-pdf.sh
# Run automatically by: just check

set -euo pipefail

DOC="${1:-pre-read}" # ← pass doc name as arg, or set default here
PDF="${DOC}.pdf"

if [[ ! -f "$PDF" ]]; then
	echo "ERROR: $PDF not found. Run 'just render' first." >&2
	exit 1
fi

# Extract text from PDF and search for unrendered Python expressions
HITS=$(pdftotext "$PDF" - 2>/dev/null | grep -c '{python}' || true)

if [[ "$HITS" -gt 0 ]]; then
	echo "ERROR: Found $HITS unrendered Python expression(s) in $PDF" >&2
	echo ""
	echo "Occurrences:"
	pdftotext "$PDF" - 2>/dev/null | grep -n '{python}' >&2 || true
	echo ""
	echo "Check for:"
	echo "  - Variables not defined in the key-numbers cell"
	echo "  - Inline expressions outside code-executed cells"
	echo "  - Cells with execute: false or errors during render"
	exit 1
fi

echo "✓ No unrendered Python expressions found in $PDF"
