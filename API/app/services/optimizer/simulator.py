from app.core.skills import Skill, XP_TABLE, xp_to_level
from app.models.plan import RoadmapStep, SkillDeficit
from app.models.player import PlayerProfile
from app.models.quest import Quest
from app.repositories.quest_repository import QuestRepository, get_quest_repository
from app.services.optimizer.methods import get_skill_rate

# Estimated time (in hours) to complete official quest lengths
QUEST_ESTIMATED_TIME: dict[str, float] = {
    "very short": 0.08,
    "short": 0.2,
    "short - medium": 0.33,
    "medium": 0.5,
    "long": 1.0,
    "very long": 2.25,
}


class OptimizationSimulator:
    """
    Simulates quest and skill progression to produce an optimal roadmap.

    Encapsulates simulation state (simulated XP, completed quests, QP, roadmap steps)
    and eliminates nested closures from the engine.
    """

    def __init__(
        self,
        player: PlayerProfile,
        missing_quests: list[Quest],
        target_quest: Quest,
        target_goal: str,
        player_completed_quests: set[str],
        custom_xp_rates: dict[Skill, int] | None = None,
        repo: QuestRepository | None = None,
    ):
        self.player = player
        self.missing_quests = missing_quests
        self.target_quest = target_quest
        self.target_goal = target_goal
        self.custom_xp_rates = custom_xp_rates
        self.repo = repo if repo is not None else get_quest_repository()

        # Initialize simulated XP and baseline tracking
        self.simulated_xp: dict[Skill, int] = {
            skill: (
                player.skills[skill].xp
                if skill in player.skills
                # Hit Points starts at level 10 or 1154 experience
                else (1154 if skill == Skill.HITPOINTS else 0)
            )
            for skill in Skill
        }
        self.initial_xp: dict[Skill, int] = dict(self.simulated_xp)
        self.hours_per_skill: dict[Skill, float] = {skill: 0.0 for skill in Skill}
        self.quest_xp_awarded: dict[Skill, int] = {skill: 0 for skill in Skill}

        self.roadmap: list[RoadmapStep] = []
        self.step_counter: int = 1

        self.remaining_quests: dict[str, Quest] = {q.name: q for q in missing_quests}
        self.completed_names: set[str] = {q.lower() for q in player_completed_quests}
        self.current_qp: int = sum(self._get_quest_qp(q) for q in player_completed_quests)
        self.ordered_completed_quests: list[Quest] = []

    # Get quest points for a given quest, if it doesnt exist return 0
    def _get_quest_qp(self, quest_name: str) -> int:
        quest = self.repo.get(quest_name)
        return quest.quest_points if quest else 0

    def candidate_sort_key(self, quest: Quest) -> tuple[float, float, str]:
        """
        Calculates sort priority for quest candidates:
        1. Estimated quest duration (shortest first)
        2. Required training hours for deficit skills
        3. Alphabetical quest name for deterministic ordering
        """
        q_time = QUEST_ESTIMATED_TIME.get(quest.length.strip().lower(), 0.5)
        needed_training_hours = 0.0
        for skill, req_level in quest.requirements.skills.items():
            req_xp = XP_TABLE[min(req_level, 99)]
            curr_xp = self.simulated_xp[skill]
            if curr_xp < req_xp:
                rate = get_skill_rate(skill, self.custom_xp_rates)
                needed_training_hours += (req_xp - curr_xp) / rate
        return (q_time, needed_training_hours, quest.name)

    def is_quest_doable_without_skilling(self, quest: Quest) -> bool:
        """Returns True if the player meets all skill requirements without additional training."""
        return all(
            xp_to_level(self.simulated_xp[skill]) >= req_level
            for skill, req_level in quest.requirements.skills.items()
        )

    def get_ready_candidates(self) -> list[Quest]:
        """Returns quests whose quest prerequisites are satisfied, preferring QP-ready candidates."""
        ready = [
            q
            for q in self.remaining_quests.values()
            if all(prereq.lower() in self.completed_names for prereq in q.requirements.quests)
        ]
        if not ready:
            # Fallback to avoid deadlock if circular or unresolvable dependencies exist
            ready = list(self.remaining_quests.values())

        qp_ready = [q for q in ready if self.current_qp >= q.requirements.quest_points]
        return qp_ready if qp_ready else ready

    def select_next_quest(self) -> Quest:
        """Selects the next optimal quest based on skilling readiness and duration."""
        candidates = self.get_ready_candidates()
        doable_now = [q for q in candidates if self.is_quest_doable_without_skilling(q)]
        if doable_now:
            return min(doable_now, key=self.candidate_sort_key)
        return min(candidates, key=self.candidate_sort_key)

    def train_prerequisites_for_quest(self, quest: Quest) -> None:
        """Generates training roadmap steps for any skill requirements not yet met."""
        for skill, required_level in quest.requirements.skills.items():
            required_xp = XP_TABLE[min(required_level, 99)]
            current_xp = self.simulated_xp[skill]

            if current_xp < required_xp:
                xp_diff = required_xp - current_xp
                rate = get_skill_rate(skill, self.custom_xp_rates)
                training_hours = round(xp_diff / rate, 2)
                self.hours_per_skill[skill] += training_hours

                current_lvl = xp_to_level(current_xp)
                self.roadmap.append(
                    RoadmapStep(
                        step_number=self.step_counter,
                        step_type="skill_training",
                        title=f"Train {skill.value.title()} to level {required_level}",
                        description=(
                            f"Train from level {current_lvl} to {required_level} "
                            f"(+{xp_diff:,} XP needed for {quest.name}) at ~{rate:,} XP/hr."
                        ),
                        estimated_hours=training_hours,
                    )
                )
                self.step_counter += 1
                self.simulated_xp[skill] = required_xp

    def format_quest_description(self, quest: Quest) -> str:
        """Constructs human-readable description indicating XP rewards and downstream unlock context."""
        parts: list[str] = []
        rewards_list = [
            f"+{xp:,} {sk.value.title()} XP"
            for sk, xp in quest.xp_rewards.items()
        ]
        if rewards_list:
            parts.append(f"Grants: {', '.join(rewards_list)}")

        downstream = [
            q
            for q in self.missing_quests
            if q.name != quest.name
            and any(req.lower() == quest.name.lower() for req in q.requirements.quests)
        ]
        direct_dependents = [
            d.name
            for d in downstream
            if not any(
                any(req.lower() == other.name.lower() for req in d.requirements.quests)
                for other in downstream
                if other.name != d.name
            )
        ]

        if direct_dependents:
            parts.append(f"Prerequisite for {', '.join(direct_dependents)}")
        elif quest.name.lower() != self.target_quest.name.lower():
            parts.append(f"Prerequisite for {self.target_quest.name}")

        return ". ".join(parts) + "." if parts else f"Goal {self.target_quest.name} completed!"

    def complete_quest(self, quest: Quest) -> None:
        """Advances simulation state with quest completion, roadmap step, and XP rewards."""
        desc = self.format_quest_description(quest)
        self.roadmap.append(
            RoadmapStep(
                step_number=self.step_counter,
                step_type="quest",
                title=f"Complete {quest.name}",
                description=desc,
                estimated_hours=QUEST_ESTIMATED_TIME.get(quest.length.strip().lower(), 0.5),
            )
        )
        self.step_counter += 1

        # Apply quest XP rewards ONLY for prerequisite quests, not the final goal itself
        is_target_goal = (
            quest.id == self.target_quest.id
            or quest.name.lower() == self.target_quest.name.lower()
            or quest.id == self.target_goal
            or quest.name.lower() == self.target_goal.lower()
        )
        if not is_target_goal:
            for sk, xp in quest.xp_rewards.items():
                self.simulated_xp[sk] += xp
                self.quest_xp_awarded[sk] += xp

        self.completed_names.add(quest.name.lower())
        self.current_qp += quest.quest_points
        self.ordered_completed_quests.append(quest)
        del self.remaining_quests[quest.name]

    def run(self) -> None:
        """Executes the greedy simulation until all remaining quests are completed."""
        while self.remaining_quests:
            best_quest = self.select_next_quest()
            self.train_prerequisites_for_quest(best_quest)
            self.complete_quest(best_quest)

    def build_skill_deficits(self, skill_requirements: dict[Skill, int]) -> list[SkillDeficit]:
        """Builds summary breakdown of initial skill vs target level, grind XP, and free quest XP."""
        deficits: list[SkillDeficit] = []
        for skill, target_level in skill_requirements.items():
            init_xp = self.initial_xp[skill]
            init_level = xp_to_level(init_xp)
            target_xp = XP_TABLE[min(target_level, 99)]
            raw_xp_needed = max(0, target_xp - init_xp)
            free_xp = self.quest_xp_awarded.get(skill, 0)
            net_grind_xp = max(0, raw_xp_needed - free_xp)
            hours = round(self.hours_per_skill.get(skill, 0.0), 2)

            deficits.append(
                SkillDeficit(
                    skill=skill,
                    current_level=init_level,
                    target_level=target_level,
                    current_xp=init_xp,
                    target_xp=target_xp,
                    xp_needed=raw_xp_needed,
                    quest_xp_rewards=free_xp,
                    remaining_xp_to_grind=net_grind_xp,
                    estimated_hours=hours,
                )
            )
        return deficits
