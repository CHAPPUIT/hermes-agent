---
name: generation-bulletins-paie
description: Génère les bulletins de paie mensuels pour tous les salariés actifs d'une entreprise OKE
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [paie, bulletins, mensuel, oke]
    related_skills: [dsn-mensuelle, calcul-cotisations, solde-tout-compte]
---

# Génération des bulletins de paie

## Contexte
Tu travailles avec OKE, une plateforme de gestion comptable et de paie. Ce skill te guide pour générer les bulletins de paie mensuels.

## Prérequis
- L'entreprise doit être configurée dans OKE avec des salariés actifs
- Les contrats de travail doivent être renseignés (salaire brut, heures, CCN)
- Les variables du mois doivent être saisies (absences, primes, heures sup)

## Étapes

### 1. Vérifier les salariés actifs
```
Utilise query_db pour lister les salariés actifs :
- Table : payroll_employees
- Filtre : status = 'active', company_id = <company_id>
- Vérifie que chaque salarié a un contrat actif
```

### 2. Vérifier les variables du mois
```
Utilise query_db pour lister les variables :
- Table : payroll_variable_elements
- Filtre : period = <YYYY-MM>, company_id = <company_id>
- Vérifie : absences, primes, heures supplémentaires
```

### 3. Lancer le calcul
```
Utilise call_api :
- POST /api/v1/payroll/payslips/calculate/bulk
- Body : { company_id, period, employee_ids (optionnel) }
- Attend le résultat avec le nombre de bulletins calculés
```

### 4. Vérifier les résultats
```
Pour chaque bulletin calculé :
- Vérifie le brut (cohérent avec le contrat)
- Vérifie les cotisations (taux corrects pour la CCN)
- Vérifie le net (brut - cotisations)
- Compare avec le mois précédent si disponible
```

### 5. Signaler les anomalies
```
Si des écarts sont détectés :
- Brut différent du contrat → vérifier les EVP
- Cotisations inhabituelles → vérifier la CCN
- Net négatif → erreur à corriger
Génère un rapport avec exec_code (pandas)
```

## Résultat attendu
- X bulletins calculés avec succès
- Y erreurs signalées avec détails
- Rapport résumé au format markdown

## Notes
- Les données sont protégées par le trust layer (NIR, noms anonymisés si envoi cloud)
- Les calculs complexes (Fillon, prorata) utilisent le moteur de paie OKE
- En cas de doute, proposer une vérification manuelle avant validation
