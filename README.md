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

Pour initialiser MySQL, fournir la variable SQL de session `@agent_password`
depuis une source secrete externe, puis executer dans **la meme session admin**,
dans cet ordre :
[00_mysql_base_et_utilisateur.sql](sql/00_mysql_base_et_utilisateur.sql),
[01_schema.sql](sql/01_schema.sql) et [02_donnees.sql](sql/02_donnees.sql).
Le premier script ne contient aucun mot de passe et exige cette variable.
Ne pas enregistrer sa valeur dans un fichier versionne ou dans l'historique shell.
Les scripts de schema et de donnees reinitialisent le catalogue : utiliser
uniquement une base dediee. `CREATE USER IF NOT EXISTS` ne change pas le mot
de passe d'un compte deja existant.

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

## Tests sans Azure OpenAI

Tests unitaires seuls, sans MySQL ni identifiants Azure :

```console
python -m pytest -q -m "not integration"
```

La suite couvre les outils du catalogue (recherche, fournisseur, stock, prix,
statistiques), les requetes parametrees, l'echappement LIKE, la fermeture des
connexions, la propagation du refus d'ecriture, le decoupage PDF par page,
le classement RAG et les citations. Les acces base sont simules par
`unittest.mock`. Une fixture interdit les connexions reseau des tests unitaires.
Le test de configuration Azure utilise des valeurs factices sans appel au modele.

Tests d'integration : utiliser **une base MySQL 8.4 de test** initialisee avec
les trois scripts SQL, contenant les 38 produits, et le compte `agent_ia`
limite a `SELECT`. Fournir `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER` et
`DB_PASSWORD` via l'environnement ou le fichier local `.env`, puis :

```console
python -m pytest -q --junitxml=pipelines-test-results/pytest.xml
```

Definir `RUN_MYSQL_TESTS=1` pour inclure les tests d'integration (sinon ignores).
Ils verifient les donnees, les cinq outils, le mode de session lecture seule
et le refus reel des `INSERT`, `UPDATE`, `DELETE` et `CREATE TABLE`, y compris
apres desactivation du garde-fou de session. Aucun test n'appelle Azure OpenAI.

## Azure Pipelines

Creer un pipeline Azure DevOps depuis le depot Azure Repos et selectionner
[azure-pipelines.yml](azure-pipelines.yml). Ce fichier remplace l'ancien
`azure.pipeline.yaml` ; mettre a jour le chemin si un pipeline existait deja.
Les pushes sur `main` declenchent :

La structure du pipeline initial est conservee : stage `Build` / job `BuildCode`,
puis stage `Test` / job `RunTests` dependant du premier. Le cache de dependances
est actif. Le stage `Build` verifie la syntaxe et publie l'artefact `code`,
sans `.env`, environnement virtuel ni journal de conversation. Le stage `Test`
telecharge cet artefact sans nouveau checkout et execute :

1. Installation de Python 3.13, puis des dependances dans `.venv`.
2. Demarrage d'un conteneur MySQL 8.4 isole, sur un port local attribue
   dynamiquement, avec des mots de passe aleatoires generes pour cette execution.
3. Attente bornee de MySQL et execution des trois scripts SQL du projet.
4. Execution de tous les tests avec `RUN_MYSQL_TESTS=1` et generation JUnit.
5. Publication du rapport dans l'onglet **Tests** Azure DevOps, meme si pytest
   echoue. Un test en echec ou un rapport absent fait echouer le pipeline.
6. Suppression du conteneur et de ses volumes anonymes, meme en cas d'echec.

Aucun variable group Azure OpenAI ni secret Azure n'est requis pour ces tests.
Le mot de passe MySQL de test est transmis aux etapes suivantes comme variable
secrete Azure Pipelines. Un agent Microsoft heberge avec Docker et un acces
sortant aux registres de paquets/images est necessaire.

## Versionnement dans Azure Repos depuis VS Code

Le depot local ne devient pas un depot Azure Repos par la seule presence du
pipeline. Creer le depot Git dans Azure DevOps, puis ajouter son URL comme remote
`azure` depuis le terminal VS Code :

```console
git remote add azure https://dev.azure.com/ORGANISATION/PROJET/_git/DEPOT
git remote -v
```

Si le remote `azure` existe deja, verifier son URL plutot que le recreer.

Ne pas inclure de PAT dans l'URL : utiliser Git Credential Manager ou la
connexion Azure DevOps. Dans **Controle de code source**, examiner les diffs,
indexer les fichiers voulus (jamais `.env`) et generer eventuellement le message
avec GitHub Copilot. L'humain effectue ensuite le commit signe (`git commit -S`)
et choisit **Push vers... > azure** depuis VS Code. Aucun commit ni push n'est
execute par l'assistant.

Les fichiers `.env` et `.env.*` sont ignores, sauf le modele `.env.example`.
Verifier aussi les scripts SQL avant chaque commit.

**Attention :** un mot de passe auparavant versionne dans le script SQL doit
etre considere comme compromis. Le supprimer du fichier courant ne le supprime
pas de l'historique Git. Avant publication vers Azure Repos, changer ce mot de
passe partout ou il a ete utilise et faire traiter l'historique par le
responsable du depot si necessaire.