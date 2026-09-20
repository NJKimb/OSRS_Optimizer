/**
 * API client for interacting with the OSRS Account Optimizer backend.
 */

// Determine API base URL dynamically
function getInitialBaseUrl() {
  const loc = window.location;
  // If served directly through FastAPI or on localhost:8000
  if (loc.hostname === 'localhost' || loc.hostname === '127.0.0.1') {
    if (loc.port === '8000') {
      return '';
    }
  }
  // If opened via file:// or another local dev port, target FastAPI default port
  return 'http://127.0.0.1:8000';
}

let apiBaseUrl = getInitialBaseUrl();

export function setApiBaseUrl(url) {
  apiBaseUrl = url.replace(/\/$/, '');
}

export function getApiBaseUrl() {
  return apiBaseUrl;
}

async function handleResponse(response) {
  if (!response.ok) {
    let errorDetail = `Request failed with status ${response.status}`;
    try {
      const errJson = await response.json();
      if (errJson.detail) {
        errorDetail = typeof errJson.detail === 'string' ? errJson.detail : JSON.stringify(errJson.detail);
      }
    } catch {
      // ignore
    }
    throw new Error(errorDetail);
  }
  return await response.json();
}

/**
 * Check if the backend API is online and healthy.
 */
export async function checkHealth() {
  try {
    const res = await fetch(`${apiBaseUrl}/api/health`, { method: 'GET' });
    if (!res.ok) return false;
    const data = await res.json();
    return data.status === 'healthy';
  } catch {
    return false;
  }
}

/**
 * Fetch list of all quests with optional search and difficulty filtering.
 */
export async function fetchQuests(search = '', difficulty = '') {
  const params = new URLSearchParams();
  if (search) params.append('search', search);
  if (difficulty) params.append('difficulty', difficulty);

  const query = params.toString() ? `?${params.toString()}` : '';
  const res = await fetch(`${apiBaseUrl}/api/quests${query}`);
  return handleResponse(res);
}

/**
 * Fetch a specific quest by name or slug.
 */
export async function fetchQuest(questName) {
  const res = await fetch(`${apiBaseUrl}/api/quests/${encodeURIComponent(questName)}`);
  return handleResponse(res);
}

/**
 * Fetch player stats from Jagex Hiscores via the backend.
 */
export async function fetchPlayer(username, accountType = 'main') {
  const params = new URLSearchParams({ account_type: accountType });
  const res = await fetch(`${apiBaseUrl}/api/player/${encodeURIComponent(username)}?${params}`);
  return handleResponse(res);
}

/**
 * Request an optimal roadmap and skill deficit plan.
 */
export async function generatePlan(requestPayload) {
  const res = await fetch(`${apiBaseUrl}/api/optimize/plan`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(requestPayload)
  });
  return handleResponse(res);
}
