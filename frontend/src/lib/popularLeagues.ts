// Curated list of "mainstream" OddAlerts competition_ids shown by default in
// the Matches league filter. Click "更多" to reveal the long tail (currently
// 800+ competitions in the DB — most are amateur tiers or U19/women variants
// that visually clutter the chip row).
//
// IDs verified against /api/competitions/:ID at 2026-05-16.
// Add to this set as needed; ordering is not preserved (chips are alpha-sorted
// elsewhere).

export const POPULAR_LEAGUE_IDS = new Set<number>([
  // European top 5
  423,  // Premier League — England
  419,  // La Liga — Spain
  477,  // Bundesliga — Germany
  499,  // Serie A — Italy
  200,  // Ligue 1 — France
  // Other top European
  437,  // Eredivisie — Netherlands
  475,  // Liga Portugal — Portugal
  // UEFA
  51,   // Champions League — Europe
  32,   // Europa League — Europe
  // Cups / second tiers (England)
  418,  // Championship — England
  327,  // FA Cup — England
  268,  // Carabao Cup — England
  // Americas
  68,   // Major League Soccer — USA
  2,    // Liga MX — Mexico
  115,  // Serie A — Brazil (Brasileirão)
  461,  // Copa Libertadores — South America
  696,  // Copa Sudamericana — South America
  // Asia / Oceania
  77,   // J1 League — Japan
  230,  // K League 1 — South Korea
  27,   // Pro League — Saudi Arabia
  456,  // AFC Champions League Elite — Asia
  // Africa
  657,  // CAF Champions League — Africa
])
