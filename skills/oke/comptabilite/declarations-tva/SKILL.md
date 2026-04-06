---
name: declarations-tva
description: Prepare et verifie les declarations de TVA mensuelles ou trimestrielles dans OKE
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [comptabilite, tva, fiscal, declaration, oke]
    category: comptabilite
    requires_toolsets: [oke]
    related_skills: [revision-cycle-achats, cloture-annuelle, rapprochement-bancaire]
---

# Declarations de TVA

## Contexte
Tu travailles avec OKE pour preparer les declarations de TVA (CA3 mensuelle ou CA12 annuelle).

## Prerequis
- Ecritures de la periode saisies et validees
- Plan comptable avec comptes de TVA correctement parametres (445x)
- Regime TVA de l'entreprise identifie (reel normal, simplifie, mini-reel)

## Etapes

### 1. Identifier le regime et la periode
```
Utilise query_db :
- Table : companies
- Filtre : company_id = <company_id>
- Recupere : vat_regime, vat_period (monthly/quarterly), last_vat_declaration_date
```

### 2. Extraire les bases de TVA
```
Utilise query_db :
- Table : accounting_entries
- Filtre : period = <YYYY-MM>, account_number LIKE '445%'
- Calcule par taux :
  - TVA collectee (4457x) : base HT + montant TVA
  - TVA deductible sur achats (44566) : base HT + montant TVA
  - TVA deductible sur immobilisations (44562)
  - TVA intra-communautaire (4452)
```

### 3. Calculer la TVA nette
```
TVA nette = TVA collectee - TVA deductible
- Si positif : TVA a payer
- Si negatif : credit de TVA (a reporter ou rembourser)

Verifier :
- Coherence avec le CA declare
- Pas de taux de TVA aberrant
- Prorata de deduction si activite mixte
```

### 4. Comparer avec la periode precedente
```
Utilise query_db :
- Meme requete pour la periode N-1
- Ecart > 20% → signaler avec explication
- Verifier la continuite du credit de TVA si applicable
```

### 5. Generer la declaration
```
Utilise call_api :
- POST /api/v1/fiscal/vat-declarations
- Body : { company_id, period, collected, deductible, net, credit_carried }
- Le endpoint genere le formulaire CA3/CA12
```

### 6. Rapport de controle
```
Utilise exec_code (pandas) :
- Tableau recapitulatif par taux
- Comparatif N / N-1
- Anomalies detectees
- Montant a payer ou credit a reporter
```

## Resultat attendu
- Declaration TVA pre-remplie
- Rapport de controle avec ecarts signales
- Montant TVA nette

## Notes
- Date limite CA3 : entre le 15 et le 24 du mois suivant (selon DGFIP)
- Credit de TVA : proposer le remboursement si > 760 EUR
- Les montants sont arrondis a l'euro le plus proche
