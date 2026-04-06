---
name: dsn-mensuelle
description: Genere et verifie la Declaration Sociale Nominative mensuelle dans OKE
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [paie, dsn, declaration, urssaf, oke]
    category: paie
    requires_toolsets: [oke]
    related_skills: [generation-bulletins, calcul-cotisations, solde-tout-compte]
---

# DSN mensuelle

## Contexte
Tu travailles avec OKE pour generer la Declaration Sociale Nominative (DSN) mensuelle. La DSN remplace toutes les declarations sociales (DUCS, DADS, attestations, etc.).

## Prerequis
- Bulletins de paie du mois calcules et valides
- Entreprise configuree : SIRET, code APE, convention collective, IDCC
- Salaries avec NIR (numero de securite sociale) renseigne
- Contrats a jour (date debut, qualification, temps de travail)

## Etapes

### 1. Verifier les bulletins du mois
```
Utilise query_db :
- Table : payroll_payslips
- Filtre : period = <YYYY-MM>, company_id = <company_id>, status = 'validated'
- Verifier : tous les salaries actifs ont un bulletin valide
- Si bulletins manquants → generer d'abord (skill generation-bulletins)
```

### 2. Collecter les evenements DSN
```
Utilise query_db :
- Table : payroll_dsn_events
- Filtre : period = <YYYY-MM>, company_id = <company_id>
- Types d'evenements :
  - S20 : fin de contrat (licenciement, demission, retraite)
  - S21 : autres motifs d'arret (maladie, maternite, AT)
  - S60 : signalements arret de travail
```

### 3. Generer le fichier DSN
```
Utilise call_api :
- POST /api/v1/payroll/dsn/generate
- Body : { company_id, period, type: "mensuelle", events: [...] }
- Le endpoint genere le fichier NEODeS (norme DSN-P24V01)
- Recupere : file_id, bloc_count, anomaly_count
```

### 4. Controles pre-depot
```
Utilise call_api :
- POST /api/v1/payroll/dsn/validate
- Body : { file_id }
- Verifications :
  - Coherence NIR / nom / prenom
  - Montants brut et net coherents avec les bulletins
  - Taux de cotisations conformes au taux DSN
  - Pas de NIR manquant
  - Codes CTP corrects
```

### 5. Signaler les anomalies
```
Pour chaque anomalie :
- Bloquante → doit etre corrigee avant depot
- Non bloquante → a surveiller

Anomalies frequentes :
- NIR provisoire encore utilise
- Ecart brut DSN vs brut bulletin > 1 EUR
- Salarie sorti sans evenement S20
- Taux AT/MP incorrect
```

### 6. Rapport DSN
```
Utilise exec_code (pandas) :
- Resume : nombre de salaries declares, masse salariale
- Cotisations par organisme (URSSAF, retraite, prevoyance)
- Evenements du mois
- Anomalies avec actions correctives
- Date limite de depot (5 ou 15 du mois suivant selon effectif)
```

## Resultat attendu
- Fichier DSN pret au depot (ou liste des corrections)
- Rapport de controle
- Rappel date limite

## Notes
- Les NIR sont des donnees sensibles → trust layer actif
- Date limite : 5 du mois suivant (> 50 salaries) ou 15 du mois suivant (< 50 salaries)
- En cas de premiere DSN, verifier le parameetrage de l'emetteur
- Le depot se fait sur net-entreprises.fr (hors scope agent)
