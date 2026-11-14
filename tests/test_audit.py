import ast
import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contract_extraction_claim_audit import phrases
from contract_extraction_claim_audit.audit import audit, module_evidence, claims
from contract_extraction_claim_audit.__main__ import main

EXPECTED_POS = ('contract extraction', 'extract contracts', 'extracts contracts', 'extracting contracts', 'extract contract', 'extracts contract', 'extracting contract', 'contract parsing', 'contract parser', 'parse contracts', 'parses contracts', 'parse contract', 'parses contract', 'contract scanning', 'contract scanner', 'scan contracts', 'scans contracts', 'scan contract', 'scans contract', 'agreement extraction', 'extract agreements', 'extracts agreements', 'extracting agreements', 'extract agreement', 'extracts agreement', 'extracting agreement', 'agreement parsing', 'agreement parser', 'parse agreements', 'parses agreements', 'parse agreement', 'parses agreement', 'legal agreement extraction', 'extract legal agreements', 'extracts legal agreements', 'extracting legal agreements', 'extract legal agreement', 'extracts legal agreement', 'extracting legal agreement', 'contract data extraction', 'extract contract data', 'contract field extraction', 'contract document extraction', 'extract contract documents', 'contract terms extraction', 'extract contract terms', 'contract clause extraction', 'extract contract clauses', 'legal document extraction', 'extract legal documents')
EXPECTED_NEG = ('no contract extraction', 'does not extract contracts', 'does not extract contract', 'does not support contract extraction', 'without contract extraction', 'no agreement extraction', 'does not extract agreements', 'does not extract agreement', 'does not support agreement extraction', 'without agreement extraction', 'no legal agreement extraction', 'does not extract legal agreements', 'does not extract legal agreement', 'does not support legal agreement extraction', 'without legal agreement extraction', 'contract extraction not supported', 'agreement extraction not supported', 'legal agreement extraction not supported', 'no contract parser', 'does not parse contracts', 'does not parse contract', 'no contract scanner', 'does not scan contracts', 'does not scan contract')
EXPECTED_NAMES = ('extract_contract', 'extract_contracts', 'parse_contract', 'parse_contracts', 'extract_agreement', 'extract_agreements', 'parse_agreement', 'parse_agreements', 'extract_contract_data', 'parse_contract_data', 'contract_extraction', 'contract_extractor', 'contract_parser', 'agreement_extraction', 'extract_contract_info', 'parse_contract_info', 'contract_scan', 'contract_scanner', 'scan_contract', 'scan_contracts', 'extract_legal_agreement', 'parse_legal_agreement', 'extract_contract_terms', 'parse_contract_terms')

AZURE = 'from azure.ai.formrecognizer import DocumentAnalysisClient\nc = DocumentAnalysisClient()\n'


class AuditTests(unittest.TestCase):
    def project(self, prose='We extract contracts.', files=None, options=()):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'README.md').write_text(prose)
            for name, source in (files or {}).items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(source)
            result = audit(root)
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                code = main(['audit', temp, '--json', *options])
            return result, code, json.loads(output.getvalue())

    def test_phrase_oracle(self):
        tree = ast.parse(Path(phrases.__file__).read_text())
        parsed = {n.targets[0].id: ast.literal_eval(n.value) for n in tree.body if isinstance(n, ast.Assign)}
        self.assertEqual(parsed['CONTRACTEXTRACTION'], EXPECTED_POS)
        self.assertEqual(parsed['NOCONTRACTEXTRACTION'], EXPECTED_NEG)
        self.assertEqual(parsed['GENERIC_NAMES'], EXPECTED_NAMES)
        self.assertEqual((len(EXPECTED_POS), len(EXPECTED_NEG), len(set(EXPECTED_NAMES))), (50, 24, 24))

    def test_bad(self):
        result, code, output = self.project(files={'app.py': 'import mindee'})
        self.assertEqual(code, 2)
        self.assertEqual(result['findings'][0]['rule'], 'documented-contract-extraction-claim-false')
        self.assertEqual(result['findings'][0]['severity'], 'HIGH')
        self.assertEqual(output['verdict'], 'FAIL')
        self.assertTrue(output['findings'][0]['message'])

    def test_good(self):
        self.assertEqual(self.project(files={'app.py': 'x.extract_contract()'})[1], 0)

    def test_denial(self):
        result, code, _ = self.project('does not extract contracts', {'app.py': 'x.extract_contract()'})
        self.assertEqual(code, 2)
        self.assertEqual([f['rule'] for f in result['findings']], ['documented-no-contract-extraction-claim-false'])
        self.assertEqual(result['findings'][0]['severity'], 'HIGH')

    def test_no_claim(self):
        self.assertEqual(self.project('A tool.', {'app.py': 'x.extract_contract()'})[1], 0)

    def test_no_source_positive(self):
        self.assertEqual(self.project()[1], 2)

    def test_no_source_denial(self):
        self.assertEqual(self.project('no contract extraction')[1], 0)

    def test_test_only_threshold(self):
        for name in ('tests/app.py', 'test_app.py', 'app_test.py'):
            with self.subTest(name=name):
                result, code, _ = self.project(files={name: 'x.extract_contract()'})
                self.assertEqual(code, 0)
                self.assertEqual(result['findings'][0]['severity'], 'MEDIUM')
                self.assertEqual(self.project(files={name: 'x.extract_contract()'}, options=['--fail-on', 'medium'])[1], 2)

    def test_fences(self):
        for marker in ('```', '~~~', '   ````'):
            self.assertEqual(claims(marker + '\nextract contracts\n' + marker.strip()), ([], []))
        self.assertTrue(claims('    ```\nextract contracts')[0])
        self.assertTrue(claims('`extract contracts`')[0])

    def test_normalization(self):
        self.assertEqual(claims("doesn't extract contracts"), ([], ['does not extract contracts']))
        self.assertTrue(claims('EXTRACT-CONTRACTS')[0])
        self.assertFalse(claims('preextract contractsuffix')[0])
        self.assertFalse(claims('extract\n\ncontracts')[0])
        for phrase in EXPECTED_NEG:
            self.assertEqual(claims(phrase), ([], [phrase]))
        for phrase in EXPECTED_POS:
            self.assertEqual(claims(phrase), ([phrase], []))

    def test_scope_split(self):
        self.assertEqual(self.project(files={'a.py': AZURE, 'b.py': 'c.begin_analyze_document("prebuilt-contract")'})[1], 2)

    def test_excluded_directories(self):
        for name in ('fixtures/app.py', 'docs/app.py', 'examples/app.py'):
            self.assertEqual(self.project(files={name: 'x.extract_contract()'})[1], 2)

    def test_doc_selection(self):
        self.assertEqual(self.project('neutral', {'nested/docs/page.md': 'extract contracts'})[1], 2)
        self.assertEqual(self.project('neutral', {'nested/page.md': 'extract contracts'})[1], 0)

    def test_symlinks(self):
        with tempfile.TemporaryDirectory() as temp, tempfile.TemporaryDirectory() as other:
            root = Path(temp)
            external = Path(other)
            (root / 'README.md').write_text('extract contracts')
            (external / 'app.py').write_text('x.extract_contract()')
            (root / 'app.py').symlink_to(external / 'app.py')
            (root / 'linked').symlink_to(external, target_is_directory=True)
            self.assertFalse(audit(root)['evidence']['production'])
            (root / 'README.md').unlink()
            (external / 'claim.md').write_text('extract contracts')
            (root / 'README.md').symlink_to(external / 'claim.md')
            self.assertEqual(audit(root)['verdict'], 'PASS')

    def test_ignore(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'README.md').write_text('extract contracts')
            (root / 'app.py').write_text('x.extract_contract()')
            self.assertEqual(audit(root, ['app.py'])['verdict'], 'FAIL')
            self.assertEqual(audit(root, ['README.md', 'app.py'])['verdict'], 'PASS')

    def test_usage_errors(self):
        for args in ([], ['audit', '--fail-on', 'MEDIUM'], ['audit', '--unknown'], ['audit', '.', '--ignore', 'a', 'b']):
            with self.subTest(args=args), contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    main(args)
                self.assertEqual(error.exception.code, 1)
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(main(['audit', '/nonexistent-r199-path']), 1)

    def test_version_and_module(self):
        process = subprocess.run([sys.executable, '-m', 'contract_extraction_claim_audit', '--version'], capture_output=True, text=True)
        self.assertEqual((process.returncode, process.stdout.strip()), (0, '0.1.0'))

    def test_console_configuration(self):
        config = Path(__file__).resolve().parents[1] / 'pyproject.toml'
        if config.exists():
            self.assertIn('contract-extraction-claim-audit = "contract_extraction_claim_audit.__main__:main"', config.read_text())

    def test_self_readme(self):
        readme = Path(__file__).resolve().parents[1] / 'README.md'
        if readme.exists():
            self.assertEqual(claims(readme.read_text()), ([], []))


def add_case(name, source, expected):
    def test(self):
        self.assertEqual(module_evidence(source), expected, source)
    setattr(AuditTests, 'test_' + name, test)


for index, name in enumerate(EXPECTED_NAMES):
    add_case('generic_attribute_%02d' % index, 'x.' + name + '()', True)
    add_case('generic_import_%02d' % index, 'from library import ' + name + ' as operation\noperation()', True)
    add_case('generic_bare_%02d' % index, name + '()', False)
    add_case('generic_shadow_%02d' % index, 'def ' + name + '(): pass\nx.' + name + '()', False)

for index, source in enumerate([
    AZURE + 'c.begin_analyze_document("prebuilt-contract")',
    'from azure.ai.documentintelligence import DocumentIntelligenceClient as D\nc=D()\nc.begin_analyze_document_from_url("prebuilt-contract")',
    AZURE + 'c.begin_analyze_document(model_id="prebuilt-contract")',
    'import azure.ai.formrecognizer as af\nc=af.DocumentAnalysisClient()\nx.begin_analyze_document("prebuilt-contract")',
    'import azure.ai.documentintelligence\nc=azure.ai.documentintelligence.DocumentIntelligenceClient()\nx.begin_analyze_document("prebuilt-contract")',
    'from azure.ai import formrecognizer as af\nc=af.DocumentAnalysisClient()\nx.begin_analyze_document("prebuilt-contract")',
]):
    add_case('azure_positive_%02d' % index, source, True)

for index, model in enumerate(['prebuilt-invoice', 'prebuilt-receipt', 'prebuilt-layout', 'prebuilt-read', 'prebuilt-idDocument', 'prebuilt-check.us', 'prebuilt-tax.us', 'prebuilt-bankStatement.us', 'prebuilt-payStub.us', 'prebuilt-healthInsuranceCard.us', 'prebuilt-businessCard', 'prebuilt-creditCard', 'prebuilt-contract.us', 'prebuilt-Contract', 'other']):
    add_case('azure_wrong_model_%02d' % index, AZURE + 'c.begin_analyze_document(' + repr(model) + ')', False)

for index, product in enumerate(['InvoiceV4', 'ReceiptV5', 'PassportV1', 'FinancialDocumentV1', 'BankCheckV1', 'BankAccountDetailsV2', 'PayslipV2', 'PayslipV3', 'HealthcareCardV1', 'BusinessCardV1', 'CustomV1', 'ContractV1']):
    add_case('mindee_product_%02d' % index, 'from mindee import Client, product\nc=Client()\nc.parse(product.' + product + ', input_doc)', False)

VERYFI = ('process_any_document process_any_document_url process_document process_document_url process_w2_document process_w9_document process_w8_document process_check process_check_url process_check_with_remittance process_check_with_remittance_url process_bank_statement_document process_bank_statement_document_url process_bussines_card_document process_bussines_card_document_url classify_document get_business_cards get_business_card delete_business_card process_contract_document process_contract_document_url').split()
for index, method in enumerate(VERYFI):
    add_case('veryfi_%02d' % index, 'from veryfi import Client\nc=Client()\nc.' + method + '(doc)', False)

NEGATIVE_SOURCES = [
    'import mindee', 'import veryfi', 'import azure.ai.formrecognizer',
    'from mindee import Client\nc=Client()', 'from veryfi import Client\nc=Client()', AZURE,
    'x.begin_analyze_document("prebuilt-contract")',
    'import azure\nc=azure.DocumentAnalysisClient()\nc.begin_analyze_document("prebuilt-contract")',
    'from other import DocumentAnalysisClient\nc=DocumentAnalysisClient()\nc.begin_analyze_document("prebuilt-contract")',
    'textract.analyze_document()', 'textract.analyze_expense()', 'textract.start_document_analysis()', 'textract.get_expense_analysis()',
    'pdfplumber.extract_text()', 'fitz.extract_text()', 'pypdf.extract_text()', 'PyPDF2.extract_text()', 'pdfminer.extract_text()',
    'pytesseract.image_to_string()', 'pandas.read_csv()', 'pandas.read_excel()',
    'camelot.read_pdf()', 'tabula.read_pdf()', 'tabula.convert_into()',
    'pdfplumber.extract_table()', 'pdfplumber.extract_tables()', 'pdfplumber.find_table()', 'pdfplumber.find_tables()', 'fitz.find_tables()',
    'import re\ntext=ocr.image_to_string(doc)\nfields={"title": re.search("Title: (.*)", text)}',
    'text="contract text"\nfields=text.split(":")',
    'import subprocess\nsubprocess.run(["mindee", "parse", "contract"])',
    'import subprocess\nsubprocess.run(["veryfi", "contract"])',
    '# x.extract_contract()\ns="x.extract_contract()"', 'x.extract_contract', 'x.extract_contract(',
    'from lib import extract_contract as run\nrun=lambda:None\nrun()',
    'from lib import extract_contract as run\nrun: object = None\nrun()',
    'from lib import extract_contract as run\nwith manager() as run:\n run()',
    'from lib import extract_contract as run\nasync def f():\n async with manager() as run:\n  run()',
    'class X:\n def extract_contract(self): pass\nx.extract_contract()',
    'class extract_contract: pass\nx.extract_contract()',
    'from azure.ai.formrecognizer import DocumentAnalysisClient\ndef DocumentAnalysisClient(): pass\nc=DocumentAnalysisClient()\nc.begin_analyze_document("prebuilt-contract")',
]
for index, source in enumerate(NEGATIVE_SOURCES):
    add_case('not_evidence_%02d' % index, source, False)

add_case('azure_similar_module_not_gate', 'import azure.ai.formrecognizer_fake\nc=azure.DocumentAnalysisClient()\nc.begin_analyze_document("prebuilt-contract")', False)
add_case('azure_rebound_import', 'import azure.ai.formrecognizer as af\naf = object()\nc=af.DocumentAnalysisClient()\nc.begin_analyze_document("prebuilt-contract")', False)
add_case('generic_module_alias', 'import library as lib\nlib.parse_contract_terms()', True)
add_case('generic_alias_local_definition', 'from library import extract_contract as run\ndef run(): pass\nrun()', False)

if __name__ == '__main__':
    unittest.main()
