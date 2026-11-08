from __future__ import annotations

import json
import platform
import statistics
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone

from . import config
from . import screen_guide as sg
from .crypto import open_text, seal
from .mission_graph import MissionGraph, MissionNode
from .plugin_runtime import PluginOperation
from .semantic import similarity
from .verification import verify


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    passed: bool
    duration_ms: float
    detail: str


def _case(name: str, operation) -> BenchmarkCase:
    started = time.perf_counter()
    try:
        detail = str(operation())
        passed = True
    except Exception as exc:
        detail = f"{type(exc).__name__}: {exc}"
        passed = False
    return BenchmarkCase(name, passed, round((time.perf_counter() - started) * 1000, 3), detail)


def run_suite(write_report: bool = False) -> dict:
    """Run fast, offline checks that can fail when reliability contracts regress."""
    def encryption():
        private = "private benchmark payload"
        wrapped = seal(private)
        assert private not in wrapped and open_text(wrapped) == private
        return "Encrypted storage round-trip preserved confidentiality"

    def graph():
        mission = MissionGraph("benchmark", [
            MissionNode("observe", "inspect", "active"),
            MissionNode("act", "invoke", "Save", ("observe",)),
            MissionNode("confirm", "inspect", "saved", ("act",)),
        ])
        mission.validate()
        assert [item.node_id for item in mission.ready()] == ["observe"]
        return "Dependency order and graph validation passed"

    def cycle_guard():
        bad = MissionGraph("cycle", [MissionNode("a", "x", "", ("b",)),
                                      MissionNode("b", "x", "", ("a",))])
        try:
            bad.validate()
        except ValueError:
            return "Cyclic plan rejected"
        raise AssertionError("Cyclic plan was accepted")

    def postcondition():
        outcome = verify(lambda value, result: value == result, "expected", "expected")
        assert outcome.verified and outcome.observed
        failure = verify(lambda _value, _result: False, "x", "y")
        assert not failure.verified
        return "Positive and negative postconditions distinguished"

    def retrieval():
        related = similarity("project planning", "planning the project milestones")
        unrelated = similarity("project planning", "cinematic voice microphone")
        assert related > unrelated
        return f"Related={related:.3f}; unrelated={unrelated:.3f}"

    def typed_contract():
        contract = PluginOperation("create_task", "Create one task", "object", "inherit")
        assert contract.input_type == "object" and contract.operation_id == "create_task"
        return "Typed plugin operation contract constructed"

    class _Tree:
        def __init__(self, controls):
            self.controls = controls

        def list_windows(self):
            return [sg.WindowInfo(1, "Benchmark window")]

        def read_tree(self, handle, limit):
            return sg.WindowInfo(1, "Benchmark window"), iter(self.controls)

    def screen_observation():
        controls = [sg.ControlInfo(f"Control {i}" if i % 3 else "", "Button", True, "", i % 8)
                    for i in range(6_000)]
        started = time.perf_counter()
        obs = sg.observe(1, _Tree(controls), limit=400)
        elapsed = (time.perf_counter() - started) * 1000
        assert obs.truncated and len(obs.controls) == 400
        assert elapsed < 250, f"observation took {elapsed:.1f} ms"
        return f"6,000-node tree bounded to {len(obs.controls)} controls in {elapsed:.1f} ms"

    def screen_grounding():
        obs = sg.observe(1, _Tree([sg.ControlInfo(n, "MenuItem") for n in
                                   ("File", "Save as", "Export", "Print", "Help")]))
        steps = sg.ground([sg.GuidanceStep("a", "save as"), sg.GuidanceStep("b", "Export PDF"),
                           sg.GuidanceStep("c", "Settings"), sg.GuidanceStep("d", "")], obs)
        assert [s.grounded for s in steps] == [True, True, False, False]
        assert steps[1].matched_control == "Export"
        return "Observed controls grounded; unobserved and generic steps flagged"

    cases = [_case("Encrypted storage", encryption), _case("Mission dependency graph", graph),
             _case("Cycle rejection", cycle_guard), _case("Postcondition verification", postcondition),
             _case("Local related-memory retrieval", retrieval),
             _case("Typed plugin contract", typed_contract),
             _case("Screen Guide bounded observation", screen_observation),
             _case("Screen Guide grounding", screen_grounding)]
    durations = [item.duration_ms for item in cases]
    report = {
        "schema": 1,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "platform": platform.system(),
        "python": platform.python_version(),
        "passed": sum(item.passed for item in cases),
        "failed": sum(not item.passed for item in cases),
        "total_ms": round(sum(durations), 3),
        "median_ms": round(statistics.median(durations), 3) if durations else 0,
        "cases": [asdict(item) for item in cases],
    }
    if write_report:
        config.APP_DIR.mkdir(parents=True, exist_ok=True)
        destination = config.APP_DIR / "benchmark-latest.json"
        temporary = destination.with_suffix(".tmp")
        temporary.write_text(json.dumps(report, indent=2), encoding="utf-8")
        temporary.replace(destination)
        report["report_path"] = str(destination)
    return report
