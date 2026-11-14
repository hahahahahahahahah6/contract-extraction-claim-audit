# Documentation claim auditor

An offline static auditor comparing documentation promises with recognized calls in Python source. It reports unsupported promises and contradictions without executing project code. Requires Python 3.9 or newer; no runtime dependencies.

## Installation and usage

```sh
python3 -m pip install .
contract-extraction-claim-audit audit .
contract-extraction-claim-audit audit . --json --verbose --ignore build --ignore dist --fail-on medium
python3 -m contract_extraction_claim_audit audit .
contract-extraction-claim-audit --version
```

The repository defaults to the current directory. Repeatable ignore prefixes select relative subtrees. Exit 0 means PASS at the selected threshold, 2 means findings at that threshold, and 1 means usage or I/O error. The default threshold is high; medium also fails on evidence found only in tests. JSON includes verdict, findings with rule, severity, message and locations, and evidence paths. Verbose output lists evidence paths.

## Matching rules

Root README.md and Markdown files with a docs path component are checked. Fenced blocks using backticks or tildes with up to three leading spaces are excluded; inline code counts. Paragraphs split on blank lines. Normalization lowercases, expands contractions, replaces hyphens with spaces and collapses whitespace. Boundary matches use longest phrases first with alphabetical ties. Denial spans are removed before positive matching. Each family produces at most one finding.

Source is parsed with AST and never executed. Symlinks are excluded. Fixtures, docs and examples provide no evidence; tests count separately. Invalid syntax provides no evidence. Imports and aliases resolve within one module. Local function, method and class definitions shadow route names. Assignments, annotated assignments and context manager bindings shadow imported names. Bare imports and references do not count. Generic attribute calls accept any base; bare names require an imported recognized name. A positive promise without source fails; a denial without source passes.

The exact vocabulary and evidence rules follow as reference data.

```text
contract extraction
extract contracts
extracts contracts
extracting contracts
extract contract
extracts contract
extracting contract
contract parsing
contract parser
parse contracts
parses contracts
parse contract
parses contract
contract scanning
contract scanner
scan contracts
scans contracts
scan contract
scans contract
agreement extraction
extract agreements
extracts agreements
extracting agreements
extract agreement
extracts agreement
extracting agreement
agreement parsing
agreement parser
parse agreements
parses agreements
parse agreement
parses agreement
legal agreement extraction
extract legal agreements
extracts legal agreements
extracting legal agreements
extract legal agreement
extracts legal agreement
extracting legal agreement
contract data extraction
extract contract data
contract field extraction
contract document extraction
extract contract documents
contract terms extraction
extract contract terms
contract clause extraction
extract contract clauses
legal document extraction
extract legal documents
no contract extraction
does not extract contracts
does not extract contract
does not support contract extraction
without contract extraction
no agreement extraction
does not extract agreements
does not extract agreement
does not support agreement extraction
without agreement extraction
no legal agreement extraction
does not extract legal agreements
does not extract legal agreement
does not support legal agreement extraction
without legal agreement extraction
contract extraction not supported
agreement extraction not supported
legal agreement extraction not supported
no contract parser
does not parse contracts
does not parse contract
no contract scanner
does not scan contracts
does not scan contract

Generic names:
extract_contract, extract_contracts, parse_contract, parse_contracts, extract_agreement, extract_agreements, parse_agreement, parse_agreements, extract_contract_data, parse_contract_data, contract_extraction, contract_extractor, contract_parser, agreement_extraction, extract_contract_info, parse_contract_info, contract_scan, contract_scanner, scan_contract, scan_contracts, extract_legal_agreement, parse_legal_agreement, extract_contract_terms, parse_contract_terms

documented-contract-extraction-claim-false HIGH (MEDIUM with test-only evidence)
documented-no-contract-extraction-claim-false HIGH
DocumentAnalysisClient / DocumentIntelligenceClient construction +
begin_analyze_document / begin_analyze_document_from_url call with
model id exactly "prebuilt-contract" (pair, 1); import gate
azure.ai.formrecognizer or azure.ai.documentintelligence. Match is
case-sensitive and exact. NOTE: the model is GA in v4.0 (2024-11-30)
AND v3.1 — the Learn contract concept page states "This content
applies to: v3.1 (GA) | Latest version: v4.0 (GA)" and lists the
Contract model with model id "prebuilt-contract" for both. The tool
still counts the call, since it detects the call in source, not
whether the call succeeds against a current API version.

## mindee names (implementation MUST match exactly)

NO mindee route: mindee has no contract product in the Python
SDK. The 4.22.0 wheel, inspected 2026-11-13, contains no
contract product directory and no Contract product class (grep
"contract" across all wheel entry names returns no matches), so a
mindee parse with ANY product is NOT evidence.

## veryfi names (implementation MUST match exactly)

NO veryfi route: veryfi has no contract method in the Python
SDK. The 5.1.0 wheel, inspected 2026-11-13, contains no
process_contract_document / process_contract_document_url
method and no contracts module, so a veryfi call of ANY kind is
NOT evidence. Veryfi process_any_document / process_any_document_url
is generic AnyDocs configurable extraction, NOT evidence.

```

## Honest limitations

These reference notes explain ambiguity and exclusions.

```text
- The bare phrases "contract extraction" / "extract contract" /
  "extract contracts" are deliberately CONTRACTEXTRACTION phrases:
  in document-tool docs they almost always name contract
  extraction. But "contract" can also name a smart contract, a
  code contract, or a contract the tool merely stores, signs, or
  manages without extracting fields from it: a doc that means
  storing, signing, or managing contracts, not extracting fields
  from them, is a false positive; the tool flags the claim, only
  the code decides.
- "agreement extraction" / "extract agreement(s)" are
  deliberately phrases: the Azure model covers agreements as
  contracts. But "agreement" is a generic word — a doc can say
  "extract agreement" about reaching an agreement, a user
  agreement the tool merely displays, or a terms-of-service page
  the tool merely renders: a doc that means agreement in that
  sense, not extracting fields from an agreement document, is a
  false positive; the tool flags the claim, only the code decides.
- "legal agreement extraction" / "extract legal agreement(s)" /
  "legal document extraction" / "extract legal documents" are
  deliberately phrases: "legal document" can also name any legal
  paperwork the tool merely stores or files, and a "legal
  agreement" can be a clickwrap the tool merely records. The tool
  flags the claim; only the code decides.
- "contract terms extraction" / "extract contract terms" and
  "contract clause extraction" / "extract contract clauses" are
  deliberately phrases: "terms" can also mean terms of service
  the tool merely shows, and "clauses" can be template text the
  tool merely inserts. The tool flags the claim; only the code
  decides.
- "contract scanning" / "scan contract(s)" are deliberately
  phrases: "scanning" a contract can mean merely photographing
  it or OCRing it into raw text, with no structured field
  extraction. The tool flags the claim; only the code decides.
- A generic `extract_contract(` / `parse_contract(` /
  `extract_agreement(` call can name a string parser for text
  the user typed in rather than a document extractor: the tool
  counts the call, the claim plus the code decide — and a
  subprocess call invoking an external CLI is NOT evidence by
  design, so a thin wrapper that only calls subprocess fails.
- Azure `begin_analyze_document` with model id
  "prebuilt-contract" counts as evidence: the model is GA in
  v4.0 (2024-11-30) and v3.1 and the tool detects the client
  call in source, not whether the call succeeds against a
  current API version.
- Azure `begin_analyze_document` with "prebuilt-contract.us"
  is NOT detected: no such model id exists — the contract
  model id has no ".us" suffix (unlike the US document models
  prebuilt-tax.us / prebuilt-payStub.us /
  prebuilt-healthInsuranceCard.us / prebuilt-check.us /
  prebuilt-bankStatement.us).
- Azure `begin_analyze_document` with "prebuilt-Contract"
  is NOT detected: model ids are matched case-sensitively and
  exactly — "prebuilt-contract" (all lowercase) counts, capital
  C does not.
- Mindee `parse` with ANY product is NOT detected: mindee has no
  contract product in the Python SDK (4.22.0 wheel inspected
  2026-11-13), so no mindee parse can be a contract extraction
  operation.
- Veryfi `process_any_document` / `process_any_document_url` are
  NOT detected: AnyDocs is generic configurable extraction, not a
  contract operation.
- Veryfi `process_document` is NOT detected: it processes generic
  receipts and invoices. Only a contract method would count
  here, and none exists.
- Veryfi `process_w2_document` / `process_w9_document` /
  `process_w8_document` are NOT detected: tax forms are a separate
  document type covered by the tax-form family. Say so in the
  README.
- Veryfi `process_check` / `process_check_url` /
  `process_check_with_remittance` /
  `process_check_with_remittance_url` are NOT detected: checks are
  a separate document type covered by the bank-check family. Say
  so in the README.
- Veryfi `process_bank_statement_document` /
  `process_bank_statement_document_url` are NOT detected: bank
  statements are a separate document type covered by the
  bank-statement family's domain.
- Veryfi `process_bussines_card_document` /
  `process_bussines_card_document_url` are NOT detected: business
  cards are a separate document type covered by the
  business-card family.
- Veryfi `get_business_cards` / `get_business_card` /
  `delete_business_card` are NOT detected: retrieval and
  management, not extraction.
- Veryfi `classify_document` is NOT detected: classification, not
  extraction.
- Azure `begin_analyze_document` with "prebuilt-invoice" /
  "prebuilt-receipt" / "prebuilt-layout" / "prebuilt-idDocument" /
  "prebuilt-check.us" / "prebuilt-tax.us" /
  "prebuilt-bankStatement.us" / "prebuilt-payStub.us" /
  "prebuilt-healthInsuranceCard.us" / "prebuilt-businessCard" /
  "prebuilt-creditCard" is NOT detected, for the same reason:
  invoices, receipts, layouts, ID documents, checks, tax forms,
  bank statements, pay stubs, health insurance cards, business
  cards, and credit cards are separate document types covered by
  their own families.
- Mindee `parse` with InvoiceV4 / ReceiptV5 / PassportV1 /
  FinancialDocumentV1 / BankCheckV1 / BankAccountDetailsV2 /
  PayslipV2 / PayslipV3 / HealthcareCardV1 / BusinessCardV1 /
  CustomV1 is NOT detected: those are other document types, and
  mindee has no contract product at all.
- Textract `analyze_document` / `analyze_expense` /
  `start_document_analysis` / `get_expense_analysis` are NOT
  detected: generic document and expense analysis are not
  contract extraction, and Textract has no contract operation.
 
- A hand-rolled extraction from OCR text (`re.search` /
  `re.findall` on extracted text plus manual field assembly, no
  listed call) is NOT detected: the tool requires a listed call.
 
- The mindee CLI, the veryfi CLI, and any other external contract
  tool invoked through subprocess are NOT detected:
  subprocess calls invoking an external CLI are NOT evidence by
  design.
- Azure Document Intelligence, Mindee, and Veryfi are cloud APIs:
  the tool detects the client call in source, not whether
  credentials are configured or the call succeeds. Say so in the
  README.
- "extract contract title" / "extract parties" / "extract
  effective date" claims are NOT in the phrase lists: contract
  titles, parties, and dates are contract data points, not
  contract extraction claims on their own.
- Invoice extraction claims ("extract invoices", "invoice
  extraction"), receipt extraction claims ("extract receipts",
  "receipt extraction"), ID document extraction claims ("extract
  passports", "passport extraction"), bank check extraction claims
  ("extract bank checks", "check extraction"), bank statement
  extraction claims ("extract bank statements", "statement
  extraction"), tax form extraction claims ("extract tax forms",
  "extract w2 forms", "1099 extraction"), pay stub extraction
  claims ("extract pay stubs", "payslip extraction"), health
  insurance card extraction claims ("extract health insurance
  cards", "health insurance card extraction"), business card
  extraction claims ("extract business cards", "business card
  extraction"), and credit card extraction claims ("extract credit
  cards", "credit card extraction") are NOT in the phrase lists:
  this family covers contracts only.
- Contract management claims ("manage contracts", "sign contracts",
  "store contracts", "contract lifecycle management") are NOT in
  the phrase lists: managing, signing, or storing contracts is not
  extracting fields from them.
- As with every family: static pattern matching, not semantic
  judgement; dead code counts; alias chains the tracer cannot follow
  are missed; exact phrases only, not semantics; denial handling
  depends on the denial phrase list; each route must sit in a single
  module.

Additional exclusions: plain text through pdfplumber, fitz, pypdf, PyPDF2 or pdfminer; OCR through pytesseract; CSV/spreadsheets through pandas; tables through camelot, tabula, pdfplumber or fitz. Strings, comments, bare references and syntax-invalid files do not count.
```

## Differentiation

This checks documentation against an explicit call vocabulary. It does not validate SDK behavior, returned fields, service availability or credentials.

## Development

```sh
python3 -m unittest discover
python3 -m venv .venv
.venv/bin/python3 -m pip install build
.venv/bin/python3 -m build
```

Both distributions include the tests. The tool uses only the standard library, makes no network calls and writes only to standard output or standard error.
