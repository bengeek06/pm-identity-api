# Stratégie de Tests - Identity Service

## 📋 Vue d'ensemble

Ce document explique la stratégie de tests adoptée pour Identity Service, notamment concernant l'intégration avec Guardian Service.

## 🎯 Principes

### 1. Tests Unitaires = Logique Métier
- **Objectif** : Valider la logique métier de l'application
- **Scope** : Code de l'application uniquement
- **Dépendances externes** : Mockées (Guardian, Storage, etc.)
- **Vitesse** : Rapides (<10s pour toute la suite)
- **Localisation** : `tests/unit/`

### 2. Tests d'Intégration = Comportement Réel
- **Objectif** : Valider l'intégration avec services externes
- **Scope** : Flux complets avec services réels
- **Dépendances externes** : Services Docker réels
- **Vitesse** : Plus lents (besoin de démarrer services)
- **Localisation** : `tests/integration/`

## 🔄 Décisions de Refactoring (Nov 2025)

### Problème Identifié

L'ancienne approche avait **77 tests dans test_user.py** (2582 lignes) avec :
- ❌ 27 tests complexes testant l'intégration Guardian en mode unitaire
- ❌ Mocks complexes et fragiles (mock.patch imbriqués)
- ❌ Tests qui échouent dès que Guardian change son API
- ❌ Maintenance difficile
- ❌ Coverage médiocre malgré beaucoup de tests (66%)

### Solution Adoptée

**Suppression des tests Guardian unitaires complexes**
- ✅ Supprimé 27 tests d'intégration déguisés en tests unitaires
- ✅ Réduction de 48% du fichier test_user.py (1215 lignes)
- ✅ Temps d'exécution réduit (~2s économisés)

**Création de tests d'intégration dédiés**
- ✅ 3 tests d'intégration Guardian dans `tests/integration/test_guardian_integration.py`
- ✅ Tests skippés automatiquement si Guardian non disponible
- ✅ Documentation claire du comportement attendu

**Tests Guardian conservés**
- ✅ `test_simple_guardian.py` - Test du parsing de réponse Guardian
- ✅ `test_guardian_formats.py` - Tests des différents formats de réponse
- ✅ `test_jwt_forwarding.py` - Tests du forwarding JWT
- ✅ Ces tests valident la logique de l'application, pas Guardian

## 📊 Impact

### Avant Refactoring
```
Tests unitaires : 316 tests (27 skipped)
test_user.py    : 2582 lignes, 77 tests
Temps exécution : ~8s
Coverage        : 66%
Maintenance     : Difficile (mocks complexes)
```

### Après Refactoring
```
Tests unitaires : 289 tests (0 skipped)
test_user.py    : 1367 lignes, 50 tests
Temps exécution : ~6s
Coverage        : 66% (inchangé, mais tests plus pertinents)
Maintenance     : Facile (tests focalisés)
Tests intégration : +3 tests Guardian
```

## 🎓 Bonnes Pratiques

### Quand écrire un test unitaire ?

✅ **OUI** pour :
- Logique de validation (schemas, business rules)
- Transformation de données
- Gestion d'erreurs métier
- Calculs et algorithmes

❌ **NON** pour :
- Appels HTTP à services externes
- Intégration avec BDD (utiliser transactions)
- Workflows multi-services

### Quand écrire un test d'intégration ?

✅ **OUI** pour :
- Validation du flow complet avec Guardian
- Tests avec Storage Service + MinIO réels
- Validation de la sérialisation/désérialisation réelle
- Tests de bout-en-bout critiques

❌ **NON** pour :
- Validation de chaque cas d'erreur possible
- Tests déjà couverts en unitaire

## 📂 Organisation des Tests

```
tests/
├── unit/                           # Tests unitaires (rapides)
│   ├── conftest.py                 # Fixtures avec mocks
│   ├── test_company.py
│   ├── test_user.py                # 50 tests focalisés métier
│   ├── test_simple_guardian.py     # Parsing Guardian (logique)
│   ├── test_guardian_formats.py    # Formats réponse (logique)
│   └── test_jwt_forwarding.py      # JWT forwarding (logique)
│
└── integration/                    # Tests d'intégration (complets)
    ├── conftest.py                 # Fixtures avec services réels
    ├── test_user_avatar_integration.py
    ├── test_company_logo_integration.py
    └── test_guardian_integration.py    # 3 tests Guardian réels
```

## 🚀 Commandes

### Tests Unitaires (usage quotidien)
```bash
# Tous les tests unitaires
pytest tests/unit/

# Avec coverage
pytest tests/unit/ --cov=app --cov-report=term-missing

# Un fichier spécifique
pytest tests/unit/test_user.py -v

# Tous les tests sauf intégration (pour CI/CD)
pytest -m "not integration"
```

### Tests d'Intégration (avant merge)

**Option 1 : Script automatique (recommandé)**
```bash
# Par défaut : avec tous les services (Storage + Guardian)
./scripts/run-integration-tests.sh

# Sans Guardian (tests Guardian seront skipped)
./scripts/run-integration-tests.sh --skip-guardian
```

**Option 2 : Manuellement**
```bash
# Démarrer les services
docker-compose -f docker-compose.test.yml --profile guardian up -d

# Vérifier que les services sont healthy
docker-compose -f docker-compose.test.yml ps

# Lancer les tests d'intégration
pytest -m integration -v

# Arrêter les services
docker-compose -f docker-compose.test.yml --profile guardian down -v
```

### Tous les tests
```bash
# Unitaires + Intégration
./scripts/run-integration-tests.sh && pytest tests/unit/
```

## 🏗️ Infrastructure d'Intégration

### Architecture

```
┌─────────────────┐
│ Identity Service│ (tests)
└────────┬────────┘
         │
         ├──────────────────┐
         │                  │
         ▼                  ▼
┌─────────────────┐  ┌──────────────┐
│ Storage Service │  │   Guardian   │
│   (port 5001)   │  │  (port 5002) │
└────────┬────────┘  └──────────────┘
         │
         ▼
    ┌──────────┐
    │  MinIO   │
    │(port 9000)│
    └──────────┘
```

**Principes:**
- Identity → Storage API (JAMAIS MinIO direct)
- Identity → Guardian API pour l'autorisation
- Storage → MinIO (dépendance interne de Storage)

### Services Démarrés

| Service | Port | Rôle | Obligatoire |
|---------|------|------|-------------|
| MinIO | 9000, 9001 | Object Storage backend | ✅ Oui |
| Storage Service | 5001 | API de stockage de fichiers | ✅ Oui |
| Guardian Service | 5002 | Service d'autorisation | ⏭️ Optionnel |

**Note Guardian:** Le Guardian Service est optionnel. Les tests Guardian sont automatiquement skippés s'il n'est pas disponible.

```bash
# Sans Guardian → 12 tests exécutés, 3 skipped
./scripts/run-integration-tests.sh --skip-guardian

# Avec Guardian → 15 tests exécutés
./scripts/run-integration-tests.sh
```

### Stratégies d'Images Docker

#### Problème
Les images GitHub Container Registry (`ghcr.io/...`) sont générées **uniquement depuis la branche `main`**.  
Lors du développement sur une branche, ces images peuvent être obsolètes.

#### Solutions

**1. Build Local (par défaut)**
```bash
./scripts/run-integration-tests.sh
```

✅ **Avantages:**
- Teste vos branches en cours
- Fonctionne avec n'importe quelle branche
- Parfait pour le développement

⚠️ **Inconvénients:**
- Build plus lent au premier lancement
- Nécessite les repos clonés dans `../storage_service` et `../guardian_service`

**📋 Pré-requis:** Cloner les repos adjacents
```bash
cd /home/benjamin/projects/waterfall/services/
git clone https://github.com/bengeek06/storage-api-waterfall.git storage_service
git clone https://github.com/bengeek06/guardian-api-waterfall.git guardian_service
cd identity_service
./scripts/run-integration-tests.sh
```

**2. Images Distantes (legacy)**
Pour utiliser les images GHCR de `main`, modifier `scripts/integration.conf`:
```bash
STORAGE_IMAGE=ghcr.io/bengeek06/storage-api-waterfall:latest
GUARDIAN_IMAGE=ghcr.io/bengeek06/guardian-api-waterfall:latest
```

✅ **Avantages:**
- Rapide (pas de build)
- Pas besoin de cloner les autres repos
- Utilise les versions stables de `main`

⚠️ **Inconvénients:**
- Ne teste pas les changements dans Storage/Guardian
- Peut être obsolète si `main` n'est pas à jour

**Quand l'utiliser:** Tests rapides, CI/CD, ou quand vous ne modifiez que l'Identity Service.

**3. Stratégie Mixte (avancé)**
Éditer `scripts/integration.conf` pour mixer les approches:
```bash
# Build Storage localement
STORAGE_IMAGE=""
STORAGE_SERVICE_PATH=../storage_service

# Utiliser Guardian distant
GUARDIAN_IMAGE=ghcr.io/bengeek06/guardian-api-waterfall:latest
```

**Quand l'utiliser:** Vous modifiez Storage mais pas Guardian (optimisation du temps de build).

### Configuration Docker Compose

Les services sont configurés dans `docker-compose.test.yml` avec fallback intelligent:

```yaml
storage-service:
  image: ${STORAGE_IMAGE:-}
  build:
    context: ${STORAGE_SERVICE_PATH:-../storage_service}
    dockerfile: Dockerfile

guardian-service:
  image: ${GUARDIAN_IMAGE:-}
  build:
    context: ${GUARDIAN_SERVICE_PATH:-../guardian_service}
    dockerfile: Dockerfile
  profiles:
    - guardian  # Démarré seulement avec --profile guardian
```

**Mécanisme:**
- Si `STORAGE_IMAGE=""` (vide) → build local depuis `STORAGE_SERVICE_PATH`
- Si `STORAGE_IMAGE` défini → utilise l'image distante
- `profiles: guardian` rend Guardian optionnel

**MinIO** (stockage objet)
- API: http://localhost:9000
- Console: http://localhost:9001 (debug uniquement)
- Credentials: minioadmin / minioadmin123

**Storage Service** (API fichiers)
- API: http://localhost:5001
- Healthcheck: `curl -f http://localhost:5000/health`
- DB: SQLite (fichier)

**Guardian Service** (autorisation)
- API: http://localhost:5002
- Healthcheck: Python urllib (curl non disponible)
- DB: SQLite `/tmp/guardian_test.db` (persiste au reloader Flask)
- Profil: `guardian` (optionnel avec `--profile guardian`)

### Variables d'Environnement

Configuration dans `scripts/integration.conf`:
```bash
# Build Strategy: ALWAYS build from local repositories
# This ensures tests run against current branches, not just main
STORAGE_IMAGE=""
GUARDIAN_IMAGE=""

# Service Paths (local repositories)
STORAGE_SERVICE_PATH=../storage_service
GUARDIAN_SERVICE_PATH=../guardian_service
```

**Fichiers de configuration:**
- `scripts/integration.conf` - Configuration active (versionné, valeurs par défaut)
- `scripts/integration.conf.example` - Template de documentation

### Scénarios Testés

**User Avatar Integration** (5 tests)
- ✅ Upload vers Storage Service réel
- ✅ Download depuis Storage Service réel
- ✅ Delete avec vérification Storage
- ✅ Remplacement (versioning)
- ✅ Isolation entre utilisateurs

**Company Logo Integration** (7 tests)
- ✅ Upload vers Storage Service réel
- ✅ Download depuis Storage Service réel
- ✅ Delete avec vérification Storage
- ✅ Remplacement (versioning)
- ✅ Isolation entre companies
- ✅ Validation taille fichier
- ✅ Persistance lors de updates

**Guardian Integration** (3 tests)
- ✅ Autorisation avec Guardian réel
- ✅ Gestion des permissions
- ✅ Workflow complet /init-db

### Debugging

**Voir les logs des services**
```bash
# Logs en temps réel
docker-compose -f docker-compose.test.yml logs -f

# Logs d'un service spécifique
docker-compose -f docker-compose.test.yml logs storage-service
docker-compose -f docker-compose.test.yml logs guardian-service
```

**Vérifier la santé**
```bash
# Status des services
docker-compose -f docker-compose.test.yml --profile guardian ps

# Health checks manuels
curl http://localhost:5001/health  # Storage
curl http://localhost:5002/health  # Guardian
```

**Accéder à MinIO Console** (debug Storage uniquement)  
⚠️ MinIO est une dépendance interne de Storage Service
- URL: http://localhost:9001
- Username: `minioadmin`
- Password: `minioadmin123`

### Troubleshooting

**Services ne démarrent pas**
```bash
# Vérifier les ports disponibles
netstat -tuln | grep -E '(9000|9001|5001|5002)'

# Nettoyer complètement
docker-compose -f docker-compose.test.yml --profile guardian down -v
```

**Tests échouent avec "Service not available"**
```bash
# Vérifier la santé des services
docker-compose -f docker-compose.test.yml ps

# Voir les logs d'erreur
docker-compose -f docker-compose.test.yml logs --tail=50
```

**Guardian DB errors ("no such table")**
- Cause: Flask reloader crée un nouveau process, :memory: DB est perdue
- Solution: Utiliser `/tmp/guardian_test.db` (configuré dans docker-compose.test.yml)
- Le fichier est nettoyé par `scripts/run-integration-tests.sh` à chaque run

## 🔄 Workflows de Développement

### Scénario 1: Modifier uniquement Identity Service
```bash
# 1. Faire vos changements dans identity_service
# 2. Lancer les tests (build local par défaut)
./scripts/run-integration-tests.sh

# 3. Les tests valident contre Storage/Guardian de vos branches locales
```

### Scénario 2: Modifier Identity + Storage
```bash
# 1. Créer une branche dans identity_service ET storage_service
cd ../storage_service && git checkout -b feature/my-feature
cd ../identity_service && git checkout -b feature/my-feature

# 2. Faire vos changements dans les deux repos
# 3. Lancer les tests avec build local
./scripts/run-integration-tests.sh

# 4. Les tests valident vos deux branches ensemble
```

### Scénario 3: Tester avec Guardian
```bash
# 1. Faire vos changements
# 2. Lancer avec Guardian (build local)
./scripts/run-integration-tests.sh

# 3. Vérifier que les 15 tests passent (pas de skip)
# 4. Si tests Guardian skippés, vérifier que Guardian service est démarré
```

### Scénario 4: Tests rapides sans Guardian
```bash
# Skip Guardian pour gagner du temps
./scripts/run-integration-tests.sh --skip-guardian

# Résultat: 12 passed, 3 skipped (tests Guardian)
```

## 🚀 Intégration CI/CD

### GitHub Actions - Tests Unitaires + Intégration

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          pip install -r requirements-dev.txt
      - name: Run unit tests
        run: pytest -m "not integration" --cov=app
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Clone Storage Service
        run: |
          cd ..
          git clone https://github.com/bengeek06/storage-api-waterfall.git storage_service
      
      - name: Clone Guardian Service
        run: |
          cd ..
          git clone https://github.com/bengeek06/guardian-api-waterfall.git guardian_service
      
      - name: Run Integration Tests
        run: ./scripts/run-integration-tests.sh
```

### Tester des branches spécifiques en CI

```yaml
- name: Clone Storage Service (same branch)
  run: |
    cd ..
    git clone https://github.com/bengeek06/storage-api-waterfall.git storage_service
    cd storage_service
    # Checkout la même branche que la PR si elle existe
    git checkout ${{ github.head_ref }} || echo "Branch not found in storage, using main"

- name: Clone Guardian Service (same branch)
  run: |
    cd ..
    git clone https://github.com/bengeek06/guardian-api-waterfall.git guardian_service
    cd guardian_service
    git checkout ${{ github.head_ref }} || echo "Branch not found in guardian, using main"

- name: Run Integration Tests (Local Build)
  run: ./scripts/run-integration-tests.sh
```

## 📊 Résultats Attendus

### Sans Guardian
```bash
$ ./scripts/run-integration-tests.sh --skip-guardian
...
======================== 12 passed, 3 skipped in 12.44s ========================
✅ All integration tests passed!
```

### Avec Guardian (tous les services)
```bash
$ ./scripts/run-integration-tests.sh
...
======================== 15 passed in 15.20s ========================
✅ All integration tests passed!
```

### Erreurs Courantes

**Tests Guardian skippés malgré le flag**
```
SKIPPED [3] Guardian Service not available
```
→ Vérifier que Guardian service est démarré: `docker compose -f docker-compose.test.yml ps`

**Erreur "context path does not exist"**
```
Error: build path ../storage_service does not exist
```
→ Cloner les repos adjacents (voir section "Stratégies d'Images Docker")

## 🎯 Prochaines Améliorations

### Coverage à améliorer (priorités)

1. **storage_helper.py** : 10% → 70%+
   - Tests unitaires des helpers de fichiers
   - Mock de boto3/S3

2. **user_avatar.py** : 17% → 70%+
   - Tests unitaires upload/download/delete
   - Mock Storage Service

3. **user_permissions.py** : 24% → 70%+
   - Tests de la logique d'agrégation
   - Mock Guardian

4. **user_policies.py** : 31% → 70%+
   - Tests de parsing policies
   - Mock Guardian

### Tests à ajouter

- [ ] Tests de concurrence (upload simultanés)
- [ ] Tests de limites (fichiers trop gros)
- [ ] Tests de performance (endpoints lents)
- [ ] Tests de sécurité (injections, XSS)

## 📚 Références

- [pytest Documentation](https://docs.pytest.org/)
- [Flask Testing](https://flask.palletsprojects.com/en/latest/testing/)
- [Testing Best Practices](https://testdriven.io/blog/testing-best-practices/)

## 🤝 Contribution

Lors de l'ajout de nouveaux tests :

1. **Identifier le type** : Unitaire ou Intégration ?
2. **Vérifier la pertinence** : Ce test ajoute-t-il de la valeur ?
3. **Minimiser les mocks** : Tester le plus de code réel possible
4. **Documenter** : Expliquer le "pourquoi" du test
5. **Nommer clairement** : `test_<fonction>_<scenario>_<résultat_attendu>`

Exemple :
```python
def test_upload_avatar_with_valid_image_succeeds(client, user):
    """Test que l'upload d'une image valide réussit et retourne 200."""
    # Clear, focused, valuable
```
