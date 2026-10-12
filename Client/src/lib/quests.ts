import { listQuests, type Quest } from '../api'

let cached: Promise<Quest[]> | null = null

// The quest list never changes while the app is open, so fetch it once
export function allQuests(): Promise<Quest[]> {
  cached ??= listQuests()
    .then((quests) => quests.sort((a, b) => a.name.localeCompare(b.name)))
    .catch((error) => {
      cached = null
      throw error
    })
  return cached
}
