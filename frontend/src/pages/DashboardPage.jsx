import { useState, useEffect } from 'react';
import { fetchAlerts, fetchTransactions } from '../services/api';
import Card from '../components/ui/Card';
import PageHeader from '../components/ui/PageHeader';
import {
  BellAlertIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  FlagIcon,
} from '@heroicons/react/24/outline';

export default function DashboardPage() {
  const [alerts, setAlerts]           = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading]         = useState(true);
  const [error, setError]             = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([fetchAlerts(), fetchTransactions()])
      .then(([a, t]) => { setAlerts(a); setTransactions(t); })
      .catch(err => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  const totalAlerts    = alerts.length;
  const criticalAlerts = alerts.filter(a => a.risk_level === 'critique').length;
  const avgScore       = transactions.length > 0
    ? (transactions.reduce((s, t) => s + t.score, 0) / transactions.length).toFixed(2)
    : '—';
  const flaggedTx      = transactions.filter(t => t.label === 1).length;

  const KPIS = [
    { label: 'Total alertes',          value: loading ? '…' : totalAlerts,    Icon: BellAlertIcon,           color: 'text-brand-500' },
    { label: 'Alertes critiques',      value: loading ? '…' : criticalAlerts, Icon: ExclamationTriangleIcon, color: 'text-red-500' },
    { label: 'Score moyen',            value: loading ? '…' : avgScore,       Icon: ChartBarIcon,            color: 'text-amber-500' },
    { label: 'Transactions suspectes', value: loading ? '…' : flaggedTx,      Icon: FlagIcon,                color: 'text-orange-500' },
  ];

  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Vue d'ensemble — période courante"
      />

      {error && (
        <div className="mb-4 p-4 rounded-lg border border-red-200 bg-red-50">
          <p className="text-sm text-red-600">⚠ Impossible de charger les données : {error}</p>
        </div>
      )}

      {/* KPIs */}
      <div className="grid grid-cols-4 gap-4 mb-6">
        {KPIS.map(({ label, value, Icon, color }) => (
          <Card key={label} className="p-5">
            <div className="flex items-start justify-between">
              <div>
                <p className="text-sm text-slate-500 mb-1">{label}</p>
                <p className="text-3xl font-bold text-slate-900 tabular-nums">{value}</p>
              </div>
              <Icon className={`w-6 h-6 ${color} flex-shrink-0`} />
            </div>
          </Card>
        ))}
      </div>

      {/* Graphiques (placeholders) */}
      <div className="grid grid-cols-2 gap-4">
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">
            Répartition par niveau de risque
          </h2>
          <div className="h-48 bg-slate-50 rounded-lg border-2 border-dashed border-slate-200 flex items-center justify-center">
            <p className="text-sm text-slate-400">Graphique disponible en Sprint 2</p>
          </div>
        </Card>
        <Card className="p-5">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">
            Volume de transactions (7 derniers jours)
          </h2>
          <div className="h-48 bg-slate-50 rounded-lg border-2 border-dashed border-slate-200 flex items-center justify-center">
            <p className="text-sm text-slate-400">Graphique disponible en Sprint 2</p>
          </div>
        </Card>
      </div>
    </div>
  );
}
