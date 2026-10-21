const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const script = path.resolve(__dirname, '../.github/scripts/publish_pr_preview.cjs');
const HEAD = 'a'.repeat(40), BASE = 'b'.repeat(40), MERGE = 'c'.repeat(40);
const MARKER = '<!-- gps-kataster-pr-preview -->';

function fixture() {
  const repo = { id: 1, full_name: 'example/catalog' };
  const pr = {
    number: 7, state: 'open', merged: false, merge_commit_sha: MERGE,
    head: { sha: HEAD, repo, ref: 'feature' },
    base: { sha: BASE, repo, ref: 'main' },
  };
  const run = {
    id: 123, run_attempt: 2, workflow_id: 55, event: 'pull_request',
    display_title: 'PR export preview #7',
    path: '.github/workflows/pr-preview.yml', repository: repo, head_repository: repo,
    head_sha: HEAD, head_branch: 'feature', status: 'completed', conclusion: 'success',
    pull_requests: [{ number: 7, base: { sha: BASE }, head: { sha: HEAD } }],
  };
  const artifact = {
    id: 99, name: `pr-preview-7-${HEAD}-${BASE}-${MERGE}-2`, expired: false,
    expires_at: '2026-11-04T18:00:00Z', workflow_run: { id: 123, head_sha: HEAD },
  };
  const state = { pr, run, runs: [run], artifacts: [artifact], comments: [], writes: [], otherPRs: [] };
  const api = (fn) => async (args) => ({ data: await fn(args) });
  const github = { rest: {
    actions: {
      getWorkflowRun: api(() => state.run), getWorkflow: api(() => ({ id: 55 })),
      listWorkflowRuns: api(() => ({ workflow_runs: state.runs })),
      listWorkflowRunArtifacts: api(() => ({ artifacts: state.artifacts })),
    },
    pulls: { get: api(() => state.pr), list: api(() => [state.pr, ...state.otherPRs]) },
    repos: { getCommit: api(() => ({ parents: [{ sha: BASE }, { sha: HEAD }] })) },
    issues: {
      listComments: api(() => state.comments),
      createComment: api(args => { state.writes.push(['create', args]); return { id: 88 }; }),
      updateComment: api(args => { state.writes.push(['update', args]); return {}; }),
    },
  }};
  github.paginate = async (method, args) => {
    const { data } = await method(args);
    return Array.isArray(data) ? data : data.artifacts || data.workflow_runs;
  };
  const context = {
    repo: { owner: 'example', repo: 'catalog' }, serverUrl: 'https://github.com',
    payload: { workflow_run: { id: 123, run_attempt: 2 } },
  };
  async function publish() {
    assert.ok(fs.existsSync(script), 'publisher implementation is missing');
    return require(script)({ github, context });
  }
  return { state, publish };
}

test('successful build creates a comment containing the artifact and exact provenance', async () => {
  const { state, publish } = fixture();
  await publish();
  assert.equal(state.writes.length, 1);
  const [action, args] = state.writes[0];
  assert.equal(action, 'create');
  assert.equal(args.issue_number, 7);
  assert.ok(args.body.startsWith(MARKER));
  assert.ok(args.body.includes('/actions/runs/123/artifacts/99'));
  for (const sha of [HEAD, BASE, MERGE]) assert.ok(args.body.includes(sha));
  assert.ok(args.body.includes('2026-11-04T18:00:00Z'));
});

test('updates one bot comment and preserves human comments and PR body', async () => {
  const { state, publish } = fixture();
  state.pr.body = 'Human PR description';
  state.comments = [
    { id: 1, body: MARKER + '\nHuman text', user: { login: 'reader', type: 'User' } },
    { id: 2, body: MARKER + '\nOld ZIP', user: { login: 'github-actions[bot]', type: 'Bot' } },
  ];
  await publish();
  assert.equal(state.writes.length, 1);
  assert.equal(state.writes[0][0], 'update');
  assert.equal(state.writes[0][1].comment_id, 2);
  assert.equal(state.pr.body, 'Human PR description');
});

for (const status of ['in_progress', 'queued']) test(`${status} removes the old download link`, async () => {
  const { state, publish } = fixture();
  state.run.status = status; state.run.conclusion = null;
  await publish();
  assert.match(state.writes[0][1].body, /Budowanie/);
  assert.ok(!state.writes[0][1].body.includes('/artifacts/'));
});

for (const conclusion of ['failure', 'cancelled', 'timed_out', 'skipped']) test(`${conclusion} shows no ZIP`, async () => {
  const { state, publish } = fixture();
  state.run.conclusion = conclusion;
  await publish();
  assert.ok(state.writes[0][1].body.includes(conclusion));
  assert.ok(!state.writes[0][1].body.includes('/artifacts/'));
});

const ignoreCases = {
  'old head': s => { s.pr.head.sha = 'd'.repeat(40); },
  'old base': s => { s.pr.base.sha = 'd'.repeat(40); },
  'old merge': s => { s.pr.merge_commit_sha = 'd'.repeat(40); },
  'closed PR': s => { s.pr.state = 'closed'; },
  'wrong workflow': s => { s.run.workflow_id = 999; },
  'wrong event': s => { s.run.event = 'push'; },
  'missing numbered run name': s => { s.run.display_title = 'Unrelated run'; },
  'run name conflicting with PR association': s => { s.run.display_title = 'PR export preview #8'; },
  'wrong repository': s => { s.run.repository = { id: 2, full_name: 'evil/repo' }; },
  'old attempt event': s => { s.run.run_attempt = 3; },
  'newer run for same commit': s => { s.runs.push({ ...s.run, id: 124 }); },
};
for (const [name, mutate] of Object.entries(ignoreCases)) test(`ignores ${name}`, async () => {
  const { state, publish } = fixture(); mutate(state); await publish();
  assert.deepEqual(state.writes, []);
});

const badArtifacts = {
  'missing': s => { s.artifacts = []; },
  'expired': s => { s.artifacts[0].expired = true; },
  'wrong attempt': s => { s.artifacts[0].name = s.artifacts[0].name.replace(/-2$/, '-1'); },
  'wrong base': s => { s.artifacts[0].name = s.artifacts[0].name.replace(BASE, 'd'.repeat(40)); },
  'ambiguous': s => { s.artifacts.push({ ...s.artifacts[0], id: 100 }); },
};
for (const [name, mutate] of Object.entries(badArtifacts)) test(`does not link ${name} artifacts`, async () => {
  const { state, publish } = fixture(); mutate(state); await publish();
  assert.equal(state.writes.length, 1);
  assert.ok(!state.writes[0][1].body.includes('/artifacts/'));
});

test('fork run without pull_requests metadata is matched by live head repository and SHA', async () => {
  const { state, publish } = fixture();
  state.pr.head.repo = { id: 2, full_name: 'contributor/catalog' };
  state.run.head_repository = state.pr.head.repo;
  state.run.pull_requests = [];
  await publish();
  assert.equal(state.writes.length, 1);
  assert.ok(state.writes[0][1].body.includes('/artifacts/99'));
});

test('foreign fork with identical SHA cannot select a PR', async () => {
  const { state, publish } = fixture();
  state.run.pull_requests = [];
  state.run.head_repository = { id: 2, full_name: 'other/catalog' };
  await publish();
  assert.deepEqual(state.writes, []);
});

test('a newer run for another PR from the same branch does not suppress this result', async () => {
  const { state, publish } = fixture();
  state.runs.push({ ...state.run, id: 124, display_title: 'PR export preview #8',
    pull_requests: [{ number: 8, base: { sha: BASE }, head: { sha: HEAD } }] });
  await publish();
  assert.equal(state.writes.length, 1);
  assert.ok(state.writes[0][1].body.includes('/artifacts/99'));
});

test('an unassociated fork run targets only its numbered PR when two PRs share a head', async () => {
  const { state, publish } = fixture();
  state.run.pull_requests = [];
  state.otherPRs.push({ ...state.pr, number: 8, base: { ...state.pr.base, ref: 'other-base' } });
  await publish();
  assert.equal(state.writes.length, 1);
  assert.equal(state.writes[0][1].issue_number, 7);
});
