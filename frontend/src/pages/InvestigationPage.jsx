import { useParams } from 'react-router-dom';
import transactions from '../mocks/transactions.json';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import PageHeader from '../components/ui/PageHeader';

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
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  });
}

function KV({ label, value }) {
  return (
    <div className="flex justify-between py-2 border-b border-slate-100 last:border-0">
      <span className="text-sm text-slate-500">{label}</span>
      <span className="text-sm font-medium text-slate-800">{value}</span>
    </div>
  );
}

export default function InvestigationPage() {
  const { id } = useParams();
  const tx = transactions.find(t => t.transaction_id === id) ?? transactions[0];
  const level = scoreToLevel(tx.score);

  return (
    <div>
      <PageHeader
        title="Investigation"
        subtitle={`Transaction ${tx.transaction_id}`}
      />

      <div className="grid grid-cols-3 gap-4">
        {/* Détails */}
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-3">Détails transaction</h2>
          <KV label="Montant" value={formatAmount(tx.amount)} />
          <KV label="Type" value={tx.transaction_type} />
          <KV label="Canal" value={tx.channel} />
          <KV label="Date" value={formatDate(tx.timestamp)} />
        </Card>

        {/* Parties */}
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

        {/* Score */}
        <Card className="p-5 flex flex-col items-center justify-center text-center">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Score de risque</h2>
          <p className="text-5xl font-bold text-slate-900 tabular-nums mb-3">
            {tx.score.toFixed(2)}
          </p>
          <Badge level={level} size="md" />
        </Card>
      </div>

      {/* Historique */}
      <Card className="mt-4 p-6">
        <h2 className="text-sm font-semibold text-slate-700 mb-3">Historique des transactions liées</h2>
        <p className="text-sm text-slate-400 italic">
          Les transactions liées à ce compte seront affichées ici une fois le pipeline de données connecté.
        </p>
      </Card>
    </div>
  );
}
