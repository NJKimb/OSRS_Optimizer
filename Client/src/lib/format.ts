import type { AccountType, Skill } from '../api'

const numberFormat = new Intl.NumberFormat('en-US')

export function formatNumber(value: number): string {
  return numberFormat.format(value)
}

export function formatHours(hours: number): string {
  if (hours <= 0) return '0 h'
  if (hours < 1) return `${Math.max(1, Math.round(hours * 60))} min`
  if (hours < 10) return `${hours.toFixed(1)} h`
  return `${formatNumber(Math.round(hours))} h`
}

export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export const ACCOUNT_TYPES: { value: AccountType; label: string }[] = [
  { value: 'main', label: 'Regular' },
  { value: 'ironman', label: 'Ironman' },
  { value: 'hardcore_ironman', label: 'Hardcore Ironman' },
  { value: 'ultimate_ironman', label: 'Ultimate Ironman' },
]

export function accountTypeLabel(type: AccountType): string {
  return ACCOUNT_TYPES.find((option) => option.value === type)?.label ?? type
}

// In-game skill tab order, read left to right
export const SKILL_ORDER: Skill[] = [
  'attack', 'hitpoints', 'mining',
  'strength', 'agility', 'smithing',
  'defence', 'herblore', 'fishing',
  'ranged', 'thieving', 'cooking',
  'prayer', 'crafting', 'firemaking',
  'magic', 'fletching', 'woodcutting',
  'runecraft', 'slayer', 'farming',
  'construction', 'hunter', 'sailing',
]

export const DIFFICULTIES = [
  'Novice',
  'Intermediate',
  'Experienced',
  'Master',
  'Grandmaster',
  'Special',
]
