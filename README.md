# Intervention

Outil intelligent de fuzzing web qui détecte automatiquement les technologies et lance ffuf avec les dictionnaires appropriés.

## Installation

```bash
pip install -r requirements.txt
```

## Prérequis

- `nuclei` installé et dans le PATH
- `ffuf` installé et dans le PATH

## Utilisation

```bash
python intervention.py <url> [options]
```

### Options

- `--dict PATH` : Chemin vers les dictionnaires (défaut: `OneListForAll/dict`)
- `--nuclei-templates PATH` : Chemin vers les templates nuclei (défaut: `nuclei-templates`)
- `--mode {short,long}` : Mode de dictionnaire (défaut: `long`)
- `--occurrence N` : Seuil d'occurrences max (défaut: `10`)
- `-v, --verbose` : Mode verbose

### Exemples

```bash
# Scan simple
python intervention.py https://example.com

# Mode short avec seuil personnalisé
python intervention.py https://example.com --mode short --occurrence 5

# Mode verbose
python intervention.py https://example.com -v

# Plusieurs URLs
python intervention.py https://example.com https://test.com

# Fichier d'URLs
python intervention.py urls.txt
```

## Fonctionnement

1. Détection des technologies avec nuclei (tech-detect, favicon-detect, exposures, exposed-panels)
2. Mapping automatique vers les dictionnaires disponibles
3. Exécution de ffuf avec les dictionnaires appropriés
4. Analyse des résultats par longueur de réponse
5. Filtrage par nombre d'occurrences (résultats rares = intéressants)
6. Sauvegarde des résultats en JSON

## Résultats

Les résultats sont sauvegardés dans `intervention_results_<url>.json` et affichés dans le terminal avec Rich.

