#!/usr/bin/env python3
"""Continue independent readback; preserve first failed observer receipt.
The parent staged the helper mid-review, so the index ceased being the old32 input.
Use exact reversible output-only transformation bound to immutable input-r2 SHA.
"""
from pathlib import Path
p=Path(__file__).with_name('spec-q1-readback.py')
s=p.read_text()
a="check('scope_helper_only_output_argument_all_predicates_retained', hashlib.sha256(index).hexdigest()==old[path] and expected_scope==scope)"
b="""prior_scope=scope.replace(b'import argparse\\n', b'', 1).replace(b\"    parser = argparse.ArgumentParser()\\n    parser.add_argument('--out', type=Path, default=QA/'r6/evidence/frozen-scope-final')\\n    args = parser.parse_args()\\n    out = args.out.absolute()\\n    assert out.is_relative_to(QA/'r6/evidence')\", b\"    out = QA / 'r6/evidence/frozen-scope-final'\", 1)
check('scope_helper_only_output_argument_all_predicates_retained', hashlib.sha256(prior_scope).hexdigest()==old[path], prior_sha256=hashlib.sha256(prior_scope).hexdigest(), index_is_not_an_immutable_old_input=True)
r4p=ROOT/'qa/diag-mcp-027/RUNTIME-SPEC-R4.json'
r4=load(r4p)
check('original_R4_contract_preserved', sha(r4p)=='dd39b4fe6cfd32df5c09afd0b05355c733c61bc888767211f57bd6e2b5df0d04' and r4['passed'] is True and all(x['passed'] for x in r4['spec_checks']) and sha(ROOT/'qa/runtime_revision_host/DiagnosticRuntimeRevisionTest.kt.in')==r4['evidence']['runtime-revision-20261114T032020Z']['same_test_template_sha256'], sha256=sha(r4p), interpretation='Q1 adds trace follow-up only; old listener revision/default atomic writer/token/tool/address/SDK/stop contract retained')"""
assert s.count(a)==1
s=s.replace(a,b).replace("out=Q/'reviews/spec-q1-readback.json'", "out=Q/'reviews/spec-q1-readback-continuation.json'")
exec(compile(s,str(p)+'[continuation]', 'exec'),{'__name__':'__main__'})
