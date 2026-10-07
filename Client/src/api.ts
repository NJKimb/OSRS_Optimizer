const API_URL = import.meta.env.VITE_API_URL

export type Health = {
  "status": string
}

export async function getHealth(): Promise<Health> {
  const response = await fetch(`${API_URL}/api/health`)
  if (!response.ok) {
    throw new Error(`Health check failed: ${response.status}`)
  }
  return response.json()
}