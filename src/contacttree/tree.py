"""Build an emergency call tree from a roster so nobody has to phone everyone."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field


@dataclass
class Person:
    name: str
    role: str
    team: str
    rank: int
    lead: bool = False
    calls: list["Person"] = field(default_factory=list)


def load_roster(path: str) -> tuple[list[Person], list[str]]:
    """Read name, role, team, rank, lead. Returns (people, problems); bad rows are left out."""
    people, problems, seen = [], [], set()
    with open(path, newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = {"name", "role", "rank"} - set(reader.fieldnames or [])
        if missing:
            raise ValueError("missing column(s): " + ", ".join(sorted(missing)))
        for n, row in enumerate(reader, start=2):
            name = (row.get("name") or "").strip()
            if not name:
                problems.append(f"row {n}: name is empty")
                continue
            if name.lower() in seen:
                problems.append(f"row {n}: duplicate name '{name}'")
                continue
            try:
                rank = int((row.get("rank") or "").strip())
            except ValueError:
                problems.append(f"row {n}: rank '{row.get('rank')}' is not a whole number ({name})")
                continue
            seen.add(name.lower())
            people.append(Person(name, (row.get("role") or "").strip(), (row.get("team") or "").strip(), rank,
                                 (row.get("lead") or "").strip().lower() in ("yes", "y", "true", "1")))
    leads = [p.name for p in people if p.lead]
    if len(leads) > 1:
        problems.append("more than one lead: " + ", ".join(leads) + " (the first one is used)")
    return people, problems


def build_tree(people: list[Person], fanout: int = 3, absent: tuple[str, ...] = ()) -> tuple[Person, list[Person]]:
    """Return (root, absent people). Everyone present is called by exactly one caller.

    The root is the lead (or the best ranked person). Callers are taken in order of rank and
    each one calls the next `fanout` people who have not been assigned yet.
    """
    if fanout < 1:
        raise ValueError("fanout must be at least 1")
    gone = {a.strip().lower() for a in absent}
    present = [p for p in people if p.name.lower() not in gone]
    away = [p for p in people if p.name.lower() in gone]
    if not present:
        raise ValueError("nobody is present")
    for p in present:
        p.calls = []
    ordered = sorted(present, key=lambda p: p.rank)
    root = next((p for p in ordered if p.lead), ordered[0])
    rest = [p for p in ordered if p is not root]
    queue, i = [root], 0
    while queue and i < len(rest):
        caller = queue.pop(0)
        batch = rest[i:i + fanout]
        caller.calls.extend(batch)
        queue.extend(batch)
        i += fanout
    return root, away


def depth(root: Person) -> int:
    return 1 + max((depth(c) for c in root.calls), default=0)


def walk(root: Person):
    """Yield (caller, callee) pairs in the order the calls are made."""
    queue = [root]
    while queue:
        p = queue.pop(0)
        for c in p.calls:
            yield p, c
            queue.append(c)


def render(root: Person) -> str:
    """Draw the tree as indented text."""
    lines = [f"{root.name} ({root.role}) starts the tree"]

    def add(p: Person, prefix: str) -> None:
        for i, c in enumerate(p.calls):
            last = i == len(p.calls) - 1
            lines.append(f"{prefix}{'`-- ' if last else '|-- '}{c.name} ({c.role})")
            add(c, prefix + ("    " if last else "|   "))

    add(root, "")
    return "\n".join(lines)


def stats(root: Person, away: list[Person]) -> str:
    pairs = list(walk(root))
    busiest = max((len(p.calls) for p, _ in pairs), default=0)
    out = f"{len(pairs) + 1} people, {depth(root)} levels, at most {busiest} calls each"
    if away:
        out += "; absent: " + ", ".join(p.name for p in away)
    return out
