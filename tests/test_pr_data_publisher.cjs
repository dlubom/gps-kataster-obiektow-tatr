'use strict';

const test = require('node:test');
const assert = require('node:assert/strict');
const publish = require('../.github/scripts/publish_pr_data.cjs');

const HEAD = '1'.repeat(40);
const BASE = '2'.repeat(40);
const MERGE = '3'.repeat(40);
const OTHER = '4'.repeat(40);
const START = '<!-- pr-data-preview:start -->';
const END = '<!-- pr-data-preview:end -->';

function existingBlock(runId = 10, attempt = 1) {
  return `${START}\nOld generated text\n<!-- pr-data-preview:state `
    + `${JSON.stringify({ run_id: runId, run_attempt: attempt })} -->\n${END}`;
}

function assertFreshPrEventRecovery(body) {
  assert.ok(body.includes('nowy commit'));
  assert.ok(body.includes('ponownie otwórz PR'));
  assert.ok(!body.includes('Uruchom ponownie eksport'));
}

function fixture(options = {}) {
  const repository = { id: 1, full_name: 'owner/catalog' };
  const run = {
    id: 10, event: 'pull_request', path: '.github/workflows/pr-data.yml',
    run_attempt: 1, repository, head_repository: { id: 1 }, head_branch: 'change',
    head_sha: HEAD, status: 'completed', conclusion: 'success', pull_requests: [{ number: 12 }],
    ...options.run,
  };
  let pull = {
    number: 12, state: 'open', body: 'Human description\n',
    head: { sha: HEAD, ref: 'change', repo: { id: run.head_repository.id } },
    base: { sha: BASE, repo: repository }, ...options.pull,
  };
  const artifact = {
    id: 99, name: `pr-data-12-h${HEAD}-b${BASE}-m${MERGE}-r10-a1`,
    expired: false, expires_at: '2099-10-20T00:00:00Z', ...options.artifact,
  };
  const updates = [];
  const calls = { runs: 0, pulls: 0, commits: 0, lists: 0, artifacts: 0 };
  const context = {
    repo: { owner: 'owner', repo: 'catalog' },
    payload: { repository, workflow_run: { id: 10, run_attempt: 1 }, ...options.payload },
  };
  const github = { rest: {
    actions: {
      async getWorkflowRun() {
        const response = options.runs?.[Math.min(calls.runs, options.runs.length - 1)] || run;
        calls.runs++;
        return { data: structuredClone(response) };
      },
      async listWorkflowRunArtifacts() {
        calls.artifacts++;
        return { data: { artifacts: structuredClone(options.artifacts || [artifact]) } };
      },
    },
    pulls: {
      async get() {
        const response = options.pulls?.[Math.min(calls.pulls, options.pulls.length - 1)] || pull;
        calls.pulls++;
        return { data: structuredClone(response) };
      },
      async list() {
        calls.lists++;
        return { data: structuredClone(options.listedPulls || [pull]) };
      },
      async update(args) {
        updates.push(structuredClone(args));
        pull = { ...pull, body: args.body };
        return { data: structuredClone(pull) };
      },
    },
    repos: {
      async getCommit() {
        calls.commits++;
        if (options.commitError) throw new Error('Unavailable');
        return { data: structuredClone(options.commit || {
          sha: MERGE, parents: [{ sha: BASE }, { sha: HEAD }],
        }) };
      },
    },
  } };
  github.paginate = async (method, args) => {
    const { data } = await method(args);
    return Array.isArray(data) ? data : data.artifacts;
  };
  const invoke = () => publish({ github, context, core: { info() {} } });
  return { invoke, run, pull, artifact, updates, calls, context, github };
}

test('publishes verified bundle with exact provenance and preserves human body', async () => {
  const f = fixture();
  assert.deepEqual(await f.invoke(), { updated: [12], skipped: [] });
  assert.equal(f.updates.length, 1);
  const body = f.updates[0].body;
  assert.ok(body.startsWith('Human description\n\n'));
  assert.ok(body.includes(`/actions/runs/10/artifacts/99)`));
  assert.ok(body.includes(HEAD) && body.includes(BASE) && body.includes(MERGE));
  assert.ok(body.includes('2099-10-20T00:00:00Z'));
  assert.ok(body.includes('zalogowania do GitHub'));
  assert.ok(body.includes('wskazanego HEAD'));
  assert.ok(!body.includes('aktualnego HEAD'));
  assert.ok(body.includes('"run_id":10,"run_attempt":1'));
  assert.equal(f.calls.commits, 1);
});

test('same successful event is idempotent', async () => {
  const f = fixture();
  await f.invoke();
  const second = await f.invoke();
  assert.equal(f.updates.length, 1);
  assert.deepEqual(second, { updated: [], skipped: [12] });
});

test('accepts documented workflow paths with optional ref suffix', async t => {
  for (const path of ['.github/workflows/pr-data.yml', '.github/workflows/pr-data.yml@main',
    '.github/workflows/pr-data.yml@refs/pull/12/merge']) {
    await t.test(path, async () => {
      const f = fixture({ run: { path } });
      assert.deepEqual(await f.invoke(), { updated: [12], skipped: [] });
    });
  }
});

test('rejects adjacent workflow filenames and empty ref suffixes', async t => {
  for (const path of ['.github/workflows/pr-data.yml@', '.github/workflows/pr-data.yml-other',
    '.github/workflows/pr-data.yml-other@main']) {
    await t.test(path, async () => {
      const f = fixture({ run: { path } });
      await f.invoke();
      assert.equal(f.updates.length, 0);
    });
  }
});

test('replaces one generated block while preserving exact prefix and suffix', async () => {
  const prefix = '## Human notes\r\nKeep whitespace.\n\n';
  const suffix = '\n\n## More notes\n  unchanged  \n';
  const f = fixture({ pull: { body: prefix + existingBlock(9) + suffix } });
  await f.invoke();
  assert.ok(f.updates[0].body.startsWith(prefix));
  assert.ok(f.updates[0].body.endsWith(suffix));
  assert.equal(f.updates[0].body.split(START).length - 1, 1);
  assert.ok(!f.updates[0].body.includes('Old generated text'));
});

test('handles an empty PR body', async () => {
  const f = fixture({ pull: { body: null } });
  await f.invoke();
  assert.ok(f.updates[0].body.startsWith(START));
});

test('does not publish for a stale head', async () => {
  const f = fixture({ pull: { head: { sha: OTHER, ref: 'change', repo: { id: 1 } } } });
  assert.deepEqual(await f.invoke(), { updated: [], skipped: [12] });
  assert.equal(f.updates.length, 0);
});

test('stale base replaces success with an explicit stale status and no download', async () => {
  const f = fixture({ pull: { base: { sha: OTHER, repo: { id: 1 } }, body: existingBlock(9) } });
  await f.invoke();
  assert.ok(f.updates[0].body.includes('zmieniła się baza PR'));
  assertFreshPrEventRecovery(f.updates[0].body);
  assert.ok(f.updates[0].body.includes(OTHER));
  assert.ok(!f.updates[0].body.includes('/artifacts/'));
  assert.equal(f.calls.commits, 0);
});

test('a newer stored run or attempt cannot be overwritten', async t => {
  for (const [id, attempt] of [[11, 1], [10, 2]]) {
    await t.test(`${id}/${attempt}`, async () => {
      const f = fixture({ pull: { body: existingBlock(id, attempt) } });
      await f.invoke();
      assert.equal(f.updates.length, 0);
    });
  }
});

test('a stale completion event cannot publish a newer rerun', async () => {
  const f = fixture({ run: { run_attempt: 2 } });
  assert.deepEqual(await f.invoke(), { updated: [], skipped: ['unrelated-or-superseded-run'] });
  assert.equal(f.updates.length, 0);
});

test('rechecks the latest run attempt before patching', async () => {
  const f = fixture();
  f.github.rest.actions.getWorkflowRun = async () => ({ data: {
    ...f.run, run_attempt: ++f.calls.runs === 1 ? 1 : 2,
  } });
  await f.invoke();
  assert.equal(f.updates.length, 0);
});

for (const conclusion of ['failure', 'cancelled', 'timed_out', 'skipped']) {
  test(`${conclusion} clears a previous successful link`, async () => {
    const f = fixture({ run: { conclusion }, pull: { body: existingBlock(9) } });
    await f.invoke();
    assert.ok(f.updates[0].body.includes('Aktualna paczka nie jest dostępna'));
    assert.ok(f.updates[0].body.includes('/actions/runs/10)'));
    assert.ok(!f.updates[0].body.includes('/artifacts/'));
    assert.equal(f.calls.artifacts, 0);
  });
}

test('in-progress events remove the old success link', async () => {
  const f = fixture({ run: { status: 'in_progress', conclusion: null },
    pull: { body: existingBlock(9) } });
  await f.invoke();
  assert.ok(f.updates[0].body.includes('Trwa przygotowywanie'));
  assert.ok(!f.updates[0].body.includes('/artifacts/'));
  assert.equal(f.calls.artifacts, 0);
});

test('every status explains snapshot scope and conflicting PR limitations', async () => {
  for (const run of [{}, { status: 'in_progress', conclusion: null }, { conclusion: 'failure' }]) {
    const f = fixture({ run });
    await f.invoke();
    const body = f.updates[0].body;
    assert.ok(body.includes('Paczka dotyczy wyłącznie wskazanych SHA HEAD i bazy.'));
    assert.ok(body.includes('Nowszy commit lub baza wymagają nowej paczki.'));
    assert.ok(body.includes('Konflikt scalenia uniemożliwia eksport podglądu.'));
  }
});

test('missing or ambiguous artifacts never yield a download link', async t => {
  for (const artifacts of [[], [fixture().artifact, { ...fixture().artifact, id: 100 }]]) {
    await t.test(`count ${artifacts.length}`, async () => {
      const f = fixture({ artifacts });
      await f.invoke();
      assert.ok(!f.updates[0].body.includes('/artifacts/'));
      assert.ok(f.updates[0].body.includes('Nie znaleziono jednej zgodnej paczki'));
    });
  }
});

test('rejects wrong artifact identity and name shape', async t => {
  for (const name of ['other', `pr-data-12-h${HEAD}-b${BASE}-m${MERGE}-r10-a2`,
    `pr-data-12-h${OTHER}-b${BASE}-m${MERGE}-r10-a1`]) {
    await t.test(name, async () => {
      const f = fixture({ artifact: { name } });
      await f.invoke();
      assert.ok(!f.updates[0].body.includes('/artifacts/'));
    });
  }
});

test('expired artifacts never yield a download link', async t => {
  for (const artifact of [{ expired: true }, { expires_at: '2020-01-01T00:00:00Z' },
    { expires_at: 'invalid' }]) {
    await t.test(JSON.stringify(artifact), async () => {
      const f = fixture({ artifact });
      await f.invoke();
      assert.ok(f.updates[0].body.includes('Paczka wygasła'));
      assertFreshPrEventRecovery(f.updates[0].body);
      assert.ok(!f.updates[0].body.includes('/artifacts/'));
    });
  }
});

test('merge parents must be exactly current base then current head', async t => {
  for (const parents of [[{ sha: HEAD }, { sha: BASE }], [{ sha: BASE }],
    [{ sha: BASE }, { sha: OTHER }]]) {
    await t.test(JSON.stringify(parents), async () => {
      const f = fixture({ commit: { sha: MERGE, parents } });
      await f.invoke();
      assert.ok(!f.updates[0].body.includes('/artifacts/'));
      assert.ok(f.updates[0].body.includes('Commit podglądu nie odpowiada'));
    });
  }
});

test('unavailable merge commit fails closed without publishing a link', async () => {
  const f = fixture({ commitError: true });
  await f.invoke();
  assert.ok(f.updates[0].body.includes('Nie można potwierdzić commitu'));
  assert.ok(!f.updates[0].body.includes('/artifacts/'));
});

test('fork fallback matches SHA, head repository and branch', async () => {
  const f = fixture({ run: { pull_requests: [], head_repository: { id: 50 } } });
  const valid = structuredClone(f.pull);
  const differentRepo = { ...valid, number: 13, head: { ...valid.head, repo: { id: 51 } } };
  const differentBranch = { ...valid, number: 14, head: { ...valid.head, ref: 'other' } };
  f.github.rest.pulls.list = async () => {
    f.calls.lists++;
    return { data: [differentRepo, differentBranch, valid] };
  };
  await f.invoke();
  assert.equal(f.calls.lists, 1);
  assert.equal(f.updates.length, 1);
  assert.equal(f.updates[0].pull_number, 12);
});

test('closed PRs, unrelated base repository and unrelated workflow runs are skipped', async t => {
  for (const options of [{ pull: { state: 'closed' } },
    { pull: { base: { sha: BASE, repo: { id: 9 } } } },
    { run: { path: '.github/workflows/other.yml' } },
    { run: { event: 'push' } },
    { run: { repository: { id: 9, full_name: 'other/catalog' } } },
    { run: { repository: { id: 9, full_name: 'owner/catalog' } } }]) {
    await t.test(JSON.stringify(options), async () => {
      const f = fixture(options);
      await f.invoke();
      assert.equal(f.updates.length, 0);
    });
  }
});

test('malformed, duplicate or missing markers/state fail closed', async t => {
  for (const body of [START, END, END + START, existingBlock() + existingBlock(),
    `${START}\nno state\n${END}`,
    `${START}\n<!-- pr-data-preview:state {bad} -->\n${END}`,
    `${START}\n<!-- pr-data-preview:state {"run_id":0,"run_attempt":1} -->\n${END}`,
    existingBlock().replace(END, `<!-- pr-data-preview:state {"run_id":10,"run_attempt":1} -->${END}`)]) {
    await t.test(body, async () => {
      const f = fixture({ pull: { body } });
      await assert.rejects(f.invoke(), /preview (markers|state|run identity)/);
      assert.equal(f.updates.length, 0);
    });
  }
});

test('malformed namespace markers outside a valid block fail closed', async t => {
  for (const marker of ['<!-- pr-data-preview:start-->', '<!-- pr-data-preview:end-->',
    '<!-- pr-data-preview:other -->', '<!-- pr-data-preview:state {"run_id":10,"run_attempt":1} -->']) {
    await t.test(marker, async () => {
      const f = fixture({ pull: { body: `${marker}\n${existingBlock()}` } });
      await assert.rejects(f.invoke(), /preview markers/);
      assert.equal(f.updates.length, 0);
    });
  }
});

test('uses the freshest human-edited body before patching', async () => {
  const initial = fixture().pull;
  const fresh = { ...initial, body: 'Human edit made during export\n' };
  const f = fixture({ pulls: [initial, fresh] });
  await f.invoke();
  assert.ok(f.updates[0].body.startsWith(fresh.body));
  assert.ok(!f.updates[0].body.includes('Human description'));
});

test('head changes immediately before patch prevent any mutation', async () => {
  const initial = fixture().pull;
  const fresh = { ...initial, head: { ...initial.head, sha: OTHER } };
  const f = fixture({ pulls: [initial, fresh] });
  await f.invoke();
  assert.equal(f.updates.length, 0);
});

test('base changes immediately before patch replace success with stale state', async () => {
  const initial = fixture().pull;
  const fresh = { ...initial, base: { ...initial.base, sha: OTHER } };
  const f = fixture({ pulls: [initial, fresh] });
  await f.invoke();
  assert.ok(f.updates[0].body.includes('zmieniła się baza PR'));
  assertFreshPrEventRecovery(f.updates[0].body);
  assert.ok(!f.updates[0].body.includes('/artifacts/'));
});

test('newer state in the freshest body cannot be overwritten', async () => {
  const initial = fixture().pull;
  const fresh = { ...initial, body: existingBlock(11) };
  const f = fixture({ pulls: [initial, fresh] });
  await f.invoke();
  assert.equal(f.updates.length, 0);
});
