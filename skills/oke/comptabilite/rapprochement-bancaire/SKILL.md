---
name: rapprochement-bancaire
description: Effectue le rapprochement bancaire entre les ecritures OKE et les releves de banque
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [comptabilite, banque, rapprochement, lettrage, oke]
    category: comptabilite
    requires_toolsets: [oke]
    related_skills: [revision-cycle-achats, declarations-tva, cloture-annuelle]
---

# Rapprochement bancaire

## Contexte
Tu travailles avec OKE pour rapprocher les ecritures comptables (compte 512) avec les mouvements du releve bancaire.

## Prerequis
- Releve bancaire importe dans OKE (CSV, OFX, ou CAMT.053)
- Ecritures de tresorerie saisies (comptes 512x)
- Periode de rapprochement identifiee

## Etapes

### 1. Charger le releve bancaire
```
Utilise query_db :
- Table : bank_statements
- Filtre : bank_account_id = <account_id>, period = <YYYY-MM>
- Recupere : date, libelle, montant, reference
```

### 2. Charger les ecritures comptables
```
Utilise query_db :
- Table : accounting_entries
- Filtre : account_number LIKE '512%', period = <YYYY-MM>, company_id = <company_id>
- Recupere : date, libelle, debit, credit, piece, is_reconciled
```

### 3. Rapprochement automatique
```
Utilise exec_code (pandas) :
- Match par montant exact + date proche (± 3 jours)
- Match par reference/piece si disponible
- Match par montant avec tolerance (± 0.01 EUR pour arrondis)
- Marquer les ecritures rapprochees
```

### 4. Traiter les ecarts
```
Pour chaque mouvement non rapproche :
- Releve sans ecriture → ecriture manquante a saisir
- Ecriture sans releve → verifier si cheque/virement en cours
- Ecart de montant → verifier la saisie

Generer la liste des ecritures a creer :
- Frais bancaires (627)
- Interets (661/762)
- Commissions (6278)
```

### 5. Mettre a jour le rapprochement
```
Utilise call_api :
- POST /api/v1/accounting/reconciliation
- Body : { bank_account_id, period, matched_entries: [...], unmatched: [...] }
```

### 6. Etat de rapprochement
```
Utilise exec_code (pandas) :
- Solde comptable (512)
- + ecritures comptables non rapprochees
- - mouvements bancaires non rapproches
- = Solde du releve bancaire
- Verifier : ecart = 0.00 EUR
```

## Resultat attendu
- Nombre de mouvements rapproches automatiquement
- Liste des ecarts a traiter manuellement
- Etat de rapprochement equilibre
- Ecritures de regularisation proposees

## Notes
- Le rapprochement ne modifie pas les ecritures existantes
- Les ecritures proposees doivent etre validees par le comptable
- Frequence recommandee : mensuelle minimum
