from fastapi import HTTPException
from app.core.skills import Skill, XP_TABLE, xp_to_level
from app.models.plan import OptimizationResponse, OptimizationRequest, SkillDeficit, RoadmapStep
from app.models.quest import Quest
from app.services.hiscores import fetch_player_profile
from app.services.dataloader import QUEST_DB
from app.services.optimizer.methods import get_skill_rate


async def generate_optimization_plan(request: OptimizationRequest) -> OptimizationResponse:
    # Check if quest actually exists in database
    if request.target_goal not in QUEST_DB:
        raise HTTPException(
            status_code=404, 
            detail=f"Goal quest '{request.target_goal}' not found in quest database."
        )

    target_quest = QUEST_DB[request.target_goal]

    # Use cached data or fetch live data if cache doesnt exist
    player = await fetch_player_profile(request.username, request.account_type)

    # If the request contains completed quests then update the player profile with them
    if request.completed_quests:
        player.completed_quests.update(request.completed_quests)

    # Get missing quests
    missing_quests = get_missing_quests(request.target_goal, player.completed_quests)

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
    # (Gemini wrote this I have no idea how it works)
    simulated_xp: dict[Skill, int] = {
        skill: (player.skills[skill].xp if skill in player.skills else (1154 if skill == Skill.HITPOINTS else 0))
        for skill in Skill
    }
    initial_xp: dict[Skill, int] = dict(simulated_xp)
    hours_per_skill: dict[Skill, float] = {skill: 0.0 for skill in Skill}
    quest_xp_awarded: dict[Skill, int] = {skill: 0 for skill in Skill}

    roadmap: list[RoadmapStep] = []
    step_counter = 1

    for quest in missing_quests:
        # Step A: Before this quest can be started, train any deficient prerequisite skills
        for skill, required_level in quest.requirements.skills.items():
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
                            f"(+{xp_diff:,} XP needed for {quest.name}) at ~{rate:,} XP/hr."
                        ),
                        estimated_hours=training_hours
                    )
                )
                step_counter += 1
                simulated_xp[skill] = required_xp

        # Step B: Complete the quest and claim its XP rewards
        rewards_list = [
            f"+{xp:,} {sk.value.title()} XP" 
            for sk, xp in quest.xp_rewards.items()
        ]
        reward_desc = f"Grants: {', '.join(rewards_list)}" if rewards_list else "Unlocks downstream progression."

        roadmap.append(
            RoadmapStep(
                step_number=step_counter,
                step_type="quest",
                title=f"Complete {quest.name}",
                description=reward_desc,
                estimated_hours=0.0
            )
        )
        step_counter += 1

        # Apply quest XP rewards to our simulation
        for sk, xp in quest.xp_rewards.items():
            simulated_xp[sk] += xp
            quest_xp_awarded[sk] += xp

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
        missing_quests=[q.name for q in missing_quests],
        skill_deficits=skill_deficits,
        roadmap=roadmap
    )


# Function to recursively search a tree of quest prerequisites to check for completion
def get_missing_quests(target_goal: str, completed_quests: set[str] | list[str]) -> list[Quest]:
    missing_quests: list[Quest] = []
    visited_quests: set[str] = set()

    def visit(quest_id: str):
        # If quest is already done then no work needs to be done
        if quest_id in completed_quests:
            return

        # Check if quest has already been searched by DFS
        if quest_id in visited_quests:
            return

        visited_quests.add(quest_id)

        if quest_id not in QUEST_DB:
            return

        quest = QUEST_DB[quest_id]

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

