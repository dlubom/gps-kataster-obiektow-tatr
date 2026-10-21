"""Narrow GitHub REST and ordinary Git push adapter for the TPN workflow."""

from __future__ import annotations

import base64
import json
import os
import re
import subprocess
from urllib.parse import quote
from urllib.request import Request, urlopen

from .tpn_api import require
from .tpn_workflow import BRANCH_PREFIX


class GitHub:
    def __init__(self, repository, token):
        require(re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository), "invalid repository")
        require(bool(token), "missing GITHUB_TOKEN")
        self.repository, self.token = repository, token

    @property
    def git_url(self):
        return "https://github.com/" + self.repository + ".git"

    def request(self, path, method="GET", body=None):
        req = Request(
            "https://api.github.com/" + path,
            data=json.dumps(body).encode() if body is not None else None,
            method=method,
            headers={
                "Authorization": "Bearer " + self.token,
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "gps-kataster-tpn-workflow",
                "Content-Type": "application/json",
            },
        )
        with urlopen(req, timeout=30) as response:
            return json.load(response)

    def repo(self, path, method="GET", body=None):
        return self.request("repos/" + self.repository + "/" + path, method, body)

    def pages(self, path):
        result, page = [], 1
        while True:
            rows = self.repo(path + ("&" if "?" in path else "?") + f"per_page=100&page={page}")
            require(isinstance(rows, list), "invalid GitHub list response")
            result.extend(rows)
            if len(rows) < 100:
                return result
            page += 1

    def authorize(self, login):
        require(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9-]{0,38}", login), "invalid operator login")
        user = self.request("users/" + quote(login, safe=""))
        permission = self.repo("collaborators/" + quote(login, safe="") + "/permission")
        require(
            user.get("type") == "User"
            and permission.get("permission") in ("write", "maintain", "admin"),
            "unauthorized human operator",
        )

    def main(self):
        return self.repo("git/ref/heads/main")["object"]["sha"]

    def pulls(self):
        return self.pages("pulls?state=all&base=main")

    def pull(self, number):
        return self.repo("pulls/" + str(number))

    def branches(self):
        # This endpoint returns all matching refs and has no page parameter.
        rows = self.repo("git/matching-refs/heads/" + BRANCH_PREFIX)
        require(isinstance(rows, list), "invalid GitHub reference response")
        return {r["ref"].removeprefix("refs/heads/"): r["object"]["sha"] for r in rows}

    def push(self, root, head, branch):
        # The token is in the subprocess environment, never URL/argv/log output.
        credential = base64.b64encode(("x-access-token:" + self.token).encode()).decode()
        env = {
            **os.environ,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.https://github.com/.extraheader",
            "GIT_CONFIG_VALUE_0": "AUTHORIZATION: basic " + credential,
        }
        result = subprocess.run(
            [
                "git",
                "-c",
                "core.hooksPath=/dev/null",
                "-C",
                str(root),
                "push",
                "--atomic",
                self.git_url,
                head + ":refs/heads/" + branch,
            ],
            env=env,
            capture_output=True,
            check=False,
        )
        require(result.returncode == 0, "ordinary Git push failed; remote branch preserved")

    def create_pull(self, branch, batch):
        return self.repo(
            "pulls",
            "POST",
            {
                "base": "main",
                "head": branch,
                "draft": True,
                "title": "data: review TPN source changes",
                "body": (
                    "Paczka TPN przygotowana do indywidualnego review. Wszystkie decyzje zaczynają "
                    "jako pending; nowe YAML są propozycjami.\n\n"
                    "Instrukcja: [ręczny workflow TPN](https://github.com/"
                    + self.repository
                    + "/blob/main/docs/asdlc/tpn_sync_workflow.md).\n\n"
                    "Bieżące decyzje i raport są w zmienionym katalogu `data/source_reviews/tpn/`. "
                    "Jawne refresh tworzy nową paczkę w tym samym PR i zachowuje historię.\n\n"
                    "Po zapisie przez GITHUB_TOKEN człowiek wybiera **Approve workflows to run** "
                    "i sprawdza wymagane CI oraz paczkę eksportów dokładnego HEAD. "
                    "Pending blokuje merge. Merge wykonuje wyłącznie człowiek."
                ),
            },
        )
