/**
 * Couche d'accès à l'API de scoring AML.
 * Toutes les fonctions lèvent une Error avec le message API en cas de non-2xx.
 */

const BASE = process.env.REACT_APP_SCORING_API_URL ?? 'http://localhost:8000';

async function _get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Erreur ${res.status} sur ${path}`);
  }
  return res.json();
}

async function _post(path, payload) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `Erreur ${res.status} sur ${path}`);
  }
  return res.json();
}

// ---------------------------------------------------------------------------
// Alertes
// ---------------------------------------------------------------------------

/**
 * @param {{ status?: string, risk_level?: string, days?: number }} filters
 * @returns {Promise<Array>}
 */
export async function fetchAlerts({ status, risk_level, days } = {}) {
  const params = new URLSearchParams();
  if (status)     params.set('status', status);
  if (risk_level) params.set('risk_level', risk_level);
  if (days)       params.set('days', String(days));
  const qs = params.toString();
  return _get(`/alerts${qs ? `?${qs}` : ''}`);
}

// ---------------------------------------------------------------------------
// Transactions
// ---------------------------------------------------------------------------

/**
 * @param {{ limit?: number, offset?: number, account_id?: string }} options
 * @returns {Promise<Array>}
 */
export async function fetchTransactions({ limit = 100, offset = 0, account_id } = {}) {
  const params = new URLSearchParams({ limit, offset });
  if (account_id) params.set('account_id', account_id);
  return _get(`/transactions?${params.toString()}`);
}

/**
 * @param {string} id
 * @returns {Promise<Object>}
 */
export async function fetchTransaction(id) {
  return _get(`/transactions/${encodeURIComponent(id)}`);
}

// ---------------------------------------------------------------------------
// Scoring
// ---------------------------------------------------------------------------

/**
 * @param {Object} payload  — correspond au schéma TransactionIn de l'API
 * @returns {Promise<Object>} ScoreOut
 */
export async function scoreTransaction(payload) {
  return _post('/score', payload);
}
