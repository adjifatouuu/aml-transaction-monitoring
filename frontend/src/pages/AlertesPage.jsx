import { useNavigate } from 'react-router-dom';
import alerts from '../mocks/alerts.json';
import Card from '../components/ui/Card';
import Badge from '../components/ui/Badge';
import Button from '../components/ui/Button';
import PageHeader from '../components/ui/PageHeader';

const STATUS_LABELS = {
  ouverte: { label: 'Ouverte', cls: 'text-blue-600 bg-blue-50' },
  en_cours: { label: 'En cours', cls: 'text-amber-600 bg-amber-50' },
  clôturée: { label: 'Clôturée', cls: 'text-slate-500 bg-slate-100' },
};

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
  });
}

export default function AlertesPage() {
  const navigate = useNavigate();
  const ouvertes = alerts.filter(a => a.status !== 'clôturée').length;

  return (
    <div>
      <PageHeader
        title="Alertes"
        subtitle={`${ouvertes} alerte${ouvertes > 1 ? 's' : ''} active${ouvertes > 1 ? 's' : ''}`}
        actions={<Button variant="secondary">Exporter</Button>}
      />

      {/* Filtres */}
      <Card className="p-4 mb-4">
        <div className="flex items-center gap-4">
          <p className="text-sm font-medium text-slate-600 flex-shrink-0">Filtres :</p>

          <select className="text-sm rounded-md border-slate-300 py-1.5 pr-8">
            <option value="">Tous les statuts</option>
            <option value="ouverte">Ouverte</option>
            <option value="en_cours">En cours</option>
            <option value="clôturée">Clôturée</option>
          </select>

          <select className="text-sm rounded-md border-slate-300 py-1.5 pr-8">
            <option value="">Tous les niveaux</option>
            <option value="critique">Critique</option>
            <option value="élevé">Élevé</option>
            <option value="moyen">Moyen</option>
            <option value="faible">Faible</option>
          </select>

          <select className="text-sm rounded-md border-slate-300 py-1.5 pr-8">
            <option value="7">7 derniers jours</option>
            <option value="30">30 derniers jours</option>
            <option value="90">90 derniers jours</option>
          </select>
        </div>
      </Card>

      {/* Tableau */}
      <Card>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr>
                {['ID Alerte', 'Compte', 'Montant', 'Score', 'Niveau', 'Date', 'Statut'].map(col => (
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
              {alerts.map(alert => {
                const status = STATUS_LABELS[alert.status] ?? { label: alert.status, cls: '' };

                return (
                  <tr
                    key={alert.alert_id}
                    className="hover:bg-slate-50 transition-colors cursor-pointer"
                    onClick={() => navigate(`/investigation/${alert.transaction_id}`)}
                    title="Voir l'investigation"
                  >
                    <td className="px-4 py-3 text-sm font-mono text-slate-700 border-b border-slate-100">
                      {alert.alert_id}
                    </td>

                    <td className="px-4 py-3 text-sm text-slate-700 border-b border-slate-100">
                      {alert.account_id}
                    </td>

                    <td className="px-4 py-3 text-sm text-slate-700 border-b border-slate-100 tabular-nums">
                      {formatAmount(alert.amount)}
                    </td>

                    <td className="px-4 py-3 text-sm font-semibold text-slate-800 border-b border-slate-100 tabular-nums">
                      {alert.score.toFixed(2)}
                    </td>

                    <td className="px-4 py-3 border-b border-slate-100">
                      <Badge level={alert.risk_level} />
                    </td>

                    <td className="px-4 py-3 text-sm text-slate-500 border-b border-slate-100">
                      {formatDate(alert.created_at)}
                    </td>

                    <td className="px-4 py-3 border-b border-slate-100">
                      <span className={`text-xs font-medium px-2 py-1 rounded-full ${status.cls}`}>
                        {status.label}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
