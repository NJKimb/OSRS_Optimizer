const API_URL = import.meta.env.VITE_API_URL

export type Skill =
  | 'overall'
  | 'attack'
  | 'defence'
  | 'strength'
  | 'hitpoints'
  | 'ranged'
  | 'prayer'
  | 'magic'
  | 'cooking'
  | 'woodcutting'
  | 'fletching'
  | 'fishing'
  | 'firemaking'
  | 'crafting'
  | 'smithing'
  | 'mining'
  | 'herblore'
  | 'agility'
  | 'thieving'
  | 'slayer'
  | 'farming'
  | 'runecraft'
  | 'hunter'
  | 'construction'
  | 'sailing'

export type AccountType = 
  | 'main'
  | 'ironman'
  | 'hardcore_ironman'
  | 'ultimate_ironman'

export type SkillDetail = {
  'level': number
  'xp': number
  'rank': number
}

export type PlayerProfile = {
  'username': string
  'account_type': AccountType
  'skills': Record<Skill, SkillDetail>
  'quests_status': string[]
}

export type Health = {
  'status': string
}

export async function getHealth(): Promise<Health> {
  const response = await fetch(`${API_URL}/api/health`)
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`)
  }
  return response.json()
}