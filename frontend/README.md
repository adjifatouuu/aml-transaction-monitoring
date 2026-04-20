# Frontend — Interface Compliance

Application React + Tailwind CSS pour les analystes compliance.

## Fonctionnalités (Sprint 3)

- Liste des alertes AML
- Détail d'une transaction avec score et features déclenchantes
- Validation / rejet d'une alerte

## Démarrage

Node n'est pas requis en local — le frontend tourne entièrement dans Docker.

```bash
# Depuis la racine du repo
docker-compose up -d frontend
```

L'application est disponible sur http://localhost:3000.

Le dossier `src/` est monté en volume : les modifications de code sont reflétées
en direct sans rebuild de l'image (hot reload).

## Rebuild de l'image (si package.json change)

```bash
docker-compose build frontend
docker-compose up -d frontend
```
