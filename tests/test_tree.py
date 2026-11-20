from pathlib import Path

import pytest

from contacttree.__main__ import main
from contacttree.tree import Person, build_tree, depth, load_roster, render, stats, walk

EX = Path(__file__).resolve().parent.parent / "examples"
GOOD = str(EX / "roster.csv")
BAD = str(EX / "roster_with_errors.csv")


def people(n, lead_first=True):
    return [Person(f"P{i}", "role", "t", i, lead=(lead_first and i == 1)) for i in range(1, n + 1)]


def test_load_sample():
    p, problems = load_roster(GOOD)
    assert len(p) == 14 and problems == [] and p[0].lead


def test_load_reports_problems():
    p, problems = load_roster(BAD)
    assert len(p) == 3
    assert any("duplicate name 'Omar Reyes'" in x for x in problems)
    assert any("name is empty" in x for x in problems)
    assert any("rank 'first'" in x for x in problems)
    assert any("more than one lead" in x for x in problems)


def test_missing_column(tmp_path):
    f = tmp_path / "r.csv"
    f.write_text("name,role\nA,b\n")
    with pytest.raises(ValueError, match="rank"):
        load_roster(str(f))


def test_everyone_is_called_exactly_once():
    root, _ = build_tree(load_roster(GOOD)[0], 3)
    callees = [c.name for _, c in walk(root)]
    assert len(callees) == 13 and len(set(callees)) == 13 and root.name not in callees


def test_nobody_calls_more_than_fanout():
    root, _ = build_tree(load_roster(GOOD)[0], 3)
    assert all(len(p.calls) <= 3 for p, _ in walk(root))


def test_root_is_the_lead_even_if_not_first():
    ps = people(5, lead_first=False)
    ps[3].lead = True
    root, _ = build_tree(ps, 2)
    assert root.name == "P4"


def test_root_defaults_to_best_rank():
    root, _ = build_tree(people(4, lead_first=False), 2)
    assert root.name == "P1"


def test_higher_rank_calls_first():
    root, _ = build_tree(people(7), 2)
    assert [c.name for c in root.calls] == ["P2", "P3"]
    assert [c.name for c in root.calls[0].calls] == ["P4", "P5"]


def test_depth_shrinks_with_bigger_fanout():
    ps = load_roster(GOOD)[0]
    assert depth(build_tree(ps, 5)[0]) < depth(build_tree(ps, 2)[0])


def test_fanout_one_is_a_chain():
    root, _ = build_tree(people(4), 1)
    assert depth(root) == 4


def test_absent_people_are_skipped():
    root, away = build_tree(load_roster(GOOD)[0], 3, ("hannah cole", "Jon Park"))
    names = {c.name for _, c in walk(root)}
    assert "Hannah Cole" not in names and len(names) == 11
    assert [a.name for a in away] == ["Hannah Cole", "Jon Park"]


def test_absent_lead_hands_over_to_next():
    root, _ = build_tree(load_roster(GOOD)[0], 3, ("Dana Whitfield",))
    assert root.name == "Omar Reyes"


def test_bad_fanout_and_empty():
    with pytest.raises(ValueError):
        build_tree(people(3), 0)
    with pytest.raises(ValueError):
        build_tree(people(2), 2, ("P1", "P2"))


def test_render_and_stats():
    root, away = build_tree(load_roster(GOOD)[0], 3)
    text = render(root)
    assert text.splitlines()[0] == "Dana Whitfield (Facility Manager) starts the tree"
    assert len(text.splitlines()) == 14
    assert stats(root, away) == "14 people, 4 levels, at most 3 calls each"


def test_cli_codes(capsys):
    assert main(["build", GOOD]) == 0
    assert main(["build", GOOD, "--format", "csv"]) == 0
    assert "caller,callee,callee_role" in capsys.readouterr().out
    assert main(["check", GOOD]) == 0
    assert main(["check", BAD]) == 1
    assert main(["build", GOOD, "--absent", "Nobody Here"]) == 2
    assert main(["build", GOOD, "--fanout", "0"]) == 2
    assert main(["build", "nope.csv"]) == 2
