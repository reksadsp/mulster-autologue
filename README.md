### Rechargement Automatique du Catalogue Mulster

## Installation
Le script est prévu pour MacOS.
```Bash
chmod +x install.sh && ./install.sh
```
Il est nécesaire au bon fonctionnement du script d'ajouter deux fichiers .env et .ngrok à la racine du projet avec respectivement:

PERPLEXITY_API_KEY=***
NGROK_AUTH_TOKEN=***

## Utilisation:

Ajuster les prompts si besoin.

main.py:
  Préciser si l'on veut réécrire le catalogue complet en spécifiant:
```Python
debug_autologue = True
```
  Si l'on veut ne réécrire que les prix des instruments:
```Python
debug_autologue = False
```
  Ajuster les marges de prix acceptables dans chaque sous-catégories d'expert:
```Python
    def _expert_filter(self, instrument_data: InstrumentData) -> bool:
        if instrument_data.category == "Tables de mixage":
            if float(instrument_data.price) < 100 or float(instrument_data.price) > 10000:
                return False
        if instrument_data.category == "Set de Sonorisation":
            if float(instrument_data.price) < 200 or float(instrument_data.price) > 5000:
                return False
        if instrument_data.category == "Enceintes de Sonorisation":
            if float(instrument_data.price) < 200 or float(instrument_data.price) > 5000:
                return False
        return True
```

expert.py:
  Le script ne peux fonctionner qu'avec le modèle 'sonar-pro' de Perplexity.
  Ajuster la limite de tokens par requête ici:
```Python
            result = self.P_client.chat.completions.create(
                messages=messages,
                max_tokens=300,
                model="sonar-pro",
                tools=self.tools
            )
```

## Notation:
  - Le score de confiance est calculé à partir des prix et des dimensions.
  - Chaque prix qui diffère de 200 à 300% de la moyenne des prix dans la catégorie baisse le score de 0 à 50%.
  - Chaque dimension qui diffère de 20 à 120% de la moyenne de cette même dimensions dans la catégorie baisse le score de 0 à 12.5%. (4 dimensions x 12.5 = 50%)
  - Le score llm2llm concerne les descriptions, les documentations techniques et les spécifications techniques de l'instrument.
  - Il est déterminé par un modèle open-source 'phi' d'Ollama.
  - Le nombre d'éssais augmente à chaque fausse information retournée par Perplexity.
  - Si plus de 5 éssais échouent, l'instrument est écrit tel quel.
  - Les éssais invalidés sont écrits dans le fichier "errors.csv" de chaque catégorie racine.
