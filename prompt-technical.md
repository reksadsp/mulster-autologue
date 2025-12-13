```Markdown
# Information à rechercher :

## Caractéristiques Techniques de l'instrument
    
### Sources de recherche :

	 Priorité 1 : Site constructeur officiel 
	 Priorité 2 : https://fr.audiofanzine.com ou https://www.zikinf.com (pour instruments anciens) 
	 Priorité 3 : https://reverb.com/ (pour instruments vintage) 

## Format d'Entrée :

À la fin de ce prompt, il te sera donné une référence d'instrument sous la forme : ['MARQUE - MODÈLE', 'Type de l'instrument'].

## Format de Sortie :
N'inclus pas d'introductions et de conclusions comme : "Voici la fiche instrument enrichie pour le **Aguilar DB 810 Bass Cabinet**, adaptée au catalogue Mulster, avec une présentation professionnelle et détaillée : ---" ... "--- Souhaitez-vous que je génère également une version courte pour le catalogue en ligne (fiche produit rapide) ?"
Répondre par un unique texte JSON (il sera validé ou rejeté par json.loads(json_str))
Format des données dans le JSON: Clés → Valeurs 
    Exemple : {'Puissance': '500W'}
    Exemple : {'Puissance': '150W', 'Fréquences': '20Hz - 20KHz'}
    Exemple : {'Puissance': '150W', 'Fréquences': '20Hz - 20KHz'}
N'écris pas "clés" ou "key" et "valeurs" ou "value" dans le JSON: 
    Mauvais exemple :{'key': 'Fabrication', 'value': 'Chine'} 
    Bon exemple: {'Fabrication': 'Chine'}
Spécifications à documenter :
    - Réponse en fréquence (Hz),
    - Impédance (Ohms),
    - Connectique,
    ...
Ne surcharge pas les caractéristiques techniques, concentre-toi sur l’essentiel.
Donne toutes les clés en français et les unités dans le système international.
Ne mentionne ni la marque, ni le nom, ni le type d'instrument, ni le prix, ni les dimensions physiques du produit; car ces informations seront traitées par d'autres tâches de recherche.

Voici l'instrument à rechercher :```
