from typing import NamedTuple
from app.models.skills import Skill, xp_for_level, xp_to_level
from app.models.plan import RoadmapStep, SkillDeficit, StepType
from app.models.player import PlayerProfile
from app.models.quest import Quest
from app.repositories.quest_repository import QuestRepository, get_quest_repository
from app.services.optimizer.skill_boosts import (
    SkillBoost,
    get_min_base_level,
    get_skill_boost,
)
from app.services.optimizer.skill_methods import get_skill_rate

# Estimated time (in hours) to complete official quest lengths
QUEST_ESTIMATED_TIME: dict[str, float] = {
    "very short": 0.08,
    "short": 0.2,
    "short - medium": 0.33,
    "medium": 0.5,
    "long": 1.0,
    "very long": 2.25,
}


class SkillTarget(NamedTuple):
    base_level: int
    required_level: int
    boost: SkillBoost | None


class OptimizationSimulator:
    """
    Simulates quest and skill progression to produce a roadmap.

    Encapsulates simulation state (simulated XP, completed quests, QP, roadmap steps)
    and eliminates nested closures from the engine.
    """

    def __init__(
        self,
        player: PlayerProfile,
        missing_quests: list[Quest],
        target_quest: Quest,
        player_completed_quests: set[str],
        custom_xp_rates: dict[Skill, int] | None = None,
        quest_repository: QuestRepository | None = None,
        allow_boosts: bool = False,
    ):
        self.player = player
        self.missing_quests = missing_quests
        self.target_quest = target_quest
        self.custom_xp_rates = custom_xp_rates
        self.quest_repository = (
            quest_repository if quest_repository is not None else get_quest_repository()
        )
        self.allow_boosts = allow_boosts

        # Initialize simulated XP and baseline tracking
        self.simulated_xp: dict[Skill, int] = {
            skill: (
                player.skills[skill].xp
                if skill in player.skills
                # Hit Points starts at level 10 or 1154 experience
                else (xp_for_level(10) if skill == Skill.HITPOINTS else 0)
            )
            for skill in Skill
        }
        self.initial_xp: dict[Skill, int] = dict(self.simulated_xp)
        self.hours_per_skill: dict[Skill, float] = {skill: 0.0 for skill in Skill}
        self.grind_xp_per_skill: dict[Skill, int] = {skill: 0 for skill in Skill}
        self.quest_xp_awarded: dict[Skill, int] = {skill: 0 for skill in Skill}

        # Highest base level needed per skill, plus the boost (if any) used to reach it
        self.skill_targets: dict[Skill, SkillTarget] = {}

        self.roadmap: list[RoadmapStep] = []
        self.step_counter: int = 1

        self.remaining_quests: dict[str, Quest] = {
            quest.name: quest for quest in missing_quests
        }
        # Canonical quest names, so the rest of the simulator can compare to Quest.name
        self.completed_names: set[str] = {
            self.quest_repository.canonical_name(quest_name)
            for quest_name in player_completed_quests
        }
        self.current_qp: int = sum(
            self._get_quest_qp(quest_name) for quest_name in player_completed_quests
        )
        self.ordered_completed_quests: list[Quest] = []

        # Extra quests pulled in only to meet quest point requirements,
        # mapped to the quest whose QP requirement they help unlock
        self.qp_filler_reasons: dict[str, Quest] = {}

    def estimate_quest_completion_time(self, quest: Quest):
        return QUEST_ESTIMATED_TIME.get(quest.length.strip().lower(), 0.5)

    # Get quest points for a given quest, if it doesnt exist return 0
    def _get_quest_qp(self, quest_name: str) -> int:
        quest = self.quest_repository.get(quest_name)
        return quest.quest_points if quest else 0

    def get_required_base_level(
        self, quest: Quest, skill: Skill
    ) -> tuple[int, SkillBoost | None]:
        """
        Returns the base level the player must actually train to for a requirement,
        and the boost used to cover the gap (None if no boost applies).
        """
        required_level = quest.requirements.skills[skill]
        if self.allow_boosts and skill in quest.requirements.boostable_skills:
            boost = get_skill_boost(skill)
            base_level = get_min_base_level(required_level, boost)
            if base_level < required_level:
                return base_level, boost
        return required_level, None

    def estimate_quest_hours(self, quest: Quest) -> tuple[float, float]:
        """Returns (quest duration hours, training hours needed to meet its skill requirements)."""
        quest_duration_hours = self.estimate_quest_completion_time(quest)
        needed_training_hours = 0.0
        for skill in quest.requirements.skills:
            base_level, _ = self.get_required_base_level(quest, skill)
            required_xp = xp_for_level(base_level)
            current_xp = self.simulated_xp[skill]
            if current_xp < required_xp:
                xp_rate = get_skill_rate(skill, self.custom_xp_rates)
                needed_training_hours += (required_xp - current_xp) / xp_rate
        return quest_duration_hours, needed_training_hours

    def candidate_sort_key(self, quest: Quest) -> tuple[float, str]:
        """
        Calculates sort priority for quest candidates:
        1. Estimated quest duration + training hours required (shortest first)
        2. Alphabetical quest name for deterministic ordering
        """
        quest_duration_hours, needed_training_hours = self.estimate_quest_hours(quest)
        return (needed_training_hours + quest_duration_hours, quest.name)

    def qp_filler_sort_key(self, quest: Quest) -> tuple[float, str]:
        """Ranks filler quests by total hours spent per quest point gained."""
        quest_duration_hours, needed_training_hours = self.estimate_quest_hours(quest)
        return (
            (quest_duration_hours + needed_training_hours) / quest.quest_points,
            quest.name,
        )

    def is_quest_doable_without_skilling(self, quest: Quest) -> bool:
        """Returns True if the player meets all skill requirements without additional training."""
        return all(
            xp_to_level(self.simulated_xp[skill])
            >= self.get_required_base_level(quest, skill)[0]
            for skill in quest.requirements.skills
        )

    def get_ready_candidates(self) -> list[Quest]:
        """Returns remaining quests whose quest prerequisites are satisfied."""
        ready = [
            quest
            for quest in self.remaining_quests.values()
            if all(
                prereq in self.completed_names for prereq in quest.requirements.quests
            )
        ]
        if not ready:
            # Fallback to avoid deadlock if circular or unresolvable dependencies exist
            ready = list(self.remaining_quests.values())
        return ready

    def find_qp_filler_quest(self) -> Quest | None:
        """
        Finds the cheapest quest outside the plan that can be started right now,
        to earn quest points towards a blocked quest's QP requirement.
        """
        fillers = [
            quest
            for quest in self.quest_repository.all()
            if quest.quest_points > 0
            and quest.name not in self.completed_names
            and quest.name not in self.remaining_quests
            and self.current_qp >= quest.requirements.quest_points
            and all(
                prereq in self.completed_names for prereq in quest.requirements.quests
            )
        ]
        if not fillers:
            return None
        return min(fillers, key=self.qp_filler_sort_key)

    def select_next_quest(self) -> Quest:
        """Selects the next optimal quest based on skilling readiness and duration."""
        ready = self.get_ready_candidates()
        candidates = [
            quest
            for quest in ready
            if self.current_qp >= quest.requirements.quest_points
        ]
        if not candidates:
            # Every ready quest is blocked on quest points, so earn some elsewhere
            filler = self.find_qp_filler_quest()
            if filler:
                self.remaining_quests[filler.name] = filler
                self.qp_filler_reasons[filler.name] = min(
                    ready, key=lambda quest: quest.requirements.quest_points
                )
                return filler
            candidates = ready

        doable_now = [
            quest
            for quest in candidates
            if self.is_quest_doable_without_skilling(quest)
        ]
        if doable_now:
            return min(doable_now, key=self.candidate_sort_key)
        return min(candidates, key=self.candidate_sort_key)

    def train_prerequisites_for_quest(self, quest: Quest) -> None:
        """Generates training roadmap steps for any skill requirements not yet met."""
        for skill, required_level in quest.requirements.skills.items():
            base_level, boost = self.get_required_base_level(quest, skill)

            # If base requirement is higher than previously targeted, update the target
            previous_target = self.skill_targets.get(skill)
            if previous_target is None or (base_level, required_level) > (
                previous_target.base_level,
                previous_target.required_level,
            ):
                self.skill_targets[skill] = SkillTarget(
                    base_level, required_level, boost
                )

            required_xp = xp_for_level(base_level)
            current_xp = self.simulated_xp[skill]

            if current_xp < required_xp:
                # Record XP grind needed for this skill to reach the base level
                xp_diff = required_xp - current_xp
                # Update the total XP grind for this skill
                self.grind_xp_per_skill[skill] += xp_diff
                xp_rate = get_skill_rate(skill, self.custom_xp_rates)
                training_hours = xp_diff / xp_rate
                self.hours_per_skill[skill] += training_hours

                current_level = xp_to_level(current_xp)
                boost_note = (
                    f" Boost to {required_level} with a {boost.source}."
                    if boost
                    else ""
                )
                self.roadmap.append(
                    RoadmapStep(
                        step_number=self.step_counter,
                        step_type=StepType.SKILL_TRAINING,
                        title=f"Train {skill.value.title()} to level {base_level}",
                        description=(
                            f"Train from level {current_level} to {base_level} "
                            f"(+{xp_diff:,} XP needed for {quest.name}) at ~{xp_rate:,} XP/hr."
                            f"{boost_note}"
                        ),
                        estimated_hours=round(training_hours, 2),
                    )
                )
                self.step_counter += 1
                self.simulated_xp[skill] = required_xp

    def get_boosts_needed(self, quest: Quest) -> list[str]:
        """Lists the boosts the player must use for this quest at their simulated levels."""
        boosts_needed: list[str] = []
        for skill, required_level in quest.requirements.skills.items():
            _, boost = self.get_required_base_level(quest, skill)
            if boost and xp_to_level(self.simulated_xp[skill]) < required_level:
                boosts_needed.append(
                    f"{skill.value.title()} to {required_level} ({boost.source})"
                )
        return boosts_needed

    def format_quest_description(self, quest: Quest) -> str:
        """Constructs human-readable description indicating XP rewards and downstream unlock context."""
        parts: list[str] = []
        boosts_needed = self.get_boosts_needed(quest)
        if boosts_needed:
            parts.append(f"Boost {', '.join(boosts_needed)}")

        rewards_list = [
            f"+{xp_amount:,} {skill.value.title()} XP"
            for skill, xp_amount in quest.xp_rewards.items()
        ]
        if rewards_list:
            parts.append(f"Grants: {', '.join(rewards_list)}")

        blocked_quest = self.qp_filler_reasons.get(quest.name)
        if blocked_quest:
            parts.append(
                f"+{quest.quest_points} QP towards the "
                f"{blocked_quest.requirements.quest_points} QP needed for {blocked_quest.name}"
            )
            return ". ".join(parts) + "."

        downstream = [
            candidate_quest
            for candidate_quest in self.missing_quests
            if candidate_quest.name != quest.name
            and quest.name in candidate_quest.requirements.quests
        ]
        direct_dependents = [
            dependent_quest.name
            for dependent_quest in downstream
            if not any(
                other_quest.name in dependent_quest.requirements.quests
                for other_quest in downstream
                if other_quest.name != dependent_quest.name
            )
        ]

        if direct_dependents:
            parts.append(f"Prerequisite for {', '.join(direct_dependents)}")
        elif quest.name != self.target_quest.name:
            parts.append(f"Prerequisite for {self.target_quest.name}")

        return (
            ". ".join(parts) + "."
            if parts
            else f"Goal {self.target_quest.name} completed!"
        )

    def complete_quest(self, quest: Quest) -> None:
        """Advances simulation state with quest completion, roadmap step, and XP rewards."""
        quest_description = self.format_quest_description(quest)
        self.roadmap.append(
            RoadmapStep(
                step_number=self.step_counter,
                step_type=StepType.QUEST,
                title=f"Complete {quest.name}",
                description=quest_description,
                estimated_hours=self.estimate_quest_completion_time(quest),
            )
        )
        self.step_counter += 1

        # Apply quest XP rewards ONLY for prerequisite quests, not the final goal itself
        is_target_goal = quest.name == self.target_quest.name
        if not is_target_goal:
            for skill, xp_amount in quest.xp_rewards.items():
                self.simulated_xp[skill] += xp_amount

        self.completed_names.add(quest.name)
        self.current_qp += quest.quest_points
        self.ordered_completed_quests.append(quest)
        del self.remaining_quests[quest.name]

    def run(self) -> None:
        """Executes the greedy simulation until all remaining quests are completed."""
        while self.remaining_quests:
            best_quest = self.select_next_quest()
            self.train_prerequisites_for_quest(best_quest)
            self.complete_quest(best_quest)

    def build_skill_deficits(
        self, skill_requirements: dict[Skill, int] | None = None
    ) -> list[SkillDeficit]:
        """
        Builds summary breakdown of initial skill vs target level, grind XP, and free quest XP.
        Defaults to the boost-aware targets gathered while running the simulation.
        """
        if skill_requirements is not None:
            targets = {
                skill: SkillTarget(level, level, None)
                for skill, level in skill_requirements.items()
            }
        else:
            targets = self.skill_targets

        deficits: list[SkillDeficit] = []
        for skill, target in targets.items():
            initial_xp = self.initial_xp[skill]
            initial_level = xp_to_level(initial_xp)
            target_level = target.base_level
            target_xp = xp_for_level(target_level)
            raw_xp_needed = max(0, target_xp - initial_xp)
            net_grind_xp = self.grind_xp_per_skill[skill]
            free_quest_xp = raw_xp_needed - net_grind_xp
            training_hours = round(self.hours_per_skill.get(skill, 0.0), 2)

            deficits.append(
                SkillDeficit(
                    skill=skill,
                    current_level=initial_level,
                    target_level=target_level,
                    current_xp=initial_xp,
                    target_xp=target_xp,
                    xp_needed=raw_xp_needed,
                    quest_xp_rewards=free_quest_xp,
                    remaining_xp_to_grind=net_grind_xp,
                    estimated_hours=training_hours,
                    boost=(
                        f"Boost to {target.required_level} with a {target.boost.source}"
                        if target.boost
                        else None
                    ),
                )
            )
        return deficits
