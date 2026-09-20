from app.services.player_quest_parser import parse_player_quest_status
from fastapi import HTTPException
from app.core.skills import Skill, XP_TABLE, xp_to_level
from app.models.plan import OptimizationResponse, OptimizationRequest, SkillDeficit, RoadmapStep
from app.models.quest import Quest
from app.services.hiscores import fetch_player_profile
from app.services.dataloader import QUEST_DB
from app.services.optimizer.methods import get_skill_rate

# Estimated time to complete every official quest length
QUEST_ESTIMATED_TIME = {
    "very short": .08,
    "short": .2,
    "short - medium": .33,
    "medium": .5,
    "long": 1,
    "very long": 2.25
}

async def generate_optimization_plan(request: OptimizationRequest) -> OptimizationResponse:
    target_quest = QUEST_DB.get(request.target_goal)
    if not target_quest:
        for name, q in QUEST_DB.items():
            if name.lower() == request.target_goal.lower():
                target_quest = q
                break
    if not target_quest:
        raise HTTPException(
            status_code=404, 
            detail=f"Goal quest '{request.target_goal}' not found in quest database."
        )

    # Use cached data or fetch live data if cache doesnt exist
    player = await fetch_player_profile(request.username, request.account_type)

    # Merge finished quests from the exporter with the player profile
    player_completed_quests = set(player.quests_status)
    raw_quest_data = request.quests_status if request.quests_status is not None else request.completed_quests
    if raw_quest_data:
        finished_quests = parse_player_quest_status(raw_quest_data)
        player_completed_quests.update(finished_quests)

    # Get missing quests
    missing_quests = get_missing_quests(request.target_goal, player_completed_quests)

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
                    estimated_hours=0.0
                )
            ]
        )

    # Find highest 
    skill_requirements = get_skill_requirements(missing_quests)

    # Generate optimization plan accounting for quest experience rewards
    simulated_xp: dict[Skill, int] = {
        skill: (player.skills[skill].xp if skill in player.skills else (1154 if skill == Skill.HITPOINTS else 0))
        for skill in Skill
    }
    initial_xp: dict[Skill, int] = dict(simulated_xp)
    hours_per_skill: dict[Skill, float] = {skill: 0.0 for skill in Skill}
    quest_xp_awarded: dict[Skill, int] = {skill: 0 for skill in Skill}

    roadmap: list[RoadmapStep] = []
    step_counter = 1

    remaining_quests: dict[str, Quest] = {q.name: q for q in missing_quests}
    completed_names: set[str] = {q.lower() for q in player_completed_quests}

    def _resolve_qp(q_name: str) -> int:
        if q_name in QUEST_DB:
            return QUEST_DB[q_name].quest_points
        q_low = q_name.lower()
        for name, quest in QUEST_DB.items():
            if name.lower() == q_low:
                return quest.quest_points
        return 0

    current_qp: int = sum(_resolve_qp(q) for q in player_completed_quests)
    ordered_completed_quests: list[Quest] = []

    def candidate_sort_key(q: Quest):
        q_time = QUEST_ESTIMATED_TIME.get(q.length.strip().lower(), 0.5)
        needed_training_hours = 0.0
        for s, lvl in q.requirements.skills.items():
            req_xp = XP_TABLE[min(lvl, 99)]
            curr_xp = simulated_xp[s]
            if curr_xp < req_xp:
                r = get_skill_rate(s, request.custom_xp_rates)
                needed_training_hours += (req_xp - curr_xp) / r
        return (q_time, needed_training_hours, q.name)

    while remaining_quests:
        # 1. Candidate quests whose prerequisite quests are completed
        ready_candidates = [
            q for q in remaining_quests.values()
            if all(req.lower() in completed_names for req in q.requirements.quests)
        ]

        if not ready_candidates:
            # Fallback to avoid deadlock if requirements contain circular or unresolvable dependencies
            ready_candidates = list(remaining_quests.values())

        # Prefer candidates that also satisfy Quest Point requirements if available
        qp_ready = [q for q in ready_candidates if current_qp >= q.requirements.quest_points]
        candidates = qp_ready if qp_ready else ready_candidates

        # 2. Check which candidates require ZERO additional skilling right now
        doable_now = [
            q for q in candidates
            if all(xp_to_level(simulated_xp[s]) >= lvl for s, lvl in q.requirements.skills.items())
        ]

        if doable_now:
            # Prioritize completing quests over skilling; pick the shortest quest first
            best_quest = min(doable_now, key=candidate_sort_key)
        else:
            # No doable quest without skilling: pick candidate with shortest length / least training
            best_quest = min(candidates, key=candidate_sort_key)

            # Train any deficient prerequisite skills for this quest
            for skill, required_level in best_quest.requirements.skills.items():
                required_xp = XP_TABLE[min(required_level, 99)]
                current_xp = simulated_xp[skill]

                if current_xp < required_xp:
                    xp_diff = required_xp - current_xp
                    rate = get_skill_rate(skill, request.custom_xp_rates)
                    training_hours = round(xp_diff / rate, 2)
                    hours_per_skill[skill] += training_hours

                    current_lvl = xp_to_level(current_xp)
                    roadmap.append(
                        RoadmapStep(
                            step_number=step_counter,
                            step_type="skill_training",
                            title=f"Train {skill.value.title()} to level {required_level}",
                            description=(
                                f"Train from level {current_lvl} to {required_level} "
                                f"(+{xp_diff:,} XP needed for {best_quest.name}) at ~{rate:,} XP/hr."
                            ),
                            estimated_hours=training_hours
                        )
                    )
                    step_counter += 1
                    simulated_xp[skill] = required_xp

        # 3. Complete the chosen quest and claim rewards
        parts = []
        rewards_list = [
            f"+{xp:,} {sk.value.title()} XP" 
            for sk, xp in best_quest.xp_rewards.items()
        ]
        if rewards_list:
            parts.append(f"Grants: {', '.join(rewards_list)}")
        # Show specific immediate quest that chosen quest is a direct prerequisite for
        downstream = [
            q for q in missing_quests
            if q.name != best_quest.name and any(req.lower() == best_quest.name.lower() for req in q.requirements.quests)
        ]
        # Filter out indirect downstream quests (i.e. quests that depend on another quest in downstream)
        direct_dependents = [
            d.name for d in downstream
            if not any(
                any(req.lower() == other.name.lower() for req in d.requirements.quests)
                for other in downstream
                if other.name != d.name
            )
        ]

        if direct_dependents:
            parts.append(f"Prerequisite for {', '.join(direct_dependents)}")
        elif best_quest.name.lower() != target_quest.name.lower():
            parts.append(f"Prerequisite for {target_quest.name}")

        reward_desc = ". ".join(parts) + "." if parts else f"Goal {target_quest.name} completed!"

        roadmap.append(
            RoadmapStep(
                step_number=step_counter,
                step_type="quest",
                title=f"Complete {best_quest.name}",
                description=reward_desc,
                estimated_hours=QUEST_ESTIMATED_TIME.get(best_quest.length.strip().lower(), 0.5)
            )
        )
        step_counter += 1

        # Apply quest XP rewards to our simulation (ONLY for prerequisite quests, not the final goal itself!)
        if best_quest.id != request.target_goal and best_quest.name.lower() != request.target_goal.lower():
            for sk, xp in best_quest.xp_rewards.items():
                simulated_xp[sk] += xp
                quest_xp_awarded[sk] += xp

        completed_names.add(best_quest.name.lower())
        current_qp += best_quest.quest_points
        ordered_completed_quests.append(best_quest)
        del remaining_quests[best_quest.name]

    # 6. Build Skill Deficit summary breakdown
    skill_deficits: list[SkillDeficit] = []
    for skill, target_level in skill_requirements.items():
        init_xp = initial_xp[skill]
        init_level = xp_to_level(init_xp)
        target_xp = XP_TABLE[min(target_level, 99)]
        raw_xp_needed = max(0, target_xp - init_xp)
        free_xp = quest_xp_awarded.get(skill, 0)
        net_grind_xp = max(0, raw_xp_needed - free_xp)
        hours = round(hours_per_skill.get(skill, 0.0), 2)

        skill_deficits.append(
            SkillDeficit(
                skill=skill,
                current_level=init_level,
                target_level=target_level,
                current_xp=init_xp,
                target_xp=target_xp,
                xp_needed=raw_xp_needed,
                quest_xp_rewards=free_xp,
                remaining_xp_to_grind=net_grind_xp,
                estimated_hours=hours
            )
        )

    total_hours = round(sum(step.estimated_hours for step in roadmap), 2)

    return OptimizationResponse(
        goal_name=target_quest.name,
        total_hours_remaining=total_hours,
        missing_quests=[q.name for q in ordered_completed_quests],
        skill_deficits=skill_deficits,
        roadmap=roadmap
    )


# Function to recursively search a tree of quest prerequisites to check for completion
def get_missing_quests(target_goal: str, completed_quests: set[str] | list[str]) -> list[Quest]:
    missing_quests: list[Quest] = []
    visited_quests: set[str] = set()
    completed_lower = {q.lower() for q in completed_quests}

    def visit(quest_name: str):
        if quest_name.lower() in completed_lower:
            return

        if quest_name.lower() in visited_quests:
            return

        visited_quests.add(quest_name.lower())

        quest = QUEST_DB.get(quest_name)
        if not quest:
            for name, q in QUEST_DB.items():
                if name.lower() == quest_name.lower():
                    quest = q
                    break
        if not quest:
            return

        # Recursive call for each prerequisite quest
        for prerequisite in quest.requirements.quests:
            visit(prerequisite)

        missing_quests.append(quest)

    visit(target_goal)
    return missing_quests


def get_skill_requirements(missing_quests: list[Quest]) -> dict[Skill, int]:
    skill_requirements: dict[Skill, int] = {}

    for quest in missing_quests:
        for skill, required_level in quest.requirements.skills.items():
            if required_level > skill_requirements.get(skill, 0):
                skill_requirements[skill] = required_level

    return skill_requirements

