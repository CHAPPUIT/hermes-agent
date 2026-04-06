# Cron Jobs OKE pour Hermes Agent

## Installation

Lancer ces commandes apres avoir configure le gateway Hermes :

```bash
# TVA mensuelle — rappel le 15 de chaque mois a 9h
hermes cron create "0 9 15 * *" \
  --prompt "Verifie les declarations TVA en attente pour toutes les entreprises actives. Utilise oke_list_fiscal_declarations avec declaration_type=TVA et status=draft. Signale celles dont la date limite approche (< 5 jours)." \
  --deliver telegram \
  --skill declarations-tva

# Bulletins de paie — le 25 de chaque mois a 8h
hermes cron create "0 8 25 * *" \
  --prompt "Liste les entreprises dont les bulletins de paie du mois en cours n'ont pas ete generes. Utilise oke_payroll_dashboard pour chaque entreprise. Pour celles qui sont pretes (variables saisies, absences integrees), lance le calcul avec oke_calculate_payslips." \
  --deliver telegram \
  --skill generation-bulletins

# Alertes fiscales — chaque lundi a 9h
hermes cron create "0 9 * * 1" \
  --prompt "Scanne les alertes fiscales pour toutes les entreprises actives avec oke_scan_fiscal_alerts. Resume les alertes critiques et les echeances de la semaine." \
  --deliver telegram

# Rapprochement bancaire — le 5 de chaque mois a 10h
hermes cron create "0 10 5 * *" \
  --prompt "Verifie les rapprochements bancaires du mois precedent pour toutes les entreprises. Signale celles qui n'ont pas ete rapprochees ou qui ont un ecart." \
  --deliver telegram \
  --skill rapprochement-bancaire

# DSN mensuelle — le 3 de chaque mois a 8h
hermes cron create "0 8 3 * *" \
  --prompt "Verifie les DSN du mois precedent pour toutes les entreprises. Utilise oke_validate_dsn pour celles qui sont generees mais pas encore soumises. Signale les anomalies bloquantes." \
  --deliver telegram \
  --skill dsn-mensuelle
```

## Gestion

```bash
hermes cron list          # Voir tous les crons
hermes cron pause <id>    # Suspendre un cron
hermes cron resume <id>   # Reprendre
hermes cron run <id>      # Declencher manuellement
hermes cron remove <id>   # Supprimer
```

## Livraison

Les resultats sont livres sur la plateforme configuree (Telegram, Slack, Discord, Email).
Pour les tests, utiliser `--deliver local` (sauvegarde dans ~/.hermes/cron/output/).
