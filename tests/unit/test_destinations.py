# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""A signed-in account's teams and projects, read from one GET /teams answer."""

from scenario.core.api import destinations

# Two teams with two projects each and a team without a usable project, shaped
# like the SDK's TeamListResponse (fields the picker ignores are left out).
RESPONSE = {
    "teams": [
        {
            "id": "team_studio",
            "name": "Studio",
            "projects": [
                {"id": "proj_film", "name": "Film"},
                {"id": "proj_game", "name": "Game"},
            ],
        },
        {
            "id": "team_personal",
            "name": "Personal",
            "projects": [
                {"id": "proj_sketches", "name": "Sketches"},
                {"id": "proj_tests", "name": "  "},
            ],
        },
        {"id": "team_empty", "name": "Invited", "projects": []},
    ]
}


def test_every_team_keeps_its_own_projects_in_server_order():
    teams = destinations.teams_from(RESPONSE)
    assert [(t.id, t.name) for t in teams] == [
        ("team_studio", "Studio"),
        ("team_personal", "Personal"),
        ("team_empty", "Invited"),
    ]
    assert [p.id for p in teams[0].projects] == ["proj_film", "proj_game"]
    assert [p.id for p in teams[1].projects] == ["proj_sketches", "proj_tests"]
    assert teams[2].projects == ()


def test_a_blank_name_reads_as_its_id():
    teams = destinations.teams_from(RESPONSE)
    assert teams[1].project("proj_tests").name == "proj_tests"


def test_find_names_the_team_holding_a_project_in_another_team():
    teams = destinations.teams_from(RESPONSE)
    team, project = destinations.find(teams, "proj_sketches")
    assert (team.id, project.id) == ("team_personal", "proj_sketches")
    assert destinations.label(team, project) == "Personal / Sketches"
    assert destinations.find(teams, "proj_gone") is None


def test_malformed_records_are_skipped_not_trusted():
    teams = destinations.teams_from(
        {
            "teams": [
                {"id": " padded", "name": "Bad", "projects": []},
                "not a team",
                {"name": "No id"},
                {
                    "id": "team_ok",
                    "name": "Ok",
                    "projects": [{"id": ""}, {"name": "No id"}, None, {"id": "proj_ok"}],
                },
            ]
        }
    )
    assert [t.id for t in teams] == ["team_ok"]
    assert [(p.id, p.name) for p in teams[0].projects] == [("proj_ok", "proj_ok")]


def test_no_teams_is_an_empty_list():
    assert destinations.teams_from({"teams": []}) == ()
    assert destinations.teams_from({}) == ()
