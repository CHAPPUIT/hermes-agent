---
name: revision-cycle-achats
description: Revise le cycle achats/fournisseurs d'une entreprise OKE — rapprochement factures, verification lettrages, anomalies
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [comptabilite, revision, achats, fournisseurs, oke]
    category: comptabilite
    requires_toolsets: [oke]
    related_skills: [rapprochement-bancaire, cloture-annuelle, declarations-tva]
---

# Revision du cycle achats/fournisseurs

## Contexte
Tu travailles avec OKE, une plateforme de gestion comptable. Ce skill te guide pour reviser le cycle achats d'une entreprise.

## Prerequis
- L'entreprise doit etre configuree dans OKE avec un plan comptable
- Les ecritures d'achats doivent etre saisies (comptes 60x, 40x)
- L'exercice cible doit etre identifie

## Etapes

### 1. Lister les comptes fournisseurs
```
Utilise query_db :
- Table : accounting_accounts
- Filtre : account_number LIKE '401%', company_id = <company_id>
- Recupere : numero, libelle, solde
```

### 2. Verifier les lettrages
```
Utilise query_db :
- Table : accounting_entries
- Filtre : account_number LIKE '401%', is_lettered = false
- Identifie les ecritures non lettrees > 30 jours
- Signale les montants significatifs (> 1000 EUR)
```

### 3. Rapprocher avec les factures
```
Utilise call_api :
- GET /api/v1/accounting/invoices?type=purchase&company_id=<company_id>
- Compare chaque facture avec l'ecriture correspondante
- Verifie : montant HT, TVA, TTC, date
```

### 4. Controles de coherence
```
Utilise query_db :
- Solde 401 (fournisseurs) doit etre crediteur
- Total achats (60x) coherent avec CA (70x) et marge sectorielle
- Pas de soldes anormaux (debiteurs sur 401)
- Pas de doublons (meme montant, meme date, meme fournisseur)
```

### 5. Generer le rapport
```
Utilise exec_code (pandas) :
- Tableau des fournisseurs avec soldes
- Liste des ecritures non lettrees
- Anomalies detectees avec gravite (critique/warning/info)
- Recommandations
```

## Resultat attendu
- Nombre d'ecritures revisees
- Nombre d'anomalies par gravite
- Balance fournisseurs verifiee
- Rapport markdown

## Notes
- Les donnees sont protegees par le trust layer
- En cas de doute sur une ecriture, proposer une verification manuelle
- Les seuils de significativite dependent de la taille de l'entreprise
