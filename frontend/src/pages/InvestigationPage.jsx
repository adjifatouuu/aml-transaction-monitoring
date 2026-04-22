import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import PageHeader from '../components/ui/PageHeader';
import {
  getTransactionById,
  getRelatedTransactions
} from '../services/investigationService';

function scoreToLevel(score) {
  if (score >= 0.9) return 'critique';
  if (score >= 0.7) return 'élevé';
  if (score >= 0.5) return 'moyen';
  return 'faible';
}

function formatAmount(amount) {
  return new Intl.NumberFormat('fr-FR').format(amount) + ' XOF';
}

function formatDate(iso) {
  return new Date(iso).toLocaleString('fr-FR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function KV({ label, value }) {
  return (
    <div className="flex justify-between py-2 border-b border-slate-100 last:border-0 gap-4">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-800 text-right">{value ?? '-'}</span>
    </div>
  );
}

export default function InvestigationPage() {
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
        </Card>
      </div>
    );
  }

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

  return (
    <div>
      <PageHeader title="Investigation" subtitle={`Transaction suspecte ${tx.transaction_id}`} />

      <div className="grid grid-cols-3 gap-4">
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
        </Card>

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
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr>
                  {['Rang', 'Feature', 'Valeur', 'Impact', 'Interprétation'].map(col => (
                    <th
                      key={col}
                      className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-4 py-3 text-left bg-slate-50 border-b border-slate-200"
                    >
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
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
        )}
      </Card>
    </div>
  );
}
