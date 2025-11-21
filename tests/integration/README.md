# Integration Tests

Tests d'intégration pour Identity Service avec Storage Service et MinIO réels.

## Quick Start

```bash
# Default: remote images, no Guardian
./run-integration-tests.sh

# With Guardian service
./run-integration-tests.sh --with-guardian

# Build from local repositories (for testing service changes)
./run-integration-tests.sh --build-local

# All options combined
./run-integration-tests.sh --build-local --with-guardian
```

## Image Strategy: Remote vs Local Build

### Problem
- Remote images (`ghcr.io/...`) are only built from `main` branch
- When testing branches, remote images may be outdated

### Solutions

**1. Remote Images (Default)**
```bash
./run-integration-tests.sh
```
✅ Fast, no setup needed  
⚠️ Only tests against `main` branch of Storage/Guardian

**2. Local Build**
```bash
./run-integration-tests.sh --build-local
```
✅ Tests your current branches  
⚠️ Requires repos in `../storage_service`, `../guardian_service`

**3. Mixed (via `.env.integration`)**
```bash
# Build Storage locally, use remote Guardian
STORAGE_IMAGE=""
GUARDIAN_IMAGE=ghcr.io/bengeek06/guardian-api-waterfall:latest
```

See `.env.integration` for configuration options.

## Architecture

```
┌─────────────────┐
│ Identity Service│ (tests)
│   (port 5002)   │
└────────┬────────┘
         │ ONLY via Storage API
         │ (NEVER direct MinIO access)
         ▼
┌─────────────────┐      ┌──────────┐
│ Storage Service │─────▶│  MinIO   │
│   (port 5001)   │      │(port 9000)│
└─────────────────┘      └──────────┘
```

**Important:** Identity Service ne parle **JAMAIS** directement à MinIO.  
Toutes les interactions passent par l'API Storage Service.

## Prérequis

- Docker et Docker Compose
- Python 3.11+
- Package `requests` (déjà dans requirements.txt)

## Démarrage Rapide

### Option 1 : Script automatique (recommandé)

```bash
./run-integration-tests.sh
```

Le script :
- Démarre MinIO et Storage Service
- Attend que les services soient healthy
- Lance les tests d'intégration
- Nettoie automatiquement après les tests

### Option 2 : Manuel

```bash
# 1. Démarrer les services
docker-compose -f docker-compose.integration.yml up -d

# 2. Vérifier que les services sont healthy
docker-compose -f docker-compose.integration.yml ps

# 3. Lancer les tests d'intégration
pytest -m integration -v

# 4. Arrêter les services
docker-compose -f docker-compose.integration.yml down
```

## Tests Unitaires vs Intégration

### Tests Unitaires (rapides, isolés)
```bash
# Tous les tests sauf intégration (pour CI/CD)
pytest -m "not integration"

# Ou simplement
pytest
```

### Tests d'Intégration (complets, nécessitent services externes)
```bash
# Seulement les tests d'intégration
pytest -m integration -v

# Avec coverage
pytest -m integration --cov=app --cov-report=html
```

## Structure des Tests

```
tests/
├── conftest.py                    # Fixtures tests unitaires (USE_STORAGE_SERVICE=false)
├── test_*.py                      # Tests unitaires (mocks)
└── integration/
    ├── __init__.py
    ├── conftest.py                # Fixtures intégration (USE_STORAGE_SERVICE=true)
    ├── test_user_avatar_integration.py     # Tests avatar avec Storage réel
    └── test_company_logo_integration.py    # Tests logo avec Storage réel
```

## Scénarios Testés

### User Avatar Integration
- ✅ Upload vers Storage Service réel
- ✅ Download depuis Storage Service réel
- ✅ Delete avec vérification Storage
- ✅ Remplacement (old file deleted)
- ✅ Isolation entre utilisateurs

### Company Logo Integration  
- ✅ Upload vers Storage Service réel
- ✅ Download depuis Storage Service réel
- ✅ Delete avec vérification Storage
- ✅ Remplacement (old file deleted)
- ✅ Isolation entre companies
- ✅ Validation taille fichier
- ✅ Persistance lors de updates

## Configuration

### Variables d'Environnement

Les tests d'intégration utilisent :

```bash
STORAGE_SERVICE_URL=http://localhost:5001  # Storage API (seul point d'entrée)
```

**Note:** MinIO n'est **jamais** accédé directement. Les variables MINIO_* sont utilisées uniquement par Storage Service.

### Docker Compose

Le fichier `docker-compose.integration.yml` configure :
- **MinIO** : Stockage objet (port 9000 API, 9001 console)
- **Storage Service** : API de gestion fichiers (port 5001)

## Debugging

### Voir les logs des services

```bash
# Logs en temps réel
docker-compose -f docker-compose.integration.yml logs -f

# Logs Storage Service seulement
docker-compose -f docker-compose.integration.yml logs storage-service

# Logs MinIO seulement  
docker-compose -f docker-compose.integration.yml logs minio
```

### Accéder à MinIO Console (pour debugging Storage Service)

⚠️ **MinIO est une dépendance interne de Storage Service.**  
Identity Service ne doit jamais y accéder directement.

Pour debug uniquement, ouvrir http://localhost:9001 :
- Username: `minioadmin`
- Password: `minioadmin123`

### Tester Storage Service manuellement

```bash
# Health check
curl http://localhost:5001/health

# Lister les fichiers (nécessite headers)
curl -H "X-Company-ID: xxx" -H "X-User-ID: yyy" http://localhost:5001/files
```

## Troubleshooting

### Services ne démarrent pas

```bash
# Vérifier les ports disponibles
netstat -tuln | grep -E '(9000|9001|5001)'

# Nettoyer complètement
docker-compose -f docker-compose.integration.yml down -v
docker-compose -f docker-compose.integration.yml up -d
```

### Tests échouent avec "Service not available"

```bash
# Vérifier la santé des services
docker-compose -f docker-compose.integration.yml ps

# Redémarrer si unhealthy
docker-compose -f docker-compose.integration.yml restart
```

### Erreur de connexion MinIO

⚠️ **Identity Service ne doit pas accéder MinIO directement.**

Si Storage Service ne fonctionne pas, vérifier sa santé :
```bash
docker-compose -f docker-compose.integration.yml logs storage-service
curl http://localhost:5001/health
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Run unit tests
        run: pytest -m "not integration"
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Start services
        run: docker-compose -f docker-compose.integration.yml up -d
      - name: Wait for healthy
        run: |
          timeout 60 bash -c 'until docker-compose -f docker-compose.integration.yml ps | grep healthy; do sleep 2; done'
      - name: Run integration tests
        run: pytest -m integration
      - name: Cleanup
        if: always()
        run: docker-compose -f docker-compose.integration.yml down -v
```

## Développement

### Ajouter un nouveau test d'intégration

```python
import pytest

@pytest.mark.integration
def test_my_feature(integration_client, real_company, real_user, integration_token):
    """Test description"""
    integration_client.set_cookie("access_token", integration_token, domain="localhost")
    
    # Your test code
    response = integration_client.post("/endpoint", json={...})
    assert response.status_code == 200
```

### Fixtures disponibles

- `integration_client` : Flask test client configuré pour intégration
- `integration_session` : Session DB
- `real_company` : Company créée en DB
- `real_user` : User créé en DB
- `integration_token` : JWT valide
- `storage_api_client` : Client HTTP pour Storage Service API

## Notes Importantes

- ⚠️ Les tests d'intégration sont **SKIPPED** si services non disponibles
- ✅ Tests unitaires fonctionnent toujours (mode autonome)
- 🔧 Utilisez `-v` pour voir les détails des tests
- 🧹 Les services sont nettoyés automatiquement avec le script
