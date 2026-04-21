import Card from '../components/ui/Card';
import Button from '../components/ui/Button';
import PageHeader from '../components/ui/PageHeader';

export default function ParametresPage() {
  return (
    <div>
      <PageHeader
        title="Paramètres"
        subtitle="Configuration du système AML"
      />

      <div className="space-y-6 max-w-2xl">
        {/* Seuils d'alerte */}
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-5">Seuils d'alerte</h2>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Seuil de risque (<code className="text-xs bg-slate-100 px-1 rounded">RISK_THRESHOLD</code>)
              </label>
              <input
                type="number"
                step="0.01"
                min="0"
                max="1"
                defaultValue="0.7"
                className="block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
              />
              <p className="text-xs text-slate-400 mt-1">Valeur entre 0 et 1. Une transaction avec un score supérieur déclenche une alerte.</p>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                Email de notification
              </label>
              <input
                type="email"
                defaultValue="compliance@institution.sn"
                className="block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">
                URL Webhook Slack
              </label>
              <input
                type="url"
                placeholder="https://hooks.slack.com/services/..."
                className="block w-full rounded-md border-slate-300 text-sm shadow-sm focus:border-brand-500 focus:ring-brand-500"
              />
            </div>
          </div>
        </Card>

        {/* Informations système */}
        <Card className="p-6">
          <h2 className="text-sm font-semibold text-slate-700 mb-4">Informations système</h2>
          <dl className="space-y-2">
            {[
              { label: 'Version',       value: 'v0.1.0' },
              { label: 'Environnement', value: 'Développement' },
              { label: 'Pipeline',      value: 'Inactif' },
              { label: 'Modèle ML',     value: 'Non déployé' },
            ].map(({ label, value }) => (
              <div key={label} className="flex justify-between py-1.5 border-b border-slate-100 last:border-0">
                <dt className="text-sm text-slate-500">{label}</dt>
                <dd className="text-sm font-medium text-slate-800">{value}</dd>
              </div>
            ))}
          </dl>
        </Card>

        <div className="flex justify-end">
          <Button onClick={() => alert('Non implémenté — disponible en Sprint 2')}>
            Sauvegarder
          </Button>
        </div>
      </div>
    </div>
  );
}
