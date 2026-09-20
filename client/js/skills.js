/**
 * OSRS Skill Metadata, categories, default rates, and SVG icons.
 */

export const SKILLS = [
  { id: 'attack', name: 'Attack', category: 'combat', defaultRate: 65000 },
  { id: 'strength', name: 'Strength', category: 'combat', defaultRate: 65000 },
  { id: 'defence', name: 'Defence', category: 'combat', defaultRate: 65000 },
  { id: 'hitpoints', name: 'Hitpoints', category: 'combat', defaultRate: 50000 },
  { id: 'ranged', name: 'Ranged', category: 'combat', defaultRate: 75000 },
  { id: 'prayer', name: 'Prayer', category: 'combat', defaultRate: 250000 },
  { id: 'magic', name: 'Magic', category: 'combat', defaultRate: 80000 },
  { id: 'cooking', name: 'Cooking', category: 'artisan', defaultRate: 150000 },
  { id: 'woodcutting', name: 'Woodcutting', category: 'gathering', defaultRate: 60000 },
  { id: 'fletching', name: 'Fletching', category: 'artisan', defaultRate: 120000 },
  { id: 'fishing', name: 'Fishing', category: 'gathering', defaultRate: 45000 },
  { id: 'firemaking', name: 'Firemaking', category: 'artisan', defaultRate: 180000 },
  { id: 'crafting', name: 'Crafting', category: 'artisan', defaultRate: 100000 },
  { id: 'smithing', name: 'Smithing', category: 'artisan', defaultRate: 65000 },
  { id: 'mining', name: 'Mining', category: 'gathering', defaultRate: 40000 },
  { id: 'herblore', name: 'Herblore', category: 'artisan', defaultRate: 150000 },
  { id: 'agility', name: 'Agility', category: 'support', defaultRate: 45000 },
  { id: 'thieving', name: 'Thieving', category: 'support', defaultRate: 90000 },
  { id: 'slayer', name: 'Slayer', category: 'support', defaultRate: 25000 },
  { id: 'farming', name: 'Farming', category: 'gathering', defaultRate: 50000 },
  { id: 'runecraft', name: 'Runecraft', category: 'artisan', defaultRate: 35000 },
  { id: 'hunter', name: 'Hunter', category: 'gathering', defaultRate: 70000 },
  { id: 'construction', name: 'Construction', category: 'artisan', defaultRate: 180000 },
  { id: 'sailing', name: 'Sailing', category: 'support', defaultRate: 40000 }
];

export const SKILL_MAP = Object.fromEntries(SKILLS.map(s => [s.id, s]));

// Returns clean SVG icon for skill
export function getSkillIconSvg(skillId, size = 18) {
  const s = skillId.toLowerCase();
  
  // Clean stylized RPG icon SVGs for skills
  switch (s) {
    case 'attack':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14.5 4l5.5 5.5-12 12L2.5 16zM18 7.5L16.5 9M7 14.5L5.5 16"/></svg>`;
    case 'strength':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l4-4 4 4M10 5v14M4 17l4 4 4-4"/></svg>`;
    case 'defence':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/></svg>`;
    case 'hitpoints':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/></svg>`;
    case 'ranged':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><circle cx="12" cy="12" r="6"/><circle cx="12" cy="12" r="2"/></svg>`;
    case 'prayer':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2v20M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/></svg>`;
    case 'magic':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>`;
    case 'mining':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21 3l-8.5 8.5M3 21l8.5-8.5M3.5 3.5a13 13 0 0 1 17 17"/></svg>`;
    case 'smithing':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 10h18l-3 8H6l-3-8zM7 6h10M10 2h4"/></svg>`;
    case 'agility':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M13 2L3 14h9l-1 8 10-12h-9l1-8z"/></svg>`;
    case 'herblore':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M10 2v7.31M14 2v7.31M8.5 2h7M12 10a7 7 0 0 0-7 7v3h14v-3a7 7 0 0 0-7-7z"/></svg>`;
    case 'thieving':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="9" cy="12" r="4"/><circle cx="15" cy="12" r="4"/><path d="M2 12a10 10 0 0 1 20 0"/></svg>`;
    case 'crafting':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/></svg>`;
    case 'fletching':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M21.5 2.5L12 12M21.5 2.5l-7 1.5 2.5 3M21.5 2.5l-1.5 7-3-2.5M3 21l6-6M3 21l3-7M3 21l7-3"/></svg>`;
    case 'slayer':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="11" r="7"/><path d="M12 18v4M9 22h6M9 11h.01M15 11h.01M10 14h4"/></svg>`;
    case 'hunter':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 4h16v16H4zM4 12h16M12 4v16"/></svg>`;
    case 'woodcutting':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 4l6 6-4 4-6-6 4-4zM6 18l4-4M3 21l3-3"/></svg>`;
    case 'fishing':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M18 12.5a6 6 0 0 1-6 6c-3.3 0-6-2.7-6-6s2.7-6 6-6c1.8 0 3.4.8 4.5 2.1L22 4l-4 8.5z"/></svg>`;
    case 'firemaking':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2c1 3 4 5 4 9a6 6 0 0 1-12 0c0-3.5 3.5-7 5-9l3 0z"/></svg>`;
    case 'cooking':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 11h16a1 1 0 0 1 1 1v2a6 6 0 0 1-6 6H9a6 6 0 0 1-6-6v-2a1 1 0 0 1 1-1zM9 4v4M12 2v6M15 4v4"/></svg>`;
    case 'farming':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 22V10M12 10a7 7 0 0 1 7-7c0 3.87-3.13 7-7 7zM12 14a5 5 0 0 0-5-5c0 2.76 2.24 5 5 5z"/></svg>`;
    case 'runecraft':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="9"/><polygon points="12 6 17 15 7 15"/></svg>`;
    case 'construction':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2zM9 22V12h6v10"/></svg>`;
    case 'sailing':
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M2 20a16 16 0 0 0 20 0M4 18l8-14 8 14H4zM12 4v14"/></svg>`;
    default:
      return `<svg width="${size}" height="${size}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>`;
  }
}
