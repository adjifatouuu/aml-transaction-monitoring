import alerts from '../mocks/alerts.json';
import transactions from '../mocks/transactions.json';
import Card from '../components/ui/Card';
import PageHeader from '../components/ui/PageHeader';
import {
  BellAlertIcon,
  ExclamationTriangleIcon,
  ChartBarIcon,
  FlagIcon,
} from '@heroicons/react/24/outline';

const totalAlerts     = alerts.length;
const criticalAlerts  = alerts.filter(a => a.risk_level === 'critique').length;
const avgScore        = (transactions.reduce((s, t) => s + t.score, 0) / transactions.length).toFixed(2);
const flaggedTx       = transactions.filter(t => t.label === 1).length;

const KPIS = [
  { label: 'Total alertes',       value: totalAlerts,    Icon: BellAlertIcon,          color: 'text-brand-500' },
  { label: 'Alertes critiques',   value: criticalAlerts, Icon: ExclamationTriangleIcon, color: 'text-red-500' },
  { label: 'Score moyen',         value: avgScore,       Icon: ChartBarIcon,            color: 'text-amber-500' },
  { label: 'Transactions suspectes', value: flaggedTx,   Icon: FlagIcon,               color: 'text-orange-500' },
];

export default function DashboardPage() {
  return (
    <div>
      <PageHeader
        title="Dashboard"
        subtitle="Vue d'ensemble — période courante"
      />

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
