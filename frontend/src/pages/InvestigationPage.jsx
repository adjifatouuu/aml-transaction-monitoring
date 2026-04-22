<<<<<<< HEAD
import { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { fetchTransaction, fetchTransactions } from '../services/api';
=======
import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
>>>>>>> ad8b8c3a46cc3b1517650ac40fb4743603de270d
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import PageHeader from '../components/ui/PageHeader';
import {
  getTransactionById,
  getRelatedTransactions
} from '../services/investigationService';

// ---------------------------------------------------------------------------
// Données contextuelles par type de transaction
// ---------------------------------------------------------------------------

const TYPE_INFO = {
  virement: {
    label:   'Virement bancaire',
    context: 'Transfert interbancaire direct. Vecteur fréquent de blanchiment par fractionnement ou envoi vers des juridictions à risque.',
    cls:     'text-blue-700 bg-blue-50 border-blue-200',
  },
  retrait: {
    label:   'Retrait espèces',
    context: 'Conversion en liquidités — difficile à tracer une fois le cash sorti du circuit bancaire. Signal fort si montant élevé ou récurrent.',
    cls:     'text-orange-700 bg-orange-50 border-orange-200',
  },
  depot: {
    label:   'Dépôt',
    context: 'Entrée de fonds dans le système. À surveiller si les dépôts sont fragmentés (structuration) ou d\'origine inhabituelle.',
    cls:     'text-green-700 bg-green-50 border-green-200',
  },
  mobile_money: {
    label:   'Mobile Money',
    context: 'Transfert via opérateur mobile. Anonymat partiel possible ; surveiller la fréquence et les destinataires transfrontaliers.',
    cls:     'text-purple-700 bg-purple-50 border-purple-200',
  },
  paiement: {
    label:   'Paiement commercial',
    context: 'Règlement d\'une prestation ou d\'un achat. Risque plus faible sauf si le bénéficiaire est une entité écran.',
    cls:     'text-slate-700 bg-slate-50 border-slate-200',
  },
};

const CHANNEL_LABELS = {
  swift:        'SWIFT (interbancaire)',
  cbs:          'Core Banking System',
  mobile_money: 'Mobile Money',
};

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function scoreToLevel(score) {
  if (score >= 0.9) return 'critique';
  if (score >= 0.7) return 'élevé';
  if (score >= 0.5) return 'moyen';
  return 'faible';
}

function scoreBarColor(score) {
  if (score >= 0.9) return 'bg-red-500';
  if (score >= 0.7) return 'bg-orange-400';
  if (score >= 0.5) return 'bg-yellow-400';
  return 'bg-green-400';
}

function formatAmount(amount) {
  return new Intl.NumberFormat('fr-FR').format(amount) + ' XOF';
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('fr-FR', {
<<<<<<< HEAD
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
=======
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
>>>>>>> ad8b8c3a46cc3b1517650ac40fb4743603de270d
  });
}

function KV({ label, value, highlight }) {
  return (
<<<<<<< HEAD
    <div className="flex justify-between items-start py-2 border-b border-slate-100 last:border-0 gap-4">
      <span className="text-sm text-slate-500 flex-shrink-0">{label}</span>
      <span className={`text-sm font-medium text-right ${highlight ? 'text-amber-700' : 'text-slate-800'}`}>
        {value}
      </span>
=======
    <div className="flex justify-between py-2 border-b border-slate-100 last:border-0 gap-4">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-800 text-right">{value ?? '-'}</span>
>>>>>>> ad8b8c3a46cc3b1517650ac40fb4743603de270d
    </div>
  );
}

function ScoreBar({ score }) {
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-slate-100 rounded-full h-1.5">
        <div
          className={`h-1.5 rounded-full transition-all ${scoreBarColor(score)}`}
          style={{ width: `${Math.round(score * 100)}%` }}
        />
      </div>
      <span className="text-xs font-semibold tabular-nums text-slate-700 w-8 text-right">
        {score.toFixed(2)}
      </span>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function InvestigationPage() {
<<<<<<< HEAD
  const { id }       = useParams();
  const navigate     = useNavigate();
  const [tx, setTx]               = useState(null);
  const [history, setHistory]     = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState(null);

  // Charger la transaction principale
  useEffect(() => {
    setLoading(true);
    setError(null);
    const request = id
      ? fetchTransaction(id)
      : fetchTransactions({ limit: 1 }).then(list => list[0] ?? null);

    request
      .then(data => {
        if (!data) throw new Error('Aucune transaction disponible.');
        setTx(data);
      })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, [id]);

  // Charger l'historique du compte une fois la tx principale connue
  useEffect(() => {
    if (!tx) return;
    fetchTransactions({ account_id: tx.account_id, limit: 100 })
      .then(list => setHistory(list.filter(t => t.transaction_id !== tx.transaction_id)))
      .catch(() => {});
  }, [tx]);

  // ---- États de chargement ----
  if (loading) {
    return (
      <div>
        <PageHeader title="Investigation" subtitle="Chargement…" />
        <div className="p-8 text-center text-sm text-slate-400">Chargement…</div>
      </div>
    );
  }

  if (error || !tx) {
    return (
      <div>
        <PageHeader title="Investigation" subtitle="Erreur" />
        <Card className="p-6 border border-red-200 bg-red-50">
          <p className="text-sm text-red-600">⚠ {error ?? 'Transaction introuvable.'}</p>
=======
  const { id } = useParams();

  const [tx, setTx] = useState(null);
  const [relatedTx, setRelatedTx] = useState([]);
  const [loading, setLoading] = useState(true);
  const [errorCode, setErrorCode] = useState(null);

  useEffect(() => {
    let isMounted = true;

    async function load() {
      try {
        setLoading(true);
        setErrorCode(null);

        const transaction = await getTransactionById(id);
        const related = await getRelatedTransactions(
          transaction.account_id,
          transaction.transaction_id
        );

        if (!isMounted) return;
        setTx(transaction);
        setRelatedTx(related);
      } catch (e) {
        if (!isMounted) return;
        setErrorCode(e.message || 'UNKNOWN_ERROR');
      } finally {
        if (isMounted) setLoading(false);
      }
    }

    load();
    return () => {
      isMounted = false;
    };
  }, [id]);

  if (loading) {
    return (
      <div>
        <PageHeader title="Investigation" subtitle="Chargement..." />
        <Card className="p-6">
          <p className="text-sm text-slate-500">Chargement de la transaction…</p>
>>>>>>> ad8b8c3a46cc3b1517650ac40fb4743603de270d
        </Card>
      </div>
    );
  }

<<<<<<< HEAD
  const level    = scoreToLevel(tx.score);
  const typeInfo = TYPE_INFO[tx.transaction_type?.toLowerCase()] ?? {
    label: tx.transaction_type, context: '', cls: 'text-slate-700 bg-slate-50 border-slate-200',
  };
  const isNight  = new Date(tx.timestamp).getHours() >= 22 || new Date(tx.timestamp).getHours() <= 5;

  // Stats historique
  const avgHistScore = history.length > 0
    ? (history.reduce((s, t) => s + t.score, 0) / history.length).toFixed(2)
    : null;
  const highRiskCount = history.filter(t => t.score >= 0.7).length;
  const countries     = [...new Set(history.map(t => t.receiver_country))];
=======
  if (errorCode || !tx) {
    return (
      <div>
        <PageHeader title="Investigation" subtitle="Transaction introuvable" />
        <Card className="p-6">
          <p className="text-sm text-slate-500">
            Aucune transaction ne correspond à l’identifiant demandé.
          </p>
        </Card>
      </div>
    );
  }

  const level = scoreToLevel(tx.score);
>>>>>>> ad8b8c3a46cc3b1517650ac40fb4743603de270d

  return (
    <div>
      <PageHeader title="Investigation" subtitle={`Transaction suspecte ${tx.transaction_id}`} />

      {/* ------------------------------------------------------------------ */}
      {/* Ligne 1 — 3 cartes principales                                       */}
      {/* ------------------------------------------------------------------ */}
      <div className="grid grid-cols-3 gap-4">
<<<<<<< HEAD

        {/* Détails transaction */}
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Détails transaction</h2>
          <KV label="Montant"  value={formatAmount(tx.amount)} />
          <KV
            label="Type"
            value={typeInfo.label}
          />
          <KV
            label="Canal"
            value={CHANNEL_LABELS[tx.channel] ?? tx.channel}
          />
          <KV
            label="Date"
            value={formatDate(tx.timestamp)}
            highlight={isNight}
          />
          {isNight && (
            <p className="mt-2 text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded px-2 py-1">
              ⚠ Transaction effectuée en dehors des heures ouvrables
            </p>
          )}
=======
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Détails transaction</h2>
          <KV label="ID transaction" value={tx.transaction_id} />
          <KV label="Compte" value={tx.account_id} />
          <KV label="Montant" value={formatAmount(tx.amount)} />
          <KV label="Type" value={tx.transaction_type} />
          <KV label="Canal" value={tx.channel} />
          <KV label="Date / Heure" value={formatDate(tx.timestamp)} />
          <KV label="Pays émetteur" value={tx.sender_country} />
          <KV label="Pays récepteur" value={tx.receiver_country} />
>>>>>>> ad8b8c3a46cc3b1517650ac40fb4743603de270d
        </Card>

        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Parties</h2>
          <div className="mb-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Émetteur</p>
            <p className="text-sm font-medium text-slate-800">{tx.account_id}</p>
            <p className="text-xs text-slate-500 mt-0.5">Pays : {tx.sender_country}</p>
          </div>
          <div className="border-t border-slate-100 pt-4">
            <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Récepteur</p>
            <p className="text-sm font-medium text-slate-800">{tx.receiver_id}</p>
            <p className="text-xs text-slate-500 mt-0.5">Pays : {tx.receiver_country}</p>
          </div>
          {tx.sender_country !== tx.receiver_country && (
            <p className="mt-3 text-xs text-orange-600 bg-orange-50 border border-orange-200 rounded px-2 py-1">
              ⚠ Transaction transfrontalière ({tx.sender_country} → {tx.receiver_country})
            </p>
          )}
        </Card>

<<<<<<< HEAD
        {/* Score */}
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Score de risque</h2>
          <div className="flex flex-col items-center justify-center text-center mb-4">
            <p className="text-5xl font-bold text-slate-900 tabular-nums mb-2">
              {tx.score.toFixed(2)}
            </p>
            <Badge level={level} size="md" />
          </div>
          {/* Barre de score */}
          <div className="w-full bg-slate-100 rounded-full h-3 mb-4">
            <div
              className={`h-3 rounded-full ${scoreBarColor(tx.score)}`}
              style={{ width: `${Math.round(tx.score * 100)}%` }}
            />
          </div>
          {/* Indicateurs de risque */}
          <div className="space-y-1 mt-2">
            {tx.score >= 0.7 && (
              <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded px-2 py-1">
                ✗ Score supérieur au seuil d'alerte (0.70)
              </p>
            )}
            {tx.label === 1 && (
              <p className="text-xs text-red-600 bg-red-50 border border-red-100 rounded px-2 py-1">
                ✗ Marquée suspecte dans le dataset
              </p>
            )}
            {tx.score < 0.5 && (
              <p className="text-xs text-green-600 bg-green-50 border border-green-100 rounded px-2 py-1">
                ✓ Score sous le seuil — risque faible
              </p>
            )}
          </div>
        </Card>
      </div>

      {/* ------------------------------------------------------------------ */}
      {/* Contexte du type de transaction                                      */}
      {/* ------------------------------------------------------------------ */}
      <Card className="mt-4 p-5">
        <h2 className="text-sm font-semibold text-slate-700 mb-2">
          Contexte du type — {typeInfo.label}
        </h2>
        <div className={`text-sm rounded-lg border px-4 py-3 ${typeInfo.cls}`}>
          {typeInfo.context}
        </div>
      </Card>

      {/* ------------------------------------------------------------------ */}
      {/* Historique des transactions du compte                                */}
      {/* ------------------------------------------------------------------ */}
      <Card className="mt-4 p-5">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-sm font-semibold text-slate-700">
              Historique du compte émetteur
            </h2>
            <p className="text-xs text-slate-400 mt-0.5">{tx.account_id}</p>
          </div>
          {history.length > 0 && (
            <div className="flex gap-4 text-right">
              <div>
                <p className="text-xs text-slate-400">Transactions</p>
                <p className="text-sm font-semibold text-slate-700">{history.length}</p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Score moyen</p>
                <p className={`text-sm font-semibold ${parseFloat(avgHistScore) >= 0.7 ? 'text-red-600' : 'text-slate-700'}`}>
                  {avgHistScore}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Alertes passées</p>
                <p className={`text-sm font-semibold ${highRiskCount > 0 ? 'text-orange-600' : 'text-green-600'}`}>
                  {highRiskCount}
                </p>
              </div>
              <div>
                <p className="text-xs text-slate-400">Pays destinataires</p>
                <p className="text-sm font-semibold text-slate-700">{countries.length}</p>
              </div>
            </div>
          )}
        </div>

        {history.length === 0 ? (
          <p className="text-sm text-slate-400 italic py-4 text-center">
            Aucune autre transaction connue pour ce compte.
          </p>
        ) : (
=======
        <Card className="p-5 flex flex-col items-center justify-center text-center">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Score de risque</h2>
          <p className="text-5xl font-bold text-slate-900 tabular-nums mb-3">{tx.score.toFixed(2)}</p>
          <Badge level={level} size="md" />
          <p className="text-xs text-slate-500 mt-3">Score ML compris entre 0 et 1</p>
        </Card>
      </div>

      <Card className="mt-4 p-6">
        <h2 className="text-sm font-semibold text-slate-700 mb-3">Explication du score ML</h2>
        <p className="text-sm text-slate-600 leading-6">
          {tx.explanation || 'Aucune explication disponible pour cette transaction.'}
        </p>
      </Card>

      <Card className="mt-4 p-6">
        <h2 className="text-sm font-semibold text-slate-700 mb-4">Top 3 features déclenchantes</h2>
        {tx.top_features?.length ? (
>>>>>>> ad8b8c3a46cc3b1517650ac40fb4743603de270d
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
<<<<<<< HEAD
                  {['Date', 'Montant', 'Type', 'Récepteur', 'Pays dest.', 'Score', 'Niveau'].map(col => (
                    <th
                      key={col}
                      className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-3 py-2 text-left bg-slate-50 border-b border-slate-200"
=======
                  {['Rang', 'Feature', 'Valeur', 'Impact', 'Interprétation'].map(col => (
                    <th
                      key={col}
                      className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3 text-left bg-slate-50 border-b border-slate-200"
>>>>>>> ad8b8c3a46cc3b1517650ac40fb4743603de270d
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
<<<<<<< HEAD
                {[...history]
                  .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
                  .map(t => (
                    <tr
                      key={t.transaction_id}
                      className="hover:bg-slate-50 transition-colors cursor-pointer"
                      onClick={() => navigate(`/investigation/${t.transaction_id}`)}
                    >
                      <td className="px-3 py-2.5 text-xs text-slate-500 border-b border-slate-100">
                        {formatDate(t.timestamp)}
                      </td>
                      <td className="px-3 py-2.5 text-sm font-medium text-slate-800 border-b border-slate-100 tabular-nums">
                        {formatAmount(t.amount)}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-slate-600 border-b border-slate-100">
                        {TYPE_INFO[t.transaction_type?.toLowerCase()]?.label ?? t.transaction_type}
                      </td>
                      <td className="px-3 py-2.5 text-xs font-mono text-slate-600 border-b border-slate-100">
                        {t.receiver_id}
                      </td>
                      <td className="px-3 py-2.5 text-xs text-slate-500 border-b border-slate-100">
                        {t.receiver_country}
                        {t.sender_country !== t.receiver_country && (
                          <span className="ml-1 text-orange-500">↗</span>
                        )}
                      </td>
                      <td className="px-3 py-2.5 border-b border-slate-100 w-36">
                        <ScoreBar score={t.score} />
                      </td>
                      <td className="px-3 py-2.5 border-b border-slate-100">
                        <Badge level={scoreToLevel(t.score)} size="sm" />
                      </td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
=======
                {tx.top_features.slice(0, 3).map((feature, index) => (
                  <tr key={`${feature.name}-${index}`} className="hover:bg-slate-50">
                    <td className="px-4 py-3 text-sm border-b border-slate-100">{index + 1}</td>
                    <td className="px-4 py-3 text-sm font-mono border-b border-slate-100">{feature.name}</td>
                    <td className="px-4 py-3 text-sm border-b border-slate-100">{feature.value}</td>
                    <td className="px-4 py-3 text-sm font-semibold border-b border-slate-100">+{feature.impact}</td>
                    <td className="px-4 py-3 text-sm text-slate-600 border-b border-slate-100">{feature.label}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <p className="text-sm text-slate-400 italic">Aucune feature explicative disponible.</p>
        )}
      </Card>

      <Card className="mt-4 p-6">
        <h2 className="text-sm font-semibold text-slate-700 mb-3">Historique des transactions liées</h2>
        {relatedTx.length ? (
          <ul className="space-y-2">
            {relatedTx.map(t => (
              <li key={t.transaction_id} className="text-sm text-slate-600">
                {t.transaction_id} — {formatAmount(t.amount)} — {formatDate(t.timestamp)}
              </li>
            ))}
          </ul>
        ) : (
          <p className="text-sm text-slate-400 italic">Aucune transaction liée trouvée.</p>
>>>>>>> ad8b8c3a46cc3b1517650ac40fb4743603de270d
        )}
      </Card>
    </div>
  );
}
