# Guide des Tests d'Intégration

## Vue d'ensemble

Les tests d'intégration valident l'Identity Service avec de vrais services externes via Docker Compose.

## Utilisation

### Commandes de base

```bash
# Configuration par défaut (images distantes, pas de Guardian)
./run-integration-tests.sh

# Avec Guardian Service
./run-integration-tests.sh --with-guardian

# Build depuis repos locaux
./run-integration-tests.sh --build-local

# Toutes les options
./run-integration-tests.sh --build-local --with-guardian
```

### Options disponibles

| Option | Description |
|--------|-------------|
| `--with-guardian` | Démarre le Guardian Service et exécute ses tests |
| `--build-local` | Build les services depuis repos locaux au lieu d'utiliser les images distantes |
| `--help` | Affiche l'aide |

## Stratégies d'Images

### Problème
Les images GitHub Container Registry (`ghcr.io/...`) sont générées **uniquement depuis la branche `main`**.  
Lors du développement sur une branche, ces images peuvent être obsolètes.

### Solutions

#### 1. Images distantes (défaut)
```bash
./run-integration-tests.sh
```

**Avantages:**
- ✅ Rapide (pas de build)
- ✅ Pas besoin de cloner les autres repos
- ✅ Utilise les versions stables de `main`

**Inconvénients:**
- ⚠️ Ne teste pas les changements dans Storage/Guardian
- ⚠️ Peut être obsolète si `main` n'est pas à jour

**Quand l'utiliser:**
- Tests rapides
- CI/CD
- Vous ne modifiez que l'Identity Service

#### 2. Build local
```bash
./run-integration-tests.sh --build-local
```

**Pré-requis:** Repos clonés dans `../storage_service` et `../guardian_service`

```bash
cd /home/benjamin/projects/waterfall/services/
git clone https://github.com/bengeek06/storage-api-waterfall.git storage_service
git clone https://github.com/bengeek06/guardian-api-waterfall.git guardian_service
cd identity_service
./run-integration-tests.sh --build-local
```

**Avantages:**
- ✅ Teste vos branches en cours
- ✅ Fonctionne avec n'importe quelle branche
- ✅ Parfait pour le développement

**Inconvénients:**
- ⚠️ Build plus lent au premier lancement
- ⚠️ Nécessite les repos clonés

**Quand l'utiliser:**
- Développement multi-services
- Tests de compatibilité entre branches
- Avant de merger des changements qui affectent plusieurs services

#### 3. Stratégie mixte (avancé)

Éditer `.env.integration` pour mixer les approches:

```bash
# Build Storage localement
STORAGE_IMAGE=""
STORAGE_SERVICE_PATH=../storage_service

# Utiliser Guardian distant
GUARDIAN_IMAGE=ghcr.io/bengeek06/guardian-api-waterfall:latest
```

**Quand l'utiliser:**
- Vous modifiez Storage mais pas Guardian
- Optimisation du temps de build

## Guardian Service

Le Guardian Service est **optionnel**. Les tests Guardian se skip automatiquement s'il n'est pas disponible.

```bash
# Sans Guardian → 3 tests skippés
./run-integration-tests.sh
# Résultat: 12 passed, 3 skipped

# Avec Guardian → tous les tests s'exécutent
./run-integration-tests.sh --with-guardian
# Résultat: 15 passed, 0 skipped (si Guardian disponible)
```

## Configuration

### Fichier `.env.integration`

Variables d'environnement pour contrôler le comportement:

```bash
# Images Docker (laisser vide = build local)
STORAGE_IMAGE=ghcr.io/bengeek06/storage-api-waterfall:latest
GUARDIAN_IMAGE=ghcr.io/bengeek06/guardian-api-waterfall:latest

# Chemins des repos (utilisés si STORAGE_IMAGE="" ou GUARDIAN_IMAGE="")
STORAGE_SERVICE_PATH=../storage_service
GUARDIAN_SERVICE_PATH=../guardian_service
```

### Docker Compose

Le fichier `docker-compose.integration.yml` utilise:
- `image:` avec fallback vers images distantes
- `build:` pour build local si les repos existent
- `profiles:` pour rendre Guardian optionnel

```yaml
storage-service:
  image: ${STORAGE_IMAGE:-ghcr.io/bengeek06/storage-api-waterfall:latest}
  build:
    context: ${STORAGE_SERVICE_PATH:-../storage_service}
    dockerfile: Dockerfile

guardian-service:
  image: ${GUARDIAN_IMAGE:-ghcr.io/bengeek06/guardian-api-waterfall:latest}
  build:
    context: ${GUARDIAN_SERVICE_PATH:-../guardian_service}
    dockerfile: Dockerfile
  profiles:
    - guardian  # Démarré seulement avec --profile guardian
```

## Services Démarrés

| Service | Port | Rôle | Obligatoire |
|---------|------|------|-------------|
| MinIO | 9000, 9001 | Object Storage backend | ✅ Oui |
| Storage Service | 5001 | API de stockage de fichiers | ✅ Oui |
| Guardian Service | 5002 | Service d'autorisation | ⏭️ Optionnel |

## Résolution de Problèmes

### Erreur "Image not found"
```
Error: manifest for ghcr.io/.../storage-api-waterfall:latest not found
```

**Solution:** Utiliser le build local
```bash
./run-integration-tests.sh --build-local
```

### Build local échoue
```
Error: context path ../storage_service does not exist
```

**Solution:** Cloner les repos
```bash
cd /home/benjamin/projects/waterfall/services/
git clone https://github.com/bengeek06/storage-api-waterfall.git storage_service
```

### Tests Guardian toujours skippés
```
SKIPPED (Guardian Service non disponible...)
```

**Solution:** Utiliser le flag `--with-guardian`
```bash
./run-integration-tests.sh --with-guardian
```

### Services ne démarrent pas
```
ERROR: Services failed to become healthy within 60 seconds
```

**Debug:**
```bash
# Vérifier les logs
docker compose -f docker-compose.integration.yml logs storage-service

# Vérifier le statut
docker compose -f docker-compose.integration.yml ps

# Redémarrer proprement
docker compose -f docker-compose.integration.yml down -v
./run-integration-tests.sh
```

## Workflow de Développement

### Scénario 1: Modifier uniquement Identity Service
```bash
# 1. Faire vos changements dans identity_service
# 2. Lancer les tests avec images distantes (rapide)
./run-integration-tests.sh

# 3. Les tests valident contre Storage/Guardian stables
```

### Scénario 2: Modifier Identity + Storage
```bash
# 1. Créer une branche dans identity_service ET storage_service
# 2. Faire vos changements dans les deux repos
# 3. Lancer les tests avec build local
./run-integration-tests.sh --build-local

# 4. Les tests valident vos deux branches ensemble
```

### Scénario 3: Tester avec Guardian
```bash
# 1. Faire vos changements
# 2. Lancer avec Guardian
./run-integration-tests.sh --build-local --with-guardian

# 3. Vérifier que les 15 tests passent (pas de skip)
```

## Intégration CI/CD

### GitHub Actions

```yaml
name: Integration Tests

on: [push, pull_request]

jobs:
  integration:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Run Integration Tests (Remote Images)
        run: ./run-integration-tests.sh
        
      # Optionnel: tester avec Guardian
      - name: Run Integration Tests (With Guardian)
        run: ./run-integration-tests.sh --with-guardian
```

### Pour tester les branches
Si vous voulez tester des branches non-mergées dans `main`:

```yaml
- name: Clone Storage Service
  run: |
    cd ..
    git clone https://github.com/bengeek06/storage-api-waterfall.git storage_service
    cd storage_service
    git checkout ${{ github.head_ref }}  # Même branche que la PR
    
- name: Run Integration Tests (Local Build)
  run: ./run-integration-tests.sh --build-local
```

## Architecture des Tests

```
identity_service/
├── docker-compose.integration.yml    # Définition des services
├── .env.integration                  # Configuration par défaut
├── run-integration-tests.sh          # Script de lancement
├── INTEGRATION_TESTS.md              # Ce fichier
└── tests/integration/
    ├── README.md                     # Doc technique
    ├── conftest.py                   # Fixtures pytest
    ├── test_user_avatar_integration.py      # Tests avatar (5 tests)
    ├── test_company_logo_integration.py     # Tests logo (7 tests)
    └── test_guardian_integration.py         # Tests Guardian (3 tests)
```

## Résultats Attendus

### Sans Guardian (défaut)
```
12 passed, 3 skipped in 12.44s
```

### Avec Guardian
```
15 passed in 15.20s
```

## Support

Pour plus de détails techniques, voir:
- `tests/integration/README.md` - Architecture détaillée
- `docker-compose.integration.yml` - Configuration des services
- `.env.integration` - Variables d'environnement
