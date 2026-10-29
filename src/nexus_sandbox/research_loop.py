"""Bounded research-frontier controller; trusted read-only callbacks required.

No search provider, scheduler, credential, source evaluation model or live writes
are installed. A callback assessment is not independently proven by this module.
"""
import copy
import json


def require(condition):
    if not condition:
        raise ValueError('Research state or assessment invalid')


def text(value):
    return type(value) is str and bool(value.strip()) and len(value) <= 20000


def binding_ok(binding):
    require(type(binding) is dict and set(binding) ==
            {'mission_id', 'source_revision', 'policy_revision', 'code_revision'})
    require(all(text(value) for value in binding.values()))


def question_ok(question):
    require(type(question) is dict and set(question) == {'id', 'question', 'scope_reason'})
    require(all(text(value) for value in question.values()))


def same(left, right):
    # Strict JSON comparison preserves bool/int distinctions and rejects NaN.
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(
        right, sort_keys=True, allow_nan=False)


def initial_state(binding, questions):
    binding_ok(binding)
    require(type(questions) is list and 0 < len(questions) <= 100)
    for question in questions:
        question_ok(question)
    require(len({q['id'] for q in questions}) == len(questions))
    return dict(binding=copy.deepcopy(binding), questions=copy.deepcopy(questions),
                findings={}, evidence={}, connections=[], history=[], pending=None)


def validate_state(state, binding):
    require(type(state) is dict and set(state) ==
            {'binding', 'questions', 'findings', 'evidence', 'connections', 'history', 'pending'})
    require(same(state['binding'], binding))
    require(type(state['questions']) is list and 0 < len(state['questions']) <= 100)
    for question in state['questions']:
        question_ok(question)
    ids = {q['id'] for q in state['questions']}
    require(len(ids) == len(state['questions']))
    require(type(state['findings']) is dict and set(state['findings']) <= ids)
    for finding in state['findings'].values():
        require(type(finding) is dict and set(finding) == {'disposition', 'reason'})
        require(finding['disposition'] in ('RESOLVED', 'UNPRODUCTIVE', 'BLOCKED')
                and text(finding['reason']))
    require(type(state['evidence']) is dict and len(state['evidence']) <= 1000)
    for evidence_id, evidence in state['evidence'].items():
        evidence_ok(evidence)
        require(evidence_id == evidence['id'])
    require(type(state['connections']) is list and len(state['connections']) <= 1000)
    for connection in state['connections']:
        connection_ok(connection, state['evidence'])
    require(type(state['history']) is list and len(state['history']) <= 1000)
    for entry in state['history']:
        require(type(entry) is dict and set(entry) == {'question_id', 'assessment'})
        require(entry['question_id'] in ids)
        assessment_ok(entry['assessment'])
    require(state['pending'] is None or (type(state['pending']) is str
            and state['pending'] in ids and state['pending'] not in state['findings']))


def evidence_ok(evidence):
    require(type(evidence) is dict and set(evidence) ==
            {'id', 'source_ref', 'claim', 'classification'})
    require(all(text(value) for value in evidence.values()))
    require(evidence['classification'] in
            ('SOURCE_CLAIM', 'OBSERVATION', 'INTERPRETATION', 'HYPOTHESIS', 'CONTRADICTION'))


def connection_ok(connection, evidence):
    require(type(connection) is dict and set(connection) ==
            {'statement', 'classification', 'evidence_ids', 'counterexamples'})
    require(text(connection['statement']) and connection['classification'] in
            ('ANALOGY', 'HYPOTHESIS', 'SUPPORTED_RELATION'))
    require(type(connection['evidence_ids']) is list and bool(connection['evidence_ids'])
            and all(type(x) is str and x in evidence for x in connection['evidence_ids']))
    require(type(connection['counterexamples']) is list
            and all(text(x) for x in connection['counterexamples']))


def assessment_ok(assessment):
    require(type(assessment) is dict and set(assessment) ==
            {'disposition', 'reason', 'attempted_queries', 'evidence', 'followups', 'connections'})
    require(assessment['disposition'] in ('RESOLVED', 'UNPRODUCTIVE', 'BLOCKED'))
    require(text(assessment['reason']))
    require(type(assessment['attempted_queries']) is list
            and 0 < len(assessment['attempted_queries']) <= 100
            and all(text(x) for x in assessment['attempted_queries']))
    require(type(assessment['evidence']) is list and len(assessment['evidence']) <= 100)
    for evidence in assessment['evidence']:
        evidence_ok(evidence)
    require(type(assessment['followups']) is list and len(assessment['followups']) <= 100)
    for question in assessment['followups']:
        question_ok(question)
    require(type(assessment['connections']) is list and len(assessment['connections']) <= 100)


def apply_assessment(state, assessment):
    """Apply an assessment only to the saved pending question, transactionally.

    Also usable by an authorized caller to reconcile a retained pending result;
    this does not authorize rerunning an interrupted callback or inventing evidence.
    """
    assessment_ok(assessment)
    candidate = copy.deepcopy(state)
    pending = candidate['pending']
    require(pending is not None)
    for evidence in assessment['evidence']:
        old = candidate['evidence'].get(evidence['id'])
        require(old is None or same(old, evidence))
        candidate['evidence'][evidence['id']] = copy.deepcopy(evidence)
    questions = {q['id']: q for q in candidate['questions']}
    for question in assessment['followups']:
        require(question['id'] not in questions or same(questions[question['id']], question))
        if question['id'] not in questions:
            questions[question['id']] = question
            candidate['questions'].append(copy.deepcopy(question))
    for connection in assessment['connections']:
        connection_ok(connection, candidate['evidence'])
        if connection not in candidate['connections']:
            candidate['connections'].append(copy.deepcopy(connection))
    candidate['findings'][pending] = dict(disposition=assessment['disposition'],
                                         reason=assessment['reason'])
    candidate['history'].append(dict(question_id=pending, assessment=copy.deepcopy(assessment)))
    candidate['pending'] = None
    validate_state(candidate, state['binding'])
    return candidate


def run_research(binding, research, save, read, *, max_steps=5):
    """Continue all current questions and newly discovered in-scope followups.

    Caller must save an initial state explicitly. Checkpoint write/read failure
    holds; callback interruption leaves pending intent and never blindly retries.
    BLOCKED findings remain recorded while other feasible questions are pursued.
    Only the trusted caller can assess scope/evidence quality or reopen a finding.
    """
    binding_ok(binding)
    require(type(max_steps) is int and 0 < max_steps <= 100)
    require(all(callable(x) for x in (research, save, read)))
    binding = copy.deepcopy(binding)
    state = None
    def persist(candidate):
        save(binding['mission_id'], copy.deepcopy(candidate))
        observed = read(binding['mission_id'])
        validate_state(observed, binding)
        require(same(observed, candidate))
    try:
        state = copy.deepcopy(read(binding['mission_id']))
        validate_state(state, binding)
        if state['pending'] is not None:
            return dict(status='BLOCKED_RECONCILE', state=state)
        steps = 0
        while True:
            remaining = [q for q in state['questions'] if q['id'] not in state['findings']]
            if not remaining:
                blocked = any(x['disposition'] == 'BLOCKED' for x in state['findings'].values())
                return dict(status='BLOCKED' if blocked else 'FRONTIER_EXHAUSTED', state=state)
            if steps >= max_steps:
                return dict(status='PAUSED_BUDGET', state=state)
            question = copy.deepcopy(remaining[0])
            candidate = copy.deepcopy(state)
            candidate['pending'] = question['id']
            persist(candidate)  # Intent read back before research invocation.
            state = candidate
            assessment = research(question, copy.deepcopy(state))
            candidate = apply_assessment(state, assessment)
            persist(candidate)
            state = candidate
            steps += 1
    except Exception:
        # Returned state is only the last confirmed copy; inspect actual storage
        # before recovery if a save may have succeeded without verified readback.
        return dict(status='BLOCKED_CHECKPOINT_OR_RESEARCH', state=state)
