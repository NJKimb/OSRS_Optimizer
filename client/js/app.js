/**
 * OSRS Account Optimizer - Main Application Logic
 */

import { SKILLS, SKILL_MAP, getSkillIconSvg } from './skills.js';
import { PRESET_GOALS, DEMO_ACCOUNT } from './presets.js';
import * as api from './api.js';

// Application State
const state = {
  allQuests: [],
  selectedGoal: 'Song of the Elves',
  questsStatusData: null,
  detectedFinishedCount: 0,
  playerProfile: null,
  customXpRates: {},
  currentPlan: null,
  checkedSteps: new Set(),
  currentFilter: 'all',
  activeTab: 'roadmap'
};

// DOM Elements
const elements = {
  apiStatus: document.getElementById('api-status'),
  usernameInput: document.getElementById('username-input'),
  accountTypeSelect: document.getElementById('account-type-select'),
  btnFetchHiscores: document.getElementById('btn-fetch-hiscores'),
  targetGoalSelect: document.getElementById('target-goal-select'),
  presetChipsContainer: document.getElementById('preset-chips-container'),
  btnLoadDemo: document.getElementById('btn-load-demo'),
  dropzone: document.getElementById('dropzone'),
  fileInput: document.getElementById('file-input'),
  btnPasteJsonModal: document.getElementById('btn-paste-json-modal'),
  questsStatusSummary: document.getElementById('quests-status-summary'),
  questsSummaryText: document.getElementById('quests-summary-text'),
  btnClearQuests: document.getElementById('btn-clear-quests'),
  accordionToggleRates: document.getElementById('accordion-toggle-rates'),
  accordionRatesContent: document.getElementById('accordion-rates-content'),
  ratesGrid: document.getElementById('rates-grid'),
  btnResetRates: document.getElementById('btn-reset-rates'),
  btnGeneratePlan: document.getElementById('btn-generate-plan'),
  planButtonText: document.getElementById('plan-button-text'),
  planSpinner: document.getElementById('plan-spinner'),
  
  // Tabs & Views
  tabRoadmap: document.getElementById('tab-roadmap'),
  tabDeficits: document.getElementById('tab-deficits'),
  tabStats: document.getElementById('tab-stats'),
  tabQuests: document.getElementById('tab-quests'),
  viewRoadmap: document.getElementById('view-roadmap'),
  viewDeficits: document.getElementById('view-deficits'),
  viewStats: document.getElementById('view-stats'),
  viewQuests: document.getElementById('view-quests'),

  // Results Section
  resultsContainer: document.getElementById('results-container'),
  metricGoal: document.getElementById('metric-goal'),
  metricHours: document.getElementById('metric-hours'),
  metricQuestsCount: document.getElementById('metric-quests-count'),
  metricXpGrind: document.getElementById('metric-xp-grind'),
  metricXpReward: document.getElementById('metric-xp-reward'),

  // Roadmap Elements
  timelineContainer: document.getElementById('timeline-container'),
  progressContainer: document.getElementById('progress-container'),
  progressLabel: document.getElementById('progress-label'),
  progressPercent: document.getElementById('progress-percent'),
  progressBarFill: document.getElementById('progress-bar-fill'),
  filterAll: document.getElementById('filter-all'),
  filterQuests: document.getElementById('filter-quests'),
  filterSkilling: document.getElementById('filter-skilling'),
  btnCopyMarkdown: document.getElementById('btn-copy-markdown'),

  // Deficits Elements
  deficitsGrid: document.getElementById('deficits-grid'),
  deficitsEmpty: document.getElementById('deficits-empty'),

  // Player Stats Grid
  statsGrid: document.getElementById('stats-grid'),
  statsEmpty: document.getElementById('stats-empty'),

  // Quest Explorer Table
  questSearchInput: document.getElementById('quest-search-input'),
  questDifficultyFilter: document.getElementById('quest-difficulty-filter'),
  questTableBody: document.getElementById('quest-table-body'),

  // Paste JSON Modal
  pasteModal: document.getElementById('paste-modal'),
  pasteTextarea: document.getElementById('paste-textarea'),
  btnApplyPaste: document.getElementById('btn-apply-paste'),
  btnClosePaste: document.getElementById('btn-close-paste'),

  // Toast Container
  toastContainer: document.getElementById('toast-container')
};

// ============================================================================
// Notification / Toast Helpers
// ============================================================================
function showToast(message, type = 'info') {
  const toast = document.createElement('div');
  toast.className = 'toast';
  const icon = type === 'error' ? '⚠️' : (type === 'success' ? '✅' : 'ℹ️');
  toast.innerHTML = `<span>${icon}</span><span>${message}</span>`;
  elements.toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateY(10px)';
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// ============================================================================
// Initialization
// ============================================================================
async function initApp() {
  renderPresetChips();
  renderRatesInputs();
  bindEventListeners();
  await checkBackendStatus();
  await loadQuestsDirectory();
}

async function checkBackendStatus() {
  const isHealthy = await api.checkHealth();
  if (isHealthy) {
    elements.apiStatus.className = 'status-badge online';
    elements.apiStatus.innerHTML = '<span class="status-dot"></span> API Online';
  } else {
    elements.apiStatus.className = 'status-badge offline';
    elements.apiStatus.innerHTML = '<span class="status-dot"></span> API Offline';
  }
}

// ============================================================================
// Renderers
// ============================================================================

function renderPresetChips() {
  elements.presetChipsContainer.innerHTML = '';
  PRESET_GOALS.forEach(preset => {
    const chip = document.createElement('button');
    chip.type = 'button';
    chip.className = `chip-btn ${preset.name === state.selectedGoal ? 'active' : ''}`;
    chip.dataset.goal = preset.name;
    chip.innerHTML = `<span>${preset.icon}</span> <strong>${preset.name}</strong> <span style="font-size:0.75rem; opacity:0.7;">(${preset.tag})</span>`;
    chip.addEventListener('click', () => {
      selectGoal(preset.name);
    });
    elements.presetChipsContainer.appendChild(chip);
  });
}

function selectGoal(goalName) {
  state.selectedGoal = goalName;
  elements.targetGoalSelect.value = goalName;
  document.querySelectorAll('.chip-btn').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.goal === goalName);
  });
}

function renderRatesInputs() {
  elements.ratesGrid.innerHTML = '';
  SKILLS.forEach(skill => {
    const item = document.createElement('div');
    item.className = 'rate-item';
    item.innerHTML = `
      <label class="rate-label" for="rate-${skill.id}">
        ${getSkillIconSvg(skill.id, 14)}
        <span>${skill.name}</span>
      </label>
      <input type="number" id="rate-${skill.id}" class="rate-input" 
             value="${skill.defaultRate}" step="5000" min="5000" max="1000000" 
             data-skill="${skill.id}">
    `;
    const input = item.querySelector('input');
    input.addEventListener('input', (e) => {
      const val = parseInt(e.target.value, 10);
      if (!isNaN(val) && val > 0) {
        state.customXpRates[skill.id] = val;
      }
    });
    elements.ratesGrid.appendChild(item);
  });
}

async function loadQuestsDirectory() {
  try {
    const quests = await api.fetchQuests();
    state.allQuests = quests.sort((a, b) => a.name.localeCompare(b.name));
    populateQuestDropdown(state.allQuests);
    renderQuestExplorerTable(state.allQuests);
  } catch (err) {
    console.error('Failed to load quests directory:', err);
    showToast('Failed to load quest directory from API', 'error');
  }
}

function populateQuestDropdown(quests) {
  elements.targetGoalSelect.innerHTML = '';
  quests.forEach(quest => {
    const opt = document.createElement('option');
    opt.value = quest.name;
    opt.textContent = `${quest.name} (${quest.difficulty})`;
    if (quest.name.toLowerCase() === state.selectedGoal.toLowerCase()) {
      opt.selected = true;
    }
    elements.targetGoalSelect.appendChild(opt);
  });
}

// ============================================================================
// RuneLite Character Exporter & Quests Parsing
// ============================================================================
function parseQuestsStatusInput(jsonData) {
  if (!jsonData) return 0;
  let count = 0;
  try {
    if (typeof jsonData === 'string') {
      jsonData = JSON.parse(jsonData);
    }
    if (jsonData.quests && Array.isArray(jsonData.quests)) {
      count = jsonData.quests.filter(q => q.state && q.state.toUpperCase() === 'FINISHED').length;
    } else if (Array.isArray(jsonData)) {
      count = jsonData.filter(q => (q.state && q.state.toUpperCase() === 'FINISHED') || typeof q === 'string').length;
    } else if (typeof jsonData === 'object') {
      for (const key in jsonData) {
        const val = jsonData[key];
        const state = typeof val === 'object' && val !== null ? (val.state || val.status) : val;
        if (state && String(state).toUpperCase() === 'FINISHED') count++;
      }
    }
  } catch (e) {
    console.warn('Error calculating finished quest count:', e);
  }
  return count;
}

function setQuestStatusData(data, sourceLabel = 'quests.json') {
  state.questsStatusData = data;
  state.detectedFinishedCount = parseQuestsStatusInput(data);
  
  elements.questsSummaryText.textContent = `✅ Loaded ${state.detectedFinishedCount} completed quests from ${sourceLabel}`;
  elements.questsStatusSummary.style.display = 'flex';
  showToast(`Loaded ${state.detectedFinishedCount} finished quests!`, 'success');
}

function clearQuestStatusData() {
  state.questsStatusData = null;
  state.detectedFinishedCount = 0;
  elements.questsStatusSummary.style.display = 'none';
  elements.fileInput.value = '';
}

// ============================================================================
// Event Listeners Setup
// ============================================================================
function bindEventListeners() {
  // Goal select change
  elements.targetGoalSelect.addEventListener('change', (e) => {
    selectGoal(e.target.value);
  });

  // Load Demo Account
  elements.btnLoadDemo.addEventListener('click', () => {
    elements.usernameInput.value = DEMO_ACCOUNT.username;
    elements.accountTypeSelect.value = DEMO_ACCOUNT.account_type;
    selectGoal(DEMO_ACCOUNT.target_goal);
    setQuestStatusData(DEMO_ACCOUNT.quests_status, 'demo profile');
    showToast(`Loaded demo account: ${DEMO_ACCOUNT.username}`, 'success');
  });

  // File Dropzone
  elements.dropzone.addEventListener('click', () => elements.fileInput.click());
  elements.dropzone.addEventListener('dragover', (e) => {
    e.preventDefault();
    elements.dropzone.classList.add('dragover');
  });
  elements.dropzone.addEventListener('dragleave', () => {
    elements.dropzone.classList.remove('dragover');
  });
  elements.dropzone.addEventListener('drop', (e) => {
    e.preventDefault();
    elements.dropzone.classList.remove('dragover');
    if (e.dataTransfer.files.length) {
      handleFileUpload(e.dataTransfer.files[0]);
    }
  });
  elements.fileInput.addEventListener('change', (e) => {
    if (e.target.files.length) {
      handleFileUpload(e.target.files[0]);
    }
  });

  // Paste JSON Modal
  elements.btnPasteJsonModal.addEventListener('click', () => {
    elements.pasteModal.classList.add('open');
    elements.pasteTextarea.focus();
  });
  elements.btnClosePaste.addEventListener('click', () => {
    elements.pasteModal.classList.remove('open');
  });
  elements.btnApplyPaste.addEventListener('click', () => {
    const text = elements.pasteTextarea.value.trim();
    if (!text) return;
    try {
      const parsed = JSON.parse(text);
      setQuestStatusData(parsed, 'pasted JSON');
      elements.pasteModal.classList.remove('open');
      elements.pasteTextarea.value = '';
    } catch {
      showToast('Invalid JSON provided. Please check formatting.', 'error');
    }
  });

  // Clear Quests
  elements.btnClearQuests.addEventListener('click', clearQuestStatusData);

  // Accordion Toggle for Rates
  elements.accordionToggleRates.addEventListener('click', () => {
    elements.accordionRatesContent.classList.toggle('open');
    const isOpen = elements.accordionRatesContent.classList.contains('open');
    elements.accordionToggleRates.innerHTML = isOpen ? '▲ Hide Skilling XP Rates' : '▼ Customize Skilling XP Rates (XP/hr)';
  });

  // Reset Rates
  elements.btnResetRates.addEventListener('click', () => {
    state.customXpRates = {};
    renderRatesInputs();
    showToast('Reset all XP rates to mid-game defaults.', 'info');
  });

  // Fetch Hiscores
  elements.btnFetchHiscores.addEventListener('click', handleFetchHiscores);

  // Generate Plan
  elements.btnGeneratePlan.addEventListener('click', handleGeneratePlan);

  // Tab switching
  elements.tabRoadmap.addEventListener('click', () => switchTab('roadmap'));
  elements.tabDeficits.addEventListener('click', () => switchTab('deficits'));
  elements.tabStats.addEventListener('click', () => switchTab('stats'));
  elements.tabQuests.addEventListener('click', () => switchTab('quests'));

  // Roadmap Filters
  elements.filterAll.addEventListener('click', () => setRoadmapFilter('all'));
  elements.filterQuests.addEventListener('click', () => setRoadmapFilter('quest'));
  elements.filterSkilling.addEventListener('click', () => setRoadmapFilter('skill_training'));

  // Copy Markdown
  elements.btnCopyMarkdown.addEventListener('click', copyRoadmapToClipboard);

  // Quest explorer search
  elements.questSearchInput.addEventListener('input', filterQuestTable);
  elements.questDifficultyFilter.addEventListener('change', filterQuestTable);
}

function handleFileUpload(file) {
  if (!file.name.endsWith('.json')) {
    showToast('Please upload a JSON file (e.g. quests.json).', 'error');
    return;
  }
  const reader = new FileReader();
  reader.onload = (event) => {
    try {
      const json = JSON.parse(event.target.result);
      setQuestStatusData(json, file.name);
    } catch {
      showToast('Failed to parse uploaded JSON file.', 'error');
    }
  };
  reader.readAsText(file);
}

// ============================================================================
// Hiscores Fetching & Display
// ============================================================================
async function handleFetchHiscores() {
  const username = elements.usernameInput.value.trim();
  const accountType = elements.accountTypeSelect.value;
  if (!username) {
    showToast('Please enter an OSRS username first.', 'error');
    elements.usernameInput.focus();
    return;
  }

  elements.btnFetchHiscores.disabled = true;
  elements.btnFetchHiscores.innerHTML = '<span class="spinner" style="width:14px;height:14px;"></span> Fetching...';

  try {
    const profile = await api.fetchPlayer(username, accountType);
    state.playerProfile = profile;
    renderPlayerStats(profile);
    showToast(`Fetched hiscore stats for ${profile.username}!`, 'success');
  } catch (err) {
    showToast(`Failed to fetch stats: ${err.message}`, 'error');
  } finally {
    elements.btnFetchHiscores.disabled = false;
    elements.btnFetchHiscores.innerHTML = '<span>📊 Fetch Stats</span>';
  }
}

function renderPlayerStats(profile) {
  if (!profile || !profile.skills) return;
  elements.statsEmpty.style.display = 'none';
  elements.statsGrid.style.display = 'grid';
  elements.statsGrid.innerHTML = '';

  SKILLS.forEach(skill => {
    const detail = profile.skills[skill.id] || { level: 1, xp: 0 };
    const card = document.createElement('div');
    card.className = 'metric-card';
    card.innerHTML = `
      <div class="metric-label">
        ${getSkillIconSvg(skill.id, 16)}
        <span>${skill.name}</span>
      </div>
      <div class="metric-value highlight" style="font-size:1.4rem;">${detail.level}</div>
      <div class="metric-sub">${detail.xp.toLocaleString()} XP</div>
    `;
    elements.statsGrid.appendChild(card);
  });
}

// ============================================================================
// Plan Generation
// ============================================================================
async function handleGeneratePlan() {
  const username = elements.usernameInput.value.trim();
  const accountType = elements.accountTypeSelect.value;
  const targetGoal = elements.targetGoalSelect.value || state.selectedGoal;

  if (!username) {
    showToast('Please enter a username to optimize for.', 'error');
    elements.usernameInput.focus();
    return;
  }
  if (!targetGoal) {
    showToast('Please select a target goal.', 'error');
    return;
  }

  // Set loading state
  elements.btnGeneratePlan.disabled = true;
  elements.planButtonText.textContent = 'Simulating Optimal Path...';
  elements.planSpinner.style.display = 'inline-block';

  try {
    const payload = {
      username: username,
      account_type: accountType,
      target_goal: targetGoal,
      quests_status: state.questsStatusData,
      custom_xp_rates: state.customXpRates
    };

    const plan = await api.generatePlan(payload);
    state.currentPlan = plan;

    // Load saved checklist for this user + goal
    loadSavedChecklist(username, targetGoal);

    // Render results
    renderResults(plan);
    showToast(`Optimization plan ready for ${plan.goal_name}!`, 'success');
    switchTab('roadmap');
  } catch (err) {
    console.error('Plan optimization error:', err);
    showToast(`Optimization failed: ${err.message}`, 'error');
  } finally {
    elements.btnGeneratePlan.disabled = false;
    elements.planButtonText.textContent = 'Generate Optimal Roadmap';
    elements.planSpinner.style.display = 'none';
  }
}

// ============================================================================
// Render Plan Results
// ============================================================================
function renderResults(plan) {
  elements.resultsContainer.style.display = 'block';

  // Metrics
  elements.metricGoal.textContent = plan.goal_name;
  elements.metricHours.textContent = `${plan.total_hours_remaining} hrs`;
  elements.metricQuestsCount.textContent = `${plan.missing_quests.length} quests`;

  const totalGrindXp = plan.skill_deficits.reduce((sum, d) => sum + (d.remaining_xp_to_grind || 0), 0);
  const totalRewardXp = plan.skill_deficits.reduce((sum, d) => sum + (d.quest_xp_rewards || 0), 0);

  elements.metricXpGrind.textContent = totalGrindXp > 0 ? `${(totalGrindXp / 1000).toFixed(1)}k XP` : '0 XP';
  elements.metricXpReward.textContent = totalRewardXp > 0 ? `+${(totalRewardXp / 1000).toFixed(1)}k XP` : '0 XP';

  // Render Roadmap
  renderRoadmapTimeline(plan.roadmap);
  updateProgressTracker();

  // Render Deficits
  renderSkillDeficits(plan.skill_deficits);
}

function renderRoadmapTimeline(steps) {
  elements.timelineContainer.innerHTML = '';

  if (!steps || steps.length === 0) {
    elements.timelineContainer.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🏆</div>
        <h3>Goal Already Completed!</h3>
        <p>Your account already meets all requirements for this goal.</p>
      </div>
    `;
    return;
  }

  steps.forEach((step, index) => {
    const isCompleted = state.checkedSteps.has(step.step_number);
    const stepEl = document.createElement('div');
    stepEl.className = `timeline-step ${isCompleted ? 'completed' : ''}`;
    stepEl.dataset.type = step.step_type;
    stepEl.dataset.stepNumber = step.step_number;

    const typeBadgeClass = step.step_type === 'quest' ? 'quest' : (step.step_type === 'complete' ? 'complete' : 'skill_training');
    const typeLabel = step.step_type === 'quest' ? 'Quest' : (step.step_type === 'complete' ? 'Finish' : 'Skill Grind');
    const durationLabel = step.estimated_hours > 0 ? `⏱️ ~${step.estimated_hours}h` : '';

    stepEl.innerHTML = `
      <div class="step-node">${step.step_number}</div>
      <div class="step-card">
        <div class="step-left">
          <input type="checkbox" class="step-checkbox" id="step-chk-${step.step_number}" ${isCompleted ? 'checked' : ''}>
          <div class="step-content">
            <div class="step-badges">
              <span class="badge-type ${typeBadgeClass}">${typeLabel}</span>
              ${durationLabel ? `<span class="step-duration">${durationLabel}</span>` : ''}
            </div>
            <div class="step-title">${step.title}</div>
            <div class="step-desc">${step.description}</div>
          </div>
        </div>
      </div>
    `;

    const checkbox = stepEl.querySelector('.step-checkbox');
    checkbox.addEventListener('change', (e) => {
      toggleStepCompletion(step.step_number, e.target.checked);
    });

    elements.timelineContainer.appendChild(stepEl);
  });

  applyRoadmapFilter();
}

function toggleStepCompletion(stepNumber, isChecked) {
  if (isChecked) {
    state.checkedSteps.add(stepNumber);
  } else {
    state.checkedSteps.delete(stepNumber);
  }

  const stepEl = document.querySelector(`.timeline-step[data-step-number="${stepNumber}"]`);
  if (stepEl) {
    stepEl.classList.toggle('completed', isChecked);
  }

  saveCurrentChecklist();
  updateProgressTracker();
}

function updateProgressTracker() {
  if (!state.currentPlan || !state.currentPlan.roadmap.length) {
    elements.progressContainer.style.display = 'none';
    return;
  }
  elements.progressContainer.style.display = 'block';
  const total = state.currentPlan.roadmap.length;
  const completed = state.checkedSteps.size;
  const percent = total > 0 ? Math.round((completed / total) * 100) : 0;

  elements.progressLabel.textContent = `Progress: Step ${completed} of ${total} finished`;
  elements.progressPercent.textContent = `${percent}%`;
  elements.progressBarFill.style.width = `${percent}%`;
}

function setRoadmapFilter(filterType) {
  state.currentFilter = filterType;
  [elements.filterAll, elements.filterQuests, elements.filterSkilling].forEach(btn => btn.classList.remove('active'));
  if (filterType === 'all') elements.filterAll.classList.add('active');
  if (filterType === 'quest') elements.filterQuests.classList.add('active');
  if (filterType === 'skill_training') elements.filterSkilling.classList.add('active');
  applyRoadmapFilter();
}

function applyRoadmapFilter() {
  const steps = elements.timelineContainer.querySelectorAll('.timeline-step');
  steps.forEach(step => {
    if (state.currentFilter === 'all' || step.dataset.type === state.currentFilter) {
      step.style.display = 'block';
    } else {
      step.style.display = 'none';
    }
  });
}

// ============================================================================
// Skill Deficits Tab
// ============================================================================
function renderSkillDeficits(deficits) {
  elements.deficitsGrid.innerHTML = '';

  if (!deficits || deficits.length === 0) {
    elements.deficitsEmpty.style.display = 'block';
    elements.deficitsGrid.style.display = 'none';
    return;
  }

  elements.deficitsEmpty.style.display = 'none';
  elements.deficitsGrid.style.display = 'grid';

  deficits.forEach(d => {
    const card = document.createElement('div');
    card.className = 'deficit-card';

    const percent = d.target_xp > 0 ? Math.min(100, Math.round((d.current_xp / d.target_xp) * 100)) : 100;

    card.innerHTML = `
      <div class="deficit-card-header">
        <div class="deficit-skill-name">
          ${getSkillIconSvg(d.skill, 20)}
          <span>${d.skill}</span>
        </div>
        <div class="deficit-levels">${d.current_level} ➔ ${d.target_level}</div>
      </div>
      <div class="deficit-progress-bar">
        <div class="deficit-progress-fill" style="width: ${percent}%;"></div>
      </div>
      <div class="deficit-stat-row">
        <span>Current XP:</span>
        <strong>${d.current_xp.toLocaleString()}</strong>
      </div>
      <div class="deficit-stat-row">
        <span>Target XP:</span>
        <strong>${d.target_xp.toLocaleString()}</strong>
      </div>
      <div class="deficit-stat-row">
        <span>Quest XP Rewards:</span>
        <strong style="color: #2ecc71;">+${d.quest_xp_rewards.toLocaleString()} XP</strong>
      </div>
      <div class="deficit-stat-row">
        <span>Remaining to Grind:</span>
        <strong style="color: #e67e22;">${d.remaining_xp_to_grind.toLocaleString()} XP</strong>
      </div>
      <div class="deficit-stat-row" style="border-top:1px solid rgba(255,255,255,0.05); padding-top:6px;">
        <span>Estimated Time:</span>
        <strong style="color: var(--gold-primary);">~${d.estimated_hours} hrs</strong>
      </div>
    `;
    elements.deficitsGrid.appendChild(card);
  });
}

// ============================================================================
// Quest Directory Tab
// ============================================================================
function renderQuestExplorerTable(quests) {
  elements.questTableBody.innerHTML = '';
  quests.forEach(q => {
    const tr = document.createElement('tr');
    
    // Format difficulty class
    const diffLower = q.difficulty.toLowerCase().replace(/ /g, '-');
    const diffClass = `diff-${diffLower}`;

    // Format skill requirements
    const reqSkills = Object.entries(q.requirements.skills || {})
      .map(([s, lvl]) => `<span style="display:inline-flex; align-items:center; gap:3px; margin-right:6px;">${getSkillIconSvg(s, 12)} ${lvl}</span>`)
      .join('') || '<span style="color:var(--text-muted); font-size:0.8rem;">None</span>';

    // Format prereq quests
    const prereqQuests = (q.requirements.quests || []).slice(0, 3).join(', ') + 
      ((q.requirements.quests || []).length > 3 ? ` (+${(q.requirements.quests.length - 3)} more)` : '') || '<span style="color:var(--text-muted); font-size:0.8rem;">None</span>';

    tr.innerHTML = `
      <td><strong>${q.name}</strong></td>
      <td><span class="difficulty-badge ${diffClass}">${q.difficulty}</span></td>
      <td>${q.length}</td>
      <td><strong style="color:var(--gold-secondary);">${q.quest_points}</strong></td>
      <td>${reqSkills}</td>
      <td style="font-size:0.82rem; color:var(--text-secondary);">${prereqQuests}</td>
      <td>
        <button class="btn btn-secondary" style="padding:4px 10px; font-size:0.75rem;" data-quest="${q.name}">
          Set Goal
        </button>
      </td>
    `;

    tr.querySelector('button').addEventListener('click', () => {
      selectGoal(q.name);
      switchTab('roadmap');
      window.scrollTo({ top: elements.targetGoalSelect.offsetTop - 100, behavior: 'smooth' });
    });

    elements.questTableBody.appendChild(tr);
  });
}

function filterQuestTable() {
  const query = elements.questSearchInput.value.toLowerCase().trim();
  const diff = elements.questDifficultyFilter.value.toLowerCase();

  const filtered = state.allQuests.filter(q => {
    const matchesName = !query || q.name.toLowerCase().includes(query);
    const matchesDiff = !diff || q.difficulty.toLowerCase() === diff;
    return matchesName && matchesDiff;
  });

  renderQuestExplorerTable(filtered);
}

// ============================================================================
// Checklist Persistence (LocalStorage)
// ============================================================================
function getStorageKey() {
  const user = elements.usernameInput.value.trim().toLowerCase();
  const goal = (state.selectedGoal || '').toLowerCase().replace(/ /g, '_');
  return `osrs_opt_${user}_${goal}`;
}

function loadSavedChecklist(user, goal) {
  state.checkedSteps.clear();
  try {
    const raw = localStorage.getItem(`osrs_opt_${user.toLowerCase()}_${goal.toLowerCase().replace(/ /g, '_')}`);
    if (raw) {
      const arr = JSON.parse(raw);
      if (Array.isArray(arr)) {
        state.checkedSteps = new Set(arr);
      }
    }
  } catch {
    // ignore
  }
}

function saveCurrentChecklist() {
  try {
    const key = getStorageKey();
    localStorage.setItem(key, JSON.stringify(Array.from(state.checkedSteps)));
  } catch {
    // ignore
  }
}

// ============================================================================
// Copy Markdown / Export
// ============================================================================
function copyRoadmapToClipboard() {
  if (!state.currentPlan || !state.currentPlan.roadmap.length) {
    showToast('No roadmap available to copy.', 'error');
    return;
  }

  const p = state.currentPlan;
  let md = `# OSRS Roadmap: ${p.goal_name}\n`;
  md += `**Total Estimated Playtime:** ${p.total_hours_remaining} hours\n`;
  md += `**Missing Quests:** ${p.missing_quests.length}\n\n`;
  md += `## Steps\n`;

  p.roadmap.forEach(step => {
    const checked = state.checkedSteps.has(step.step_number) ? '[x]' : '[ ]';
    const dur = step.estimated_hours > 0 ? ` (~${step.estimated_hours}h)` : '';
    md += `- ${checked} **Step ${step.step_number}:** ${step.title}${dur}\n  ${step.description}\n`;
  });

  navigator.clipboard.writeText(md)
    .then(() => showToast('Roadmap copied to clipboard as Markdown!', 'success'))
    .catch(() => showToast('Failed to copy to clipboard.', 'error'));
}

// ============================================================================
// Tab Switching
// ============================================================================
function switchTab(tabId) {
  state.activeTab = tabId;
  [elements.tabRoadmap, elements.tabDeficits, elements.tabStats, elements.tabQuests].forEach(t => t.classList.remove('active'));
  [elements.viewRoadmap, elements.viewDeficits, elements.viewStats, elements.viewQuests].forEach(v => v.style.display = 'none');

  if (tabId === 'roadmap') {
    elements.tabRoadmap.classList.add('active');
    elements.viewRoadmap.style.display = 'block';
  } else if (tabId === 'deficits') {
    elements.tabDeficits.classList.add('active');
    elements.viewDeficits.style.display = 'block';
  } else if (tabId === 'stats') {
    elements.tabStats.classList.add('active');
    elements.viewStats.style.display = 'block';
  } else if (tabId === 'quests') {
    elements.tabQuests.classList.add('active');
    elements.viewQuests.style.display = 'block';
  }
}

// Run app when DOM is ready
document.addEventListener('DOMContentLoaded', initApp);
