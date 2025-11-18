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
```

### Tests d'Intégration (avant merge)
```bash
# Avec script automatique (recommandé)
./run-integration-tests.sh

# Ou manuellement
docker-compose -f docker-compose.integration.yml up -d
pytest -m integration -v
docker-compose -f docker-compose.integration.yml down
```

### Tous les tests
```bash
# Unitaires + Intégration
./run-integration-tests.sh && pytest tests/unit/
```

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
