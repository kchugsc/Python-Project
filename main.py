from datetime import datetime
import html
import json
import logging
from pathlib import Path
import re
import urllib.error
import urllib.parse
import urllib.request
import pandas as pd
import xmltodict
from Author import Author
from Corpus import Corpus
from Document import Document, HackerNewsDocument, ArxivDocument, DocumentFactory

DATA_DIR = Path("data")
CORPUS_FILE = DATA_DIR / "corpus.csv"

HN_API_URL = "https://hn.algolia.com/api/v1/search"
ARXIV_API_URL = "http://export.arxiv.org/api/query"

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


def parse_date(date_val: str | int | float | None) -> datetime:
    """Convertit une chaîne ou un timestamp en objet datetime.

    Gère les chaînes ISO 8601 (ex. '2021-08-09T08:19:54Z') et les timestamps Unix.
    En cas d'échec ou d'absence, retourne la date courante.
    """
    if date_val is None:
        return datetime.now()

    if isinstance(date_val, (int, float)):
        try:
            return datetime.fromtimestamp(date_val)
        except Exception:
            return datetime.now()

    if isinstance(date_val, str):
        clean_str = date_val.strip().replace("Z", "+00:00")
        try:
            return datetime.fromisoformat(clean_str)
        except Exception:
            pass
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%d/%m/%Y"):
            try:
                return datetime.strptime(clean_str, fmt)
            except ValueError:
                continue

    return datetime.now()


def clean_text(raw_text: str) -> str:
    """Nettoie le texte : décode les entités HTML, supprime les balises et normalise les espaces"""
    if not raw_text:
        return ""
    text = html.unescape(raw_text)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def fetch_hacker_news_documents(query: str = "climate", hits_per_page: int = 50,) -> list[Document]:
    """Récupère des articles depuis Hacker News et les instancie en objets HackerNewsDocument"""
    params = urllib.parse.urlencode({
        "query": query,
        "tags": "story",
        "hitsPerPage": hits_per_page,
    })
    url = f"{HN_API_URL}?{params}"
    logger.info("Interrogation de l'API Hacker News : %s", url)

    try:
        with urllib.request.urlopen(url) as response:
            data = json.load(response)
    except urllib.error.URLError as e:
        logger.error("Erreur lors de la requête Hacker News : %s", e)
        return []

    hits = data.get("hits", [])
    logger.info("Hacker News : %d documents récupérés.", len(hits))

    documents: list[Document] = []
    for hit in hits:
        titre = clean_text(hit.get("title") or "")
        auteur = (hit.get("author") or "Inconnu").strip()
        date_obj = parse_date(hit.get("created_at") or hit.get("created_at_i"))

        item_url = hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID', '')}"

        texte_brut = hit.get("story_text") or hit.get("title") or ""
        texte = clean_text(texte_brut)
        nb_comments = int(hit.get("num_comments") or 0)

        doc = DocumentFactory.create_document(
            doc_type="Hacker News",
            titre=titre,
            auteur=auteur,
            date=date_obj,
            url=item_url,
            texte=texte,
            nb_comments=nb_comments,
        )
        documents.append(doc)

    return documents


def fetch_arxiv_documents(search_query: str = "all:climate",start: int = 0,max_results: int = 5,) -> list[Document]:
    """Récupère des articles depuis arXiv et les instancie en objets ArxivDocument"""
    params = urllib.parse.urlencode({
        "search_query": search_query,
        "start": start,
        "max_results": max_results,
    })
    url = f"{ARXIV_API_URL}?{params}"
    logger.info("Interrogation de l'API arXiv : %s", url)

    try:
        with urllib.request.urlopen(url) as response:
            raw_data = response.read()
            data = xmltodict.parse(raw_data)
    except (urllib.error.URLError, Exception) as e:
        logger.error("Erreur lors de la requête arXiv : %s", e)
        return []

    entries = data.get("feed", {}).get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]

    logger.info("arXiv : %d documents récupérés.", len(entries))

    documents: list[Document] = []
    for entry in entries:
        titre = clean_text(entry.get("title") or "")

        raw_authors = entry.get("author", [])
        co_auteurs: list[str] = []
        if isinstance(raw_authors, list):
            auteurs_list = [a.get("name", "") for a in raw_authors if isinstance(a, dict) and a.get("name")]
            auteur = auteurs_list[0] if auteurs_list else "Inconnu"
            co_auteurs = auteurs_list[1:] if len(auteurs_list) > 1 else []
        elif isinstance(raw_authors, dict):
            auteur = raw_authors.get("name", "Inconnu")
        elif isinstance(raw_authors, str):
            auteur = raw_authors
        else:
            auteur = "Inconnu"

        date_obj = parse_date(entry.get("published") or entry.get("updated"))
        item_url = entry.get("id") or ""
        texte = clean_text(entry.get("summary") or "")

        doc = DocumentFactory.create_document(
            doc_type="Arxiv",
            titre=titre,
            auteur=auteur,
            date=date_obj,
            url=item_url,
            texte=texte,
            co_auteurs=co_auteurs,
        )
        documents.append(doc)

    return documents


def build_id2doc(documents: list[Document]) -> dict[int, Document]:
    """Indexe une liste de documents dans un dictionnaire `id2doc`, chaque document est associé à un identifiant entier unique généré au fur et à mesure
    """
    id2doc: dict[int, Document] = {}
    for doc in documents:
        doc_id = len(id2doc)
        id2doc[doc_id] = doc
    return id2doc


def build_authors(id2doc: dict[int, Document]) -> dict[str, Author]:
    """Construit le dictionnaire `id2aut` des auteurs à partir des documents indexés"""
    id2aut: dict[str, Author] = {}
    for doc_id, doc in id2doc.items():
        author_name = doc.auteur
        if author_name not in id2aut:
            id2aut[author_name] = Author(author_name)
        id2aut[author_name].add(doc, doc_id)
    return id2aut


def afficher_stats_auteur(id2aut: dict[str, Author], nom_auteur: str) -> None:
    """Affiche le nombre de documents produits et la taille moyenne des documents d'un auteur"""
    auteur = id2aut.get(nom_auteur)
    if auteur is None:
        correspondances = [
            a for nom, a in id2aut.items() if nom_auteur.lower() in nom.lower()
        ]
        if len(correspondances) == 1:
            auteur = correspondances[0]
        elif len(correspondances) > 1:
            noms = ", ".join(a.name for a in correspondances)
            print(f"Plusieurs auteurs correspondent à '{nom_auteur}' : {noms}")
            auteur = correspondances[0]
        else:
            print(f"L'auteur '{nom_auteur}' est introuvable dans le corpus.")
            return

    auteur.afficher_statistiques()


def id2doc_to_dataframe(id2doc: dict[int, Document]) -> pd.DataFrame:
    """Convertit le dictionnaire id2doc en DataFrame pandas"""
    lignes = []
    for doc_id, doc in id2doc.items():
        date_iso = doc.date.isoformat() if isinstance(doc.date, datetime) else str(doc.date)
        lignes.append({
            "id": doc_id,
            "titre": doc.titre,
            "auteur": doc.auteur,
            "date": date_iso,
            "url": doc.url,
            "texte": doc.texte,
            "origine": doc.origine,
        })
    return pd.DataFrame(lignes)


def save_corpus(df: pd.DataFrame, filepath: Path | str = CORPUS_FILE) -> Path:
    """Sauvegarde le DataFrame au format CSV"""
    path = Path(filepath)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, sep=";", encoding="utf-8")
    logger.info("Corpus sauvegardé dans %s (%d lignes)", path, len(df))
    return path


def load_corpus(filepath: Path | str = CORPUS_FILE) -> pd.DataFrame:
    """Charge un corpus sauvegardé depuis un fichier CSV"""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Le fichier de corpus '{path}' n'existe pas.")
    try:
        df = pd.read_csv(path, sep=";", encoding="utf-8")
        if len(df.columns) <= 1:
            df = pd.read_csv(path, sep="\t", encoding="utf-8")
    except Exception:
        df = pd.read_csv(path, sep="\t", encoding="utf-8")
    logger.info("Corpus chargé depuis %s (%d lignes)", path, len(df))
    return df


def is_csv_populated(filepath: Path | str = CORPUS_FILE) -> bool:
    """Vérifie si le fichier CSV existe et contient au moins une ligne de données"""
    path = Path(filepath)
    if not path.exists() or path.stat().st_size == 0:
        return False
    try:
        df = load_corpus(path)
        return not df.empty
    except Exception:
        return False


def main() -> None:
    corpus = Corpus(nom="Corpus Climat")
    if is_csv_populated(CORPUS_FILE):
        logger.info("Fichier CSV existant et rempli détecté (%s)", CORPUS_FILE)
        corpus.load(CORPUS_FILE)
        corpus.save(CORPUS_FILE)
        id2doc = corpus.id2doc
        id2aut = corpus.authors
        print(f"Corpus chargé depuis '{CORPUS_FILE}' : {corpus.ndoc} documents, {corpus.naut} auteurs.")
    else:
        logger.info("Fichier CSV absent ou vide. Récupération des documents via les API...")
        hn_docs = fetch_hacker_news_documents(query="climate", hits_per_page=50)
        arxiv_docs = fetch_arxiv_documents(search_query="all:climate", start=0, max_results=5)

        all_docs = hn_docs + arxiv_docs
        print(f"Total instances Document créées via API : {len(all_docs)}")
        print(f"  - Hacker News : {len(hn_docs)}")
        print(f"  - arXiv       : {len(arxiv_docs)}")

        for doc in all_docs:
            corpus.add(doc)

        id2doc = corpus.id2doc
        id2aut = corpus.authors
        corpus.save(CORPUS_FILE)
        print(f"Corpus sauvegardé dans '{CORPUS_FILE}' (séparateur ';').")

    if id2doc:
        premier_id = next(iter(id2doc))
        premier_doc = id2doc[premier_id]
        print(f"Affichage digeste via print(doc) (__str__) : {premier_doc}")
        print("\nAffichage complet via doc.afficher() :")
        premier_doc.afficher()

    print(f"Nombre d'auteurs dans id2aut : {len(id2aut)}")
    if id2aut:
        auteur_exemple = max(id2aut.values(), key=lambda a: a.ndoc)
        print(f"Exemple d'auteur (__str__) : {auteur_exemple}")
        afficher_stats_auteur(id2aut, auteur_exemple.name)
        try:
            choix_auteur = input("\nEntrez le nom d'un auteur pour voir ses statistiques (ou Entrée pour passer) : ").strip()
            if choix_auteur:
                afficher_stats_auteur(id2aut, choix_auteur)
        except EOFError:
            pass

    print(f"Représentation du corpus (__repr__) : {corpus!r}")
    print()
    corpus.afficher_par_date(n=5)
    print()
    corpus.afficher_par_titre(n=5)


if __name__ == "__main__":
    main()

