"""Synthetic extraction envelopes only; no assumptions about incoming customer files."""
import copy
import hashlib
import json

import pytest
import yaml

from bridgeflow.config import REPO_ROOT
from bridgeflow.documents import evaluate_document
from bridgeflow.schemas import SourceRef

POLICY = REPO_ROOT / 'data/quotation_demo/dictionary.yaml'


@pytest.fixture
def case():
    raw = POLICY.read_text()
    config = yaml.safe_load(raw)['quotation']
    declaration = SourceRef(department='procurement', filename=POLICY.name,
        paragraph='quotation', excerpt='quotation:', document_sha256=hashlib.sha256(raw.encode()).hexdigest())
    values = {'order_quantity': '10', 'material_cost': '100', 'material_usage': '2',
        'processing_hours': '0.5', 'processing_rate': '40', 'available_capacity': '8',
        'payment_history': '30', 'payment_request': '30', 'delivery_request': '14', 'delivery_commitment': '10'}
    facts = {}
    for key, spec in config['inputs'].items():
        text = f'Synthetic evidence for {key}: {values[key]} {spec["unit"]}'
        facts[key] = {'status': 'extracted', 'value': values[key], 'unit': spec['unit'],
            'sources': [SourceRef(department=spec['owner'], batch='transaction-a', filename=f'{key}.synthetic',
                paragraph='declared-fact', excerpt=text, document_sha256=hashlib.sha256(text.encode()).hexdigest()).model_dump()]}
    return config, {'id': 'transaction-a', 'status': 'extracted', 'facts': facts}, declaration


def test_cost_arithmetic_and_every_numeric_field_has_original_evidence(case):
    _config, document, declaration = case
    before = copy.deepcopy(case)
    result = evaluate_document(*case)
    assert result['status'] == 'draft', result
    fields = {field['metric']: field for field in result['fields']}
    assert fields['floor_price']['value'] == '220.00'
    assert fields['target_price']['value'] == '244.45'
    assert fields['stretch_price']['value'] == '275.00'
    assert fields['target_total']['value'] == '2444.50'
    for field in fields.values():
        assert field['sources'] and field['source_count'] >= len(field['sources'])
        assert len(field['sources']) <= 5
        for ref in field['sources']:
            assert ref['batch'] == document['id']
            assert ref['filename'] and ref['paragraph'] and ref['excerpt'] and ref['document_sha256']
            assert ref['row'] is None
    assert result['execution_status'] == 'not_approved_not_sent'
    assert result['declaration'] == declaration.model_dump()
    assert case == before
    document['facts']['material_cost']['value'] = '110'
    text = 'Synthetic evidence for material_cost: 110 SGD/kg'
    document['facts']['material_cost']['sources'][0].update(excerpt=text, document_sha256=hashlib.sha256(text.encode()).hexdigest())
    changed = evaluate_document(*case)
    assert changed['document_digest'] != result['document_digest']
    assert next(f for f in changed['fields'] if f['metric'] == 'floor_price')['value'] == '240.00'


def test_missing_cost_capacity_and_history_are_all_named_without_any_prices(case):
    config, document, declaration = case
    missing = {'material_cost', 'available_capacity', 'payment_history'}
    for key in missing:
        del document['facts'][key]
    result = evaluate_document(config, document, declaration)
    assert result['status'] == 'refused'
    assert result['fields'] == result['checks'] == []
    assert {r['field'] for r in result['refusals']} == missing
    assert all(r['code'] == 'missing_input' and r['decision_owner'] for r in result['refusals'])
    assert {r['title'] for r in result['refusals']} == {config['inputs'][key]['title'] for key in missing}


@pytest.mark.parametrize('value', ['NaN', 'Infinity', '-1', '1e100000', 'unknown', None])
def test_invalid_cost_is_refused(case, value):
    case[1]['facts']['material_cost']['value'] = value
    result = evaluate_document(*case)
    assert result['status'] == 'refused' and not result['fields']


@pytest.mark.parametrize('change,code', [
    ({'status': 'ambiguous'}, 'extraction_failed'),
    ({'sources': []}, 'missing_source'),
    ({'unit': 'USD/kg'}, 'unit_mismatch'),
    ({'sources': [{'department': 'procurement', 'filename': 'contract'}]}, 'invalid_extraction'),
])
def test_extraction_and_units_fail_closed(case, change, code):
    case[1]['facts']['material_cost'].update(change)
    result = evaluate_document(*case)
    assert result['status'] == 'refused' and not result['fields']
    assert code in {r['code'] for r in result['refusals']}


def test_text_citations_cannot_cross_transactions_or_document_versions(case):
    case[1]['facts']['material_cost']['sources'][0]['batch'] = 'transaction-b'
    assert evaluate_document(*case)['refusals'][0]['code'] == 'missing_source'
    case[1]['facts']['material_cost']['sources'][0]['batch'] = 'transaction-a'
    for key in ('material_cost', 'material_usage'):
        case[1]['facts'][key]['sources'][0]['filename'] = 'same-contract'
    assert 'source_version_conflict' in {r['code'] for r in evaluate_document(*case)['refusals']}


@pytest.mark.parametrize('key,value,check', [('available_capacity', '4', 'capacity'),
    ('payment_history', '60', 'payment_record'), ('payment_request', '60', 'payment_terms'),
    ('delivery_commitment', '20', 'delivery')])
def test_declared_thresholds_block_numbers_and_name_responsible_owner(case, key, value, check):
    case[1]['facts'][key]['value'] = value
    result = evaluate_document(*case)
    assert result['status'] == 'refused' and not result['fields']
    assert any(r['field'] == check and r['decision_owner'] for r in result['refusals'])


def test_dictionary_renaming_needs_no_python_field_hint(case):
    config, document, declaration = case
    for old in list(config['inputs']):
        new = f'任意声明_{old[::-1]}'
        config['inputs'][new] = config['inputs'].pop(old)
        document['facts'][new] = document['facts'].pop(old)
        config['metrics'] = json.loads(json.dumps(config['metrics']).replace(f'"key": "{old}"', f'"key": "{new}"'))
    assert evaluate_document(config, document, declaration)['status'] == 'draft'


@pytest.mark.parametrize('node', [
    {'op': 'metric', 'key': 'not_declared'}, {'op': 'metric', 'key': 'unit_cost'},
    {'op': 'divide', 'args': [{'op': 'input', 'key': 'material_cost'}, {'op': 'constant', 'value': 0}]},
])
def test_unknown_cyclic_and_divide_by_zero_formulas_are_refused(case, node):
    case[0]['metrics']['unit_cost']['expression'] = node
    assert evaluate_document(*case)['status'] == 'refused'


def test_constant_only_prices_cannot_claim_grounding(case):
    for key in ('floor_price', 'target_price', 'stretch_price'):
        case[0]['metrics'][key]['expression'] = {'op': 'constant', 'value': '999'}
    result = evaluate_document(*case)
    assert 'ungrounded_output' in {r['code'] for r in result['refusals']}
    assert not result['fields']


def test_limits_and_incomplete_extraction_never_fall_back_to_a_model(case):
    case[1]['status'] = 'failed'
    assert evaluate_document(*case)['refusals'][0]['code'] == 'extraction_failed'
    case[1]['status'] = 'extracted'
    case[1]['facts']['material_cost']['sources'][0]['excerpt'] = 'private raw content ' * 100
    assert evaluate_document(*case)['refusals'][0]['code'] == 'invalid_extraction'


def test_text_citation_is_actionable_and_existing_cell_citation_unchanged():
    assert SourceRef(department='procurement', filename='contract', page=2, paragraph='Payment', excerpt='Payment due', document_sha256='a' * 64).cite() == 'contract page 2 Payment'
    assert SourceRef(department='production', filename='sheet.csv', row=0, column='qty', source_row=2).cite() == 'sheet.csv row 2 column qty'


def test_read_only_catalogue_requires_auth_and_explicit_human_configuration(monkeypatch):
    from fastapi.testclient import TestClient

    from bridgeflow.api.main import app
    from bridgeflow.config import settings
    with TestClient(app) as client:
        assert client.get('/quotation/contract').json()['status'] == 'needs_configuration'
        monkeypatch.setattr(settings, 'field_dictionary_path', str(POLICY))
        result = client.get('/quotation/contract')
        assert result.status_code == 200
        assert result.json()['status'] == 'awaiting_samples'
        assert result.json()['contract']['inputs']['material_cost']['title'] == '材料采购成本'
        assert client.post('/quotation/contract', json={}).status_code == 405
        client.headers.clear()
        assert client.get('/quotation/contract').status_code == 401


def test_text_extension_does_not_allow_empty_citations():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        SourceRef(department='procurement')
    with pytest.raises(ValidationError):
        SourceRef(department='procurement', filename='contract', page=1)


def test_human_price_policy_cannot_silently_undercut_its_declared_cost_floor(case):
    case[0]['metrics']['target_price']['expression']['args'][1]['args'][1]['value'] = '-0.10'
    result = evaluate_document(*case)
    assert result['status'] == 'refused' and not result['fields']
    assert any(r['field'] == 'cost_floor' for r in result['refusals'])


def test_context_size_is_bounded_without_repeating_the_full_extraction(case):
    for fact in case[1]['facts'].values():
        fact['sources'] = [copy.deepcopy(fact['sources'][0]) for _ in range(4)]
        for ref in fact['sources']:
            ref['excerpt'] = 'x' * 480
    result = evaluate_document(*case)
    assert result['status'] == 'draft'
    assert any(field['truncated'] for field in result['fields'])
    assert all(len(field['sources']) <= 5 for field in result['fields'])
    assert len(json.dumps(result).encode()) < 60000
