# Agent catalogue et fiches fournisseurs

## Installation

Prerequis : Python (teste avec Python 3.13), un deploiement de chat Azure OpenAI
et une base MySQL configuree a partir des scripts du dossier [sql](sql/).

Depuis le dossier du projet, creer un environnement virtuel :

```console
python -m venv .venv
```

Activer cet environnement sous Windows (PowerShell) :

```powershell
.\.venv\Scripts\Activate.ps1
```

Sous Linux, macOS ou WSL :

```bash
source .venv/bin/activate
```

Installer les dependances :

```console
python -m pip install -r requirements.txt
```

Selon l'installation de Python, utiliser `python3` ou `py` a la place de `python`
pour creer l'environnement virtuel.

## Configuration

Creer un fichier `.env` a la racine du projet a partir du modele
[.env.example](.env.example), sans ecraser une configuration existante.
Remplacer les valeurs d'exemple par celles de votre ressource Azure et de votre
base MySQL. Le fichier `.env` est charge automatiquement ; les variables deja
definies dans l'environnement restent prioritaires.

Renseigner `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY` et `CHAT_DEPLOYMENT`
pour Azure, puis `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD` et `DB_NAME`
pour MySQL. Utiliser un compte MySQL en lecture seule.
Ne pas versionner `.env` ni partager les cles ou mots de passe qu'il contient.

`CHAT_DEPLOYMENT` est le seul deploiement Azure utilise, via l'API OpenAI v1.
Sa valeur est le nom exact du deploiement, pas necessairement le nom du modele.


`FICHES_REPERTOIRE` accepte un chemin absolu ou relatif au dossier du projet.
Par defaut, tous les PDF de `fiches_fournisseurs`, sous-dossiers inclus, sont lus.
Une page avec du texte correspond a un morceau, conserve en memoire avec le
fichier source et son numero de page. Chaque lancement recharge les PDF
localement, sans appel Azure ni telechargement de modele pour cette etape.
Les PDF numerises sans couche texte necessitent un OCR externe ; les pages vides
sont ignorees. Un PDF illisible ou un repertoire absent provoque une erreur explicite.

## Utilisation

```console
python agent_catalogue.py
```

Pour lancer l'interface web :

```console
streamlit run app.py
```

L'interface conserve l'historique pendant la conversation. Le bouton
« Nouvelle conversation » demarre un nouvel historique ; les outils appeles
par l'agent sont affiches sous chaque reponse.

Exemple : `Quelles sont les conditions de garantie de NovaTech ?`

L'outil `fiches.rechercher_fiches` compte les mots distincts de plus de trois
lettres de la question presents dans chaque page, sans tenir compte de la casse
ni de la ponctuation de la question. Il retourne par defaut les trois pages
les mieux classees avec un score positif (maximum dix), leur chemin relatif
et leur numero de page. Sans correspondance, il signale l'absence de resultat.
Cette recherche est lexicale, pas semantique : les synonymes ne sont pas reconnus.
L'agent recoit les pages par les appels d'outils Semantic Kernel et la consigne
de citer ces sources sous la forme `[Source : fichier.pdf, page N]`.
Les meilleurs passages ne garantissent pas une reponse pertinente : l'agent doit
dire « Je ne trouve pas cette information. » si la reponse manque dans les pages.
L'historique multi-tours existant est conserve. Prix et stocks viennent des
outils MySQL, pas des PDF.

## Tests sans Azure

```console
python -m pytest test_fiches_plugin.py -q
```