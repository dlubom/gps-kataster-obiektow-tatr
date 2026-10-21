'use strict';

// Only GitHub API metadata is read here. PR artifacts are never downloaded/executed.
const MARKER = '<!-- gps-kataster-pr-preview -->';
const WORKFLOW = 'pr-preview.yml';
const sameRepo = (left, right) => left?.id === right?.id && left?.full_name === right?.full_name;

module.exports = async function publish({ github, context }) {
  const repo = context.repo;
  const event = context.payload.workflow_run;
  const { data: run } = await github.rest.actions.getWorkflowRun({ ...repo, run_id: event.id });
  const { data: workflow } = await github.rest.actions.getWorkflow({ ...repo, workflow_id: WORKFLOW });
  if (run.event !== 'pull_request' || run.workflow_id !== workflow.id ||
      run.path !== `.github/workflows/${WORKFLOW}` ||
      run.repository?.full_name !== `${repo.owner}/${repo.repo}` ||
      run.run_attempt !== event.run_attempt) return;

  const belongs = pr => pr.state === 'open' && !pr.merged &&
    sameRepo(pr.base.repo, run.repository) && sameRepo(pr.head.repo, run.head_repository) &&
    pr.head.sha === run.head_sha && pr.head.ref === run.head_branch;
  // The numbered run name routes forks too, where GitHub can omit pull_requests.
  // It is only a hint: the live head repo/SHA/ref, association and merge still have to match.
  const title = /^PR export preview #([1-9][0-9]*)$/.exec(run.display_title || '');
  if (!title) return;
  const number = Number(title[1]);
  if (!Number.isSafeInteger(number) || (run.pull_requests?.length &&
      !run.pull_requests.some(pr => pr.number === number))) return;
  const prs = [(await github.rest.pulls.get({ ...repo, pull_number: number })).data];
  for (const pr of prs.filter(belongs)) {
    const associated = run.pull_requests?.find(item => item.number === pr.number);
    if (associated && (associated.base.sha !== pr.base.sha || associated.head.sha !== pr.head.sha)) continue;
    const isLatest = async () => {
      const runs = await github.paginate(github.rest.actions.listWorkflowRuns, {
        ...repo, workflow_id: workflow.id, event: 'pull_request', head_sha: run.head_sha,
        per_page: 100,
      });
      return !runs.some(other => other.id > run.id && other.display_title === run.display_title &&
        (!other.pull_requests?.length || other.pull_requests.some(item => item.number === pr.number)) &&
        other.head_branch === run.head_branch && sameRepo(other.head_repository, run.head_repository));
    };
    if (!await isLatest()) continue;
    const root = `${context.serverUrl || 'https://github.com'}/${repo.owner}/${repo.repo}`;
    const runUrl = `${root}/actions/runs/${run.id}`;
    let status = `⏳ Budowanie paczki — [przebieg](${runUrl}).`;
    let merge = null;
    if (run.status === 'completed') {
      status = `❌ Brak aktualnej paczki: ${run.conclusion}. [Przebieg](${runUrl}).`;
      if (run.conclusion === 'success') {
        const artifacts = await github.paginate(github.rest.actions.listWorkflowRunArtifacts, {
          ...repo, run_id: run.id, per_page: 100,
        });
        const prefix = `pr-preview-${pr.number}-${pr.head.sha}-${pr.base.sha}-`;
        const candidates = artifacts.filter(a => !a.expired && a.name.startsWith(prefix) &&
          /^[0-9a-f]{40}$/.test(a.name.slice(prefix.length, prefix.length + 40)) &&
          a.name.slice(prefix.length + 40) === `-${run.run_attempt}` &&
          a.workflow_run?.id === run.id && a.workflow_run?.head_sha === run.head_sha);
        status = `⚠️ Brak jednoznacznej, niewygasłej paczki dla tej wersji PR. [Przebieg](${runUrl}).`;
        if (candidates.length === 1) {
          const artifact = candidates[0];
          merge = artifact.name.slice(prefix.length, prefix.length + 40);
          if (merge !== pr.merge_commit_sha) continue;
          const { data: commit } = await github.rest.repos.getCommit({ ...repo, ref: merge });
          if (commit.parents.length !== 2 || commit.parents[0].sha !== pr.base.sha ||
              commit.parents[1].sha !== pr.head.sha) continue;
          status = `✅ [Pobierz ZIP eksportów](${runUrl}/artifacts/${artifact.id})\n\n` +
            `Ważny do **${artifact.expires_at}** (UTC), retencja 14 dni. Pobranie wymaga logowania do GitHub.`;
        }
      }
    }
    const identity = [pr.head.sha, pr.base.sha, pr.merge_commit_sha].join(':');
    const body = `${MARKER}\n### Paczka testowa eksportów\n\n${status}\n\n` +
      `HEAD: \`${pr.head.sha}\`\n\nBaza: \`${pr.base.sha}\`\n\n` +
      (merge ? `Testowany merge: \`${merge}\`\n\n` : '') +
      `Pełne eksporty obecnego buildera wydania, manifest i SHA256SUMS. ` +
      `To podgląd PR przed scaleniem. Zmiana samego main wymaga nowego buildu.\n`;
    const comments = await github.paginate(github.rest.issues.listComments, {
      ...repo, issue_number: pr.number, per_page: 100,
    });
    const comment = comments.find(c => c.user?.type === 'Bot' &&
      c.user.login === 'github-actions[bot]' && c.body?.startsWith(MARKER));
    // Recheck immediately before mutation: a PR update or retry may have arrived during API reads.
    const { data: fresh } = await github.rest.pulls.get({ ...repo, pull_number: pr.number });
    const { data: freshRun } = await github.rest.actions.getWorkflowRun({ ...repo, run_id: run.id });
    if (!belongs(fresh) || [fresh.head.sha, fresh.base.sha, fresh.merge_commit_sha].join(':') !== identity ||
        freshRun.run_attempt !== event.run_attempt || freshRun.status !== run.status ||
        freshRun.conclusion !== run.conclusion || !await isLatest()) continue;
    if (comment) {
      if (comment.body !== body) await github.rest.issues.updateComment({ ...repo, comment_id: comment.id, body });
    } else {
      await github.rest.issues.createComment({ ...repo, issue_number: pr.number, body });
    }
  }
};
