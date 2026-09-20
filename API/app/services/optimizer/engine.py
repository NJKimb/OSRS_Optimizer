from fastapi import HTTPException
from app.core.skills import Skill
from app.models.plan import OptimizationRequest, OptimizationResponse, RoadmapStep
from app.models.quest import Quest
from app.repositories.quest_repository import QuestRepository, get_quest_repository
from app.services.hiscores import fetch_player_profile
from app.services.optimizer.simulator import QUEST_ESTIMATED_TIME, OptimizationSimulator
from app.services.player_quest_parser import parse_player_quest_status


async def generate_optimization_plan(request: OptimizationRequest) -> OptimizationResponse:
    repo = get_quest_repository()
    target_quest = repo.get(request.target_goal)
    if not target_quest:
        raise HTTPException(
            status_code=404,
            detail=f"Goal quest '{request.target_goal}' not found in quest database.",
        )

    # Use cached data or fetch live data if cache doesn't exist
    player = await fetch_player_profile(request.username, request.account_type)

    # Merge finished quests from the exporter with the player profile
    player_completed_quests = set(player.quests_status)
    raw_quest_data = (
        request.quests_status
        if request.quests_status is not None
        else request.completed_quests
    )
    if raw_quest_data:
        finished_quests = parse_player_quest_status(raw_quest_data)
        player_completed_quests.update(finished_quests)

    # Resolve prerequisite tree
    missing_quests = get_missing_quests(request.target_goal, player_completed_quests, repo=repo)

    # If goal is already completed, return an immediate 0-hour plan
    if not missing_quests:
        return OptimizationResponse(
            goal_name=target_quest.name,
            total_hours_remaining=0.0,
            missing_quests=[],
            skill_deficits=[],
            roadmap=[
                RoadmapStep(
                    step_number=1,
                    step_type="complete",
                    title="Goal Already Completed!",
                    description=f"You have already completed {target_quest.name}.",
                    estimated_hours=0.0,
                )
            ],
        )

    skill_requirements = get_skill_requirements(missing_quests)

    simulator = OptimizationSimulator(
        player=player,
        missing_quests=missing_quests,
        target_quest=target_quest,
        target_goal=request.target_goal,
        player_completed_quests=player_completed_quests,
        custom_xp_rates=request.custom_xp_rates,
        repo=repo,
    )
    simulator.run()

    skill_deficits = simulator.build_skill_deficits(skill_requirements)
    total_hours = round(sum(step.estimated_hours for step in simulator.roadmap), 2)

    return OptimizationResponse(
        goal_name=target_quest.name,
        total_hours_remaining=total_hours,
        missing_quests=[q.name for q in simulator.ordered_completed_quests],
        skill_deficits=skill_deficits,
        roadmap=simulator.roadmap,
    )


def _collect_prerequisites_dfs(
    quest_name: str,
    completed_lower: set[str],
    visited: set[str],
    collected: list[Quest],
    repo: QuestRepository,
) -> None:
    """Recursive helper function for post-order DFS prerequisite collection."""
    q_lower = quest_name.strip().lower()
    if q_lower in completed_lower or q_lower in visited:
        return
    visited.add(q_lower)

    quest = repo.get(quest_name)
    if not quest:
        return

    for prereq in quest.requirements.quests:
        _collect_prerequisites_dfs(prereq, completed_lower, visited, collected, repo)

    collected.append(quest)


def get_missing_quests(
    target_goal: str,
    completed_quests: set[str] | list[str],
    repo: QuestRepository | None = None,
) -> list[Quest]:
    """Recursively resolves missing prerequisites for the target goal via post-order DFS."""
    if repo is None:
        repo = get_quest_repository()
    completed_lower = {q.strip().lower() for q in completed_quests}
    visited: set[str] = set()
    missing_quests: list[Quest] = []
    _collect_prerequisites_dfs(target_goal, completed_lower, visited, missing_quests, repo)
    return missing_quests


def get_skill_requirements(missing_quests: list[Quest]) -> dict[Skill, int]:
    """Finds the maximum required level for each skill across all missing quests."""
    skill_requirements: dict[Skill, int] = {}
    for quest in missing_quests:
        for skill, required_level in quest.requirements.skills.items():
            if required_level > skill_requirements.get(skill, 0):
                skill_requirements[skill] = required_level
    return skill_requirements
