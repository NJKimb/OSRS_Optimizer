import type { AccountType, PlayerProfile } from '../api'

const STORAGE_KEY = 'osrs-optimizer-account'

type Saved = {
  username: string
  accountType: AccountType
}

function load(): Saved {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? '{}')
    return {
      username: saved.username ?? '',
      accountType: saved.accountType ?? 'main',
    }
  } catch {
    return { username: '', accountType: 'main' }
  }
}

// Shared between pages so the player only types their name once
export const account = $state({
  ...load(),
  goal: '',
  profile: null as PlayerProfile | null,
})

export function rememberAccount() {
  try {
    const saved: Saved = {
      username: account.username,
      accountType: account.accountType,
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(saved))
  } catch {
    // Storage can be unavailable (private mode); the app still works without it
  }
}
