# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The teams and projects a signed-in account can send work to.

One `GET /teams` answer lists every team of the account with the projects the
account may use in it: all of a team's projects for its admins, the projects
holding a role for its members. A browser sign-in picks its destination from
this list; API keys keep their own credential-bound scope.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Project:
    id: str
    name: str


@dataclass(frozen=True)
class Team:
    id: str
    name: str
    projects: tuple

    def project(self, project_id):
        return next((p for p in self.projects if p.id == project_id), None)


def _valid_id(value):
    return isinstance(value, str) and bool(value) and value.strip() == value


def _name(record, fallback):
    name = record.get("name")
    return name.strip() if isinstance(name, str) and name.strip() else fallback


def teams_from(response):
    """Teams and their projects, in the server's order; malformed records are skipped."""
    teams = []
    for record in response.get("teams") or ():
        if not isinstance(record, dict) or not _valid_id(record.get("id")):
            continue
        projects = tuple(
            Project(project["id"], _name(project, project["id"]))
            for project in record.get("projects") or ()
            if isinstance(project, dict) and _valid_id(project.get("id"))
        )
        teams.append(Team(record["id"], _name(record, record["id"]), projects))
    return tuple(teams)


def find(teams, project_id):
    """The (team, project) pair holding ``project_id``, or None."""
    for team in teams:
        project = team.project(project_id)
        if project is not None:
            return team, project
    return None


def label(team, project):
    """How the destination reads in the interface: ``Team / Project``."""
    return f"{team.name} / {project.name}"
