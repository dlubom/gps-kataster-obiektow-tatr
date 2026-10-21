'use strict';

const BUILD_PATH = '.github/workflows/pr-data.yml';
const START = '<!-- pr-data-preview:start -->';
const END = '<!-- pr-data-preview:end -->';
const STATE = '<!-- pr-data-preview:state ';
const FRESH_PR_EVENT = 'Utwórz nowy commit lub ponownie otwórz PR, aby otrzymać aktualną paczkę.';
const SHA = /^[0-9a-f]{40}$/;
const ARTIFACT_NAME = /^pr-data-([1-9]\d*)-h([0-9a-f]{40})-b([0-9a-f]{40})-m([0-9a-f]{40})-r([1-9]\d*)-a([1-9]\d*)$/;

function positiveInteger(value) {
  return Number.isSafeInteger(value) && value > 0;
}

function parseBody(body) {
  body = body || '';
  const starts = body.split(START).length - 1;
  const ends = body.split(END).length - 1;
  if (starts === 0 && ends === 0 && !body.includes('<!-- pr-data-preview:')) {
    return { body, start: -1, end: -1, state: null };
  }
  if (starts !== 1 || ends !== 1 || body.indexOf(END) < body.indexOf(START)
      || body.split('<!-- pr-data-preview:').length - 1 !== 3) {
    throw new Error('Malformed or duplicate PR data preview markers; refusing to change the body.');
  }
  const start = body.indexOf(START);
  const end = body.indexOf(END) + END.length;
  const block = body.slice(start, end);
  const states = [...block.matchAll(/<!-- pr-data-preview:state (\{[^\r\n]*\}) -->/g)];
  if (states.length !== 1 || block.split(STATE).length - 1 !== 1) {
    throw new Error('Missing, duplicate or malformed PR data preview state.');
  }
  let state;
  try {
    state = JSON.parse(states[0][1]);
  } catch {
    throw new Error('Malformed PR data preview state JSON.');
  }
  if (!positiveInteger(state.run_id) || !positiveInteger(state.run_attempt)) {
    throw new Error('Invalid PR data preview run identity.');
  }
  return { body, start, end, state };
}

function replaceBlock(parsed, block) {
  if (parsed.start >= 0) {
    return parsed.body.slice(0, parsed.start) + block + parsed.body.slice(parsed.end);
  }
  const separator = !parsed.body || parsed.body.endsWith('\n\n') ? ''
    : parsed.body.endsWith('\n') ? '\n' : '\n\n';
  return parsed.body + separator + block;
}

function olderThanStored(run, state) {
  return state && (state.run_id > run.id
    || (state.run_id === run.id && state.run_attempt > run.run_attempt));
}

function validRun(run, eventRun, context) {
  const expected = `${context.repo.owner}/${context.repo.repo}`.toLowerCase();
  const repository = run.repository;
  const payloadRepository = context.payload.repository;
  const validPath = run.path === BUILD_PATH || (typeof run.path === 'string'
    && run.path.startsWith(`${BUILD_PATH}@`) && run.path.length > BUILD_PATH.length + 1);
  return run.id === eventRun.id && run.event === 'pull_request' && validPath
    && repository && repository.full_name?.toLowerCase() === expected
    && positiveInteger(repository.id)
    && (!payloadRepository?.id || payloadRepository.id === repository.id)
    && positiveInteger(run.run_attempt) && SHA.test(run.head_sha || '')
    && positiveInteger(run.head_repository?.id)
    && typeof run.head_branch === 'string' && run.head_branch.length > 0;
}

function currentPull(pull, run) {
  return pull.state === 'open' && pull.head?.sha === run.head_sha
    && pull.head?.repo?.id === run.head_repository.id && pull.head?.ref === run.head_branch
    && pull.base?.repo?.id === run.repository.id && SHA.test(pull.base?.sha || '');
}

function artifactIdentity(artifact) {
  const match = ARTIFACT_NAME.exec(artifact.name || '');
  if (!match) return null;
  const result = { number: Number(match[1]), head: match[2], base: match[3], merge: match[4],
    runId: Number(match[5]), attempt: Number(match[6]) };
  return [result.number, result.runId, result.attempt].every(positiveInteger) ? result : null;
}

function renderBlock(run, pull, result, owner, repo) {
  const url = `https://github.com/${owner}/${repo}/actions/runs/${run.id}`;
  const lines = [START, '### Paczka danych tego PR', '', result.message, '',
    `- HEAD PR: \`${pull.head.sha}\``, `- Baza PR: \`${pull.base.sha}\``];
  if (result.identity) {
    if (result.identity.base !== pull.base.sha) {
      lines.push(`- Baza użyta do eksportu: \`${result.identity.base}\``);
    }
    lines.push(`- Commit podglądu scalenia: \`${result.identity.merge}\``);
  }
  if (result.artifact) {
    const artifact = result.artifact;
    lines.push('', `[Pobierz pełną paczkę danych (ZIP)](${url}/artifacts/${artifact.id})`, '',
      'Paczka zawiera te same pliki danych co wydanie, w tym Excel Best/Full, GPX, CSV, '
      + 'GeoJSON, Shapefile, SQLite i statystyki, oraz manifest i sumy SHA-256.',
      `Pobranie wymaga zalogowania do GitHub. Ważność artefaktu: ${artifact.expires_at}.`);
  }
  lines.push('', `[Przebieg workflow — próba ${run.run_attempt}](${url})`, '',
    'Paczka dotyczy wyłącznie wskazanych SHA HEAD i bazy. '
    + 'Nowszy commit lub baza wymagają nowej paczki. '
    + 'Konflikt scalenia uniemożliwia eksport podglądu.', '',
    'To paczka testowa przed scaleniem PR; oficjalne wydanie jest osobnym krokiem. '
    + 'Numer przyszłego wydania, końcowy commit i czas generowania '
    + 'mogą się różnić po scaleniu.',
    `${STATE}${JSON.stringify({ run_id: run.id, run_attempt: run.run_attempt })} -->`, END);
  return lines.join('\n');
}

async function exportStatus(github, args, run, pull, artifacts) {
  if (run.status !== 'completed') {
    return { message: '⏳ Trwa przygotowywanie aktualnej paczki danych.' };
  }
  if (run.conclusion !== 'success') {
    const descriptions = { cancelled: 'został anulowany', failure: 'zakończył się błędem',
      timed_out: 'przekroczył limit czasu', skipped: 'został pominięty' };
    return { message: `⚠️ Eksport ${descriptions[run.conclusion] || 'nie zakończył się powodzeniem'}. `
      + 'Aktualna paczka nie jest dostępna.' };
  }
  const matches = artifacts.map(artifact => ({ artifact, identity: artifactIdentity(artifact) }))
    .filter(({ identity }) => identity && identity.number === pull.number
      && identity.head === run.head_sha && identity.runId === run.id
      && identity.attempt === run.run_attempt);
  if (matches.length !== 1) {
    return { message: '⚠️ Nie znaleziono jednej zgodnej paczki z tego przebiegu. '
      + 'Aktualna paczka nie jest dostępna.' };
  }
  const { artifact, identity } = matches[0];
  if (identity.base !== pull.base.sha) {
    return { identity, message: '⚠️ Podgląd jest nieaktualny: zmieniła się baza PR. '
      + FRESH_PR_EVENT };
  }
  if (!positiveInteger(artifact.id) || artifact.expired || !artifact.expires_at
      || !Number.isFinite(Date.parse(artifact.expires_at)) || Date.parse(artifact.expires_at) <= Date.now()) {
    return { identity, message: '⚠️ Paczka wygasła lub nie ma prawidłowych metadanych. '
      + FRESH_PR_EVENT };
  }
  let commit;
  try {
    commit = (await github.rest.repos.getCommit({ ...args, ref: identity.merge })).data;
  } catch {
    return { identity, message: '⚠️ Nie można potwierdzić commitu podglądu scalenia. '
      + 'Aktualna paczka nie jest dostępna.' };
  }
  if (commit.sha !== identity.merge || commit.parents?.length !== 2
      || commit.parents[0].sha !== identity.base || commit.parents[1].sha !== identity.head) {
    return { identity, message: '⚠️ Commit podglądu nie odpowiada aktualnej bazie i HEAD PR. '
      + 'Aktualna paczka nie jest dostępna.' };
  }
  return { identity, artifact, message: '✅ Gotowy podgląd danych wskazanego HEAD do sprawdzenia przed scaleniem PR.' };
}

module.exports = async function publishPrData({ github, context, core }) {
  const info = message => core?.info?.(message);
  const eventRun = context.payload.workflow_run;
  if (!eventRun || !positiveInteger(eventRun.id)) {
    throw new Error('A valid workflow_run event is required.');
  }
  const args = { owner: context.repo.owner, repo: context.repo.repo };
  const run = (await github.rest.actions.getWorkflowRun({ ...args, run_id: eventRun.id })).data;
  const result = { updated: [], skipped: [] };
  if (!validRun(run, eventRun, context)
      || (eventRun.run_attempt !== undefined && eventRun.run_attempt !== run.run_attempt)) {
    info('Skipping unrelated or superseded workflow run.');
    result.skipped.push('unrelated-or-superseded-run');
    return result;
  }
  let candidates = run.pull_requests || [];
  if (!candidates.length) {
    candidates = await github.paginate(github.rest.pulls.list, { ...args, state: 'open', per_page: 100 });
    candidates = candidates.filter(pull => currentPull(pull, run));
  }
  const numbers = [...new Set(candidates.map(pull => pull.number).filter(positiveInteger))];
  const artifacts = run.status === 'completed' && run.conclusion === 'success'
    ? await github.paginate(github.rest.actions.listWorkflowRunArtifacts,
      { ...args, run_id: run.id, per_page: 100 }) : [];
  for (const number of numbers) {
    let pull = (await github.rest.pulls.get({ ...args, pull_number: number })).data;
    if (!currentPull(pull, run)) {
      result.skipped.push(number);
      continue;
    }
    let parsed = parseBody(pull.body);
    if (olderThanStored(run, parsed.state)) {
      result.skipped.push(number);
      continue;
    }
    let status = await exportStatus(github, args, run, pull, artifacts);
    // Read both identities again before writing; a rerun or push may have happened meanwhile.
    const latestRun = (await github.rest.actions.getWorkflowRun({ ...args, run_id: run.id })).data;
    if (!validRun(latestRun, eventRun, context) || latestRun.run_attempt !== run.run_attempt
        || latestRun.status !== run.status || latestRun.conclusion !== run.conclusion) {
      result.skipped.push(number);
      continue;
    }
    const freshPull = (await github.rest.pulls.get({ ...args, pull_number: number })).data;
    if (!currentPull(freshPull, run)) {
      result.skipped.push(number);
      continue;
    }
    parsed = parseBody(freshPull.body);
    if (olderThanStored(run, parsed.state)) {
      result.skipped.push(number);
      continue;
    }
    if (status.identity && status.identity.base !== freshPull.base.sha) {
      status = { identity: status.identity, message: '⚠️ Podgląd jest nieaktualny: zmieniła się baza PR. '
        + FRESH_PR_EVENT };
    }
    pull = freshPull;
    const body = replaceBlock(parsed, renderBlock(run, pull, status, args.owner, args.repo));
    if (body === (pull.body || '')) {
      result.skipped.push(number);
      continue;
    }
    await github.rest.pulls.update({ ...args, pull_number: number, body });
    result.updated.push(number);
  }
  info(`PR data preview bodies updated: ${result.updated.join(', ') || 'none'}.`);
  return result;
};
