from typing import Any

from .learner_state import get_evaluation_snapshot, get_intervention_plan, get_learner_state

try:
    from .materials import list_learning_materials
except ImportError:
    from materials import list_learning_materials


def _safe_pct(value: float | int | None) -> int:
    try:
        return round(float(value or 0) * 100)
    except (TypeError, ValueError):
        return 0


def get_demo_personas() -> list[dict[str, Any]]:
    return [
        {
            "id": "beginner_student",
            "title": "Beginner student",
            "profile": "High-school or first-year learner building fundamentals.",
            "topic": "Python loops",
            "goal": "Understand for and while loops well enough to solve basic exercises.",
            "daily_minutes": 45,
            "deadline_days": 14,
            "demo_prompt": "Teach me Python loops simply, then create a study roadmap.",
        },
        {
            "id": "exam_crammer",
            "title": "Exam crammer",
            "profile": "Learner with an urgent deadline who needs prioritization and recovery support.",
            "topic": "Recursion",
            "goal": "Recover fast and focus only on high-impact recursion concepts before the exam.",
            "daily_minutes": 30,
            "deadline_days": 7,
            "demo_prompt": "I missed several sessions. Give me a catch-up plan for recursion this week.",
        },
        {
            "id": "working_professional",
            "title": "Working professional",
            "profile": "Busy adult learner using uploaded materials and short study blocks.",
            "topic": "Binary search",
            "goal": "Learn one interview algorithm deeply using notes and short evening sessions.",
            "daily_minutes": 25,
            "deadline_days": 10,
            "demo_prompt": "Use my uploaded notes to teach binary search and make a short roadmap.",
        },
    ]


def build_demo_metrics(user_id: str) -> dict[str, Any]:
    state = get_learner_state(user_id)
    evaluation = get_evaluation_snapshot(user_id)
    intervention = get_intervention_plan(user_id)
    materials = list_learning_materials(user_id)

    mastery = state.get("mastery", {}) if state.get("status") == "success" else {}
    roadmap_summary = state.get("roadmap_summary", {}) if state.get("status") == "success" else {}
    material_count = len(materials.get("materials", [])) if materials.get("status") == "success" else 0

    metrics = [
        {
            "label": "Overall mastery",
            "value": f"{_safe_pct(mastery.get('overall_score'))}%",
            "detail": mastery.get("overall_label", "needs support"),
        },
        {
            "label": "Roadmap completion",
            "value": f"{_safe_pct(roadmap_summary.get('completion_rate'))}%",
            "detail": f"{roadmap_summary.get('completed_sessions', 0)}/{roadmap_summary.get('total_sessions', 0)} sessions complete",
        },
        {
            "label": "Assessment coverage",
            "value": str(evaluation.get("coverage", {}).get("assessment_count", 0)),
            "detail": "assessments recorded",
        },
        {
            "label": "Grounded materials",
            "value": str(material_count),
            "detail": "uploaded study sources",
        },
        {
            "label": "Intervention risk",
            "value": intervention.get("risk_level", "unknown"),
            "detail": intervention.get("summary", "No intervention summary available."),
        },
    ]
    return {"status": "success", "metrics": metrics}


def get_demo_script(user_id: str) -> list[dict[str, Any]]:
    state = get_learner_state(user_id)
    topic = state.get("current_topic") or state.get("profile", {}).get("topic") or "Python loops"
    return [
        {
            "step": 1,
            "title": "Sign in and show learner cockpit",
            "detail": "Open the dashboard overview and show mastery, roadmap, materials, risk, and architecture readiness in one screen.",
        },
        {
            "step": 2,
            "title": "Run a diagnostic",
            "detail": f"Start a short diagnostic on {topic}, submit answers, and show mastery update live.",
        },
        {
            "step": 3,
            "title": "Generate a living roadmap",
            "detail": "Create a roadmap, then mark a session missed or completed to show automatic adaptation.",
        },
        {
            "step": 4,
            "title": "Ground the tutor in real materials",
            "detail": "Upload notes or a study image, ask a grounded question, and show source-aware tutoring.",
        },
        {
            "step": 5,
            "title": "Show intervention and reporting",
            "detail": "Refresh insights, explain learner risk level, then generate the weekly report.",
        },
        {
            "step": 6,
            "title": "Close with Google-native workflow",
            "detail": "Explain that the same report can be saved to Google Docs and roadmap sessions can become Google Tasks or Calendar actions.",
        },
    ]


def get_pitch_copy() -> dict[str, str]:
    return {
        "one_liner": "ARKAIS is an adaptive AI learning companion that diagnoses, teaches, remembers, grounds itself in real study materials, and intervenes across a learner’s full workflow using Google-native AI infrastructure.",
        "judge_angle": "We are not just generating answers. We are closing the loop from assessment to roadmap to grounded tutoring to recovery to reporting.",
    }


def get_demo_kit(user_id: str) -> dict[str, Any]:
    return {
        "status": "success",
        "personas": get_demo_personas(),
        "metrics": build_demo_metrics(user_id).get("metrics", []),
        "demo_script": get_demo_script(user_id),
        "pitch": get_pitch_copy(),
    }
