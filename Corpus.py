from __future__ import annotations
from datetime import datetime
from pathlib import Path
import re
from collections import Counter
import pandas as pd
from Author import Author
from Document import Document, HackerNewsDocument, ArxivDocument, DocumentFactory


_RE_BALISES = re.compile(r"<[^>]+>")
_RE_NON_LETTRES = re.compile(r"[^a-zà-ÿ\s]")


def supprimer_balises(texte: str) -> str:
    """Remplace les balises HTML par des espaces (TD6 - 2.1)."""
    if not texte:
        return ""
    return _RE_BALISES.sub(" ", texte)


def nettoyer_texte(texte: str) -> str:
    """Nettoie un texte : balises HTML, minuscules, sauts de ligne, ponctuation et chiffres (TD6 - 2.2)."""
    if not texte:
        return ""
    texte = supprimer_balises(texte)
    texte = texte.lower()
    texte = texte.replace("\n", " ")
    texte = _RE_NON_LETTRES.sub(" ", texte)
    return " ".join(texte.split())


def singleton(cls):
    """Décorateur implémentant le patron de conception Singleton (4.1)."""
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    # Propage les attributs et méthodes statiques vers la fonction décorée
    for attr in dir(cls):
        if not attr.startswith("__"):
            setattr(get_instance, attr, getattr(cls, attr))

    return get_instance


@singleton
class Corpus:
    """Représentation d'un corpus de documents et d'auteurs (Singleton)"""

    supprimer_balises = staticmethod(supprimer_balises)
    nettoyer_texte = staticmethod(nettoyer_texte)

    def __init__(self, nom: str, authors: dict[str, Author] | None = None, id2doc: dict[int, Document] | None = None, ndoc: int = 0, naut: int = 0):
        self.nom = nom
        self.authors: dict[str, Author] = authors if authors is not None else {}
        self.id2doc: dict[int, Document] = id2doc if id2doc is not None else {}
        self.ndoc: int = ndoc if ndoc else len(self.id2doc)
        self.naut: int = naut if naut else len(self.authors)
        self._chaine_complete: str | None = None
        self.vocabulaire: dict[str, int] = {}
        self.freq: pd.DataFrame | None = None

    def _get_chaine_complete(self) -> str:
        """Construit et met en cache la chaîne concaténant l'intégralité des textes du corpus (une seule fois au premier appel)."""
        if self._chaine_complete is None:
            self._chaine_complete = " ".join(doc.texte for doc in self.id2doc.values() if doc.texte)
        return self._chaine_complete

    def add(self, doc: Document, doc_id: int | None = None) -> None:
        """Ajoute un document au corpus et met à jour les dictionnaires id2doc et authors"""
        if doc_id is None:
            doc_id = self.ndoc
            while doc_id in self.id2doc:
                doc_id += 1

        self.id2doc[doc_id] = doc
        self.ndoc = len(self.id2doc)
        self._chaine_complete = None
        self.vocabulaire = {}
        self.freq = None

        author_name = doc.auteur
        if author_name not in self.authors:
            self.authors[author_name] = Author(author_name)
        self.authors[author_name].add(doc, doc_id)
        self.naut = len(self.authors)

    def afficher_par_date(self, n: int | None = None) -> None:
        """Affiche les documents du corpus triés selon la date (du plus récent au plus ancien)"""
        def _sort_key(doc: Document) -> float:
            if isinstance(doc.date, datetime):
                return doc.date.timestamp()
            return 0.0

        docs_tries = sorted(self.id2doc.values(), key=_sort_key, reverse=True)
        if n is not None:
            docs_tries = docs_tries[:n]

        print(f"--- Documents triés par date ({len(docs_tries)} affiché(s)) ---")
        for i, doc in enumerate(docs_tries, 1):
            date_str = doc.date.strftime("%Y-%m-%d") if isinstance(doc.date, datetime) else str(doc.date)
            source_str = f" [{doc.getType()}]" if doc.getType() else ""
            print(f"{i}.{source_str} [{date_str}] {doc} (Auteur : {doc.auteur})")

    def afficher_par_titre(self, n: int | None = None) -> None:
        """Affiche les documents du corpus triés par ordre alphabétique du titre"""
        docs_tries = sorted(self.id2doc.values(), key=lambda d: d.titre.lower())
        if n is not None:
            docs_tries = docs_tries[:n]

        print(f"--- Documents triés par titre ({len(docs_tries)} affiché(s)) ---")
        for i, doc in enumerate(docs_tries, 1):
            date_str = doc.date.strftime("%Y-%m-%d") if isinstance(doc.date, datetime) else str(doc.date)
            source_str = f" [{doc.getType()}]" if doc.getType() else ""
            print(f"{i}.{source_str} {doc} [{date_str}] (Auteur : {doc.auteur})")

    def show(self, n_docs: int = -1, tri: str = "date") -> None:
        """Affiche les éléments du corpus triés selon 'date' ou 'titre'"""
        limit = None if n_docs < 0 else n_docs
        if tri == "titre":
            self.afficher_par_titre(limit)
        else:
            self.afficher_par_date(limit)

    def __repr__(self) -> str:
        return f"Corpus(nom={self.nom!r}, ndoc={self.ndoc}, naut={self.naut})"

    def __str__(self) -> str:
        return f"Corpus '{self.nom}' : {self.ndoc} documents, {self.naut} auteurs"

    def to_dataframe(self) -> pd.DataFrame:
        """Convertit le corpus en DataFrame pandas"""
        lignes = []
        for doc_id, doc in self.id2doc.items():
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

    def save(self, filepath: str | Path = "data/corpus.csv") -> Path:
        """Enregistre le corpus sur le disque dur via une table DataFrame"""
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        df = self.to_dataframe()
        df.to_csv(path, index=False, sep=";", encoding="utf-8")
        return path

    def load(self, filepath: str | Path = "data/corpus.csv") -> None:
        """Charge le corpus depuis un fichier CSV via une table DataFrame"""
        path = Path(filepath)
        if not path.exists():
            raise FileNotFoundError(f"Le fichier de corpus '{path}' n'existe pas.")

        try:
            df = pd.read_csv(path, sep=";", encoding="utf-8")
            if len(df.columns) <= 1:
                df = pd.read_csv(path, sep="\t", encoding="utf-8")
        except Exception:
            df = pd.read_csv(path, sep="\t", encoding="utf-8")

        self.id2doc.clear()
        self.authors.clear()
        self.ndoc = 0
        self.naut = 0
        self._chaine_complete = None
        self.vocabulaire = {}
        self.freq = None

        for idx, row in df.iterrows():
            doc_id = int(row["id"]) if "id" in row and pd.notna(row["id"]) else int(idx)
            titre = str(row["titre"]) if "titre" in row and pd.notna(row["titre"]) else ""
            auteur = str(row["auteur"]) if "auteur" in row and pd.notna(row["auteur"]) else "Inconnu"
            raw_date = str(row["date"]) if "date" in row and pd.notna(row["date"]) else ""
            url = str(row["url"]) if "url" in row and pd.notna(row["url"]) else ""
            texte = str(row["texte"]) if "texte" in row and pd.notna(row["texte"]) else ""
            origine = str(row["origine"]) if "origine" in row and pd.notna(row["origine"]) else ""

            date_obj = self._parse_date(raw_date)
            doc = DocumentFactory.create_document(doc_type=origine, titre=titre, auteur=auteur, date=date_obj, url=url, texte=texte)
            self.add(doc, doc_id=doc_id)

    def search(self, mot_clef: str, taille_contexte: int = 30) -> list[str]:
        """Retourne les passages des documents contenant le mot-clef entré en paramètre (TD6 - 1.1)."""
        if not mot_clef:
            return []
        chaine = self._get_chaine_complete()
        passages: list[str] = []
        for match in re.finditer(mot_clef, chaine, flags=re.IGNORECASE):
            debut = max(0, match.start() - taille_contexte)
            fin = min(len(chaine), match.end() + taille_contexte)
            passages.append(chaine[debut:fin])
        return passages

    def concorde(self, expression: str, taille_contexte: int = 30) -> pd.DataFrame:
        """Construit un concordancier pour une expression donnée et retourne un DataFrame pandas (TD6 - 1.2)."""
        colonnes = ["contexte gauche", "motif trouvé", "contexte droit"]
        if not expression:
            return pd.DataFrame(columns=colonnes)

        chaine = self._get_chaine_complete()
        lignes = []
        for match in re.finditer(expression, chaine, flags=re.IGNORECASE):
            debut_gauche = max(0, match.start() - taille_contexte)
            fin_droit = min(len(chaine), match.end() + taille_contexte)

            gauche = "..." + chaine[debut_gauche:match.start()]
            motif = match.group(0)
            droit = chaine[match.end():fin_droit] + "..."

            lignes.append({
                "contexte gauche": gauche,
                "motif trouvé": motif,
                "contexte droit": droit,
            })

        return pd.DataFrame(lignes, columns=colonnes)

    def construire_vocabulaire(self) -> dict[str, int]:
        """Construit le vocabulaire du corpus dans un dictionnaire via un set (TD6 - 2.3)."""
        ensemble_mots: set[str] = set()
        for doc in self.id2doc.values():
            texte_nettoye = nettoyer_texte(doc.texte)
            mots = texte_nettoye.split()
            ensemble_mots.update(mots)

        self.vocabulaire = {mot: idx for idx, mot in enumerate(sorted(ensemble_mots))}
        return self.vocabulaire

    def construire_tableau_frequence(self) -> pd.DataFrame:
        """Construit le tableau freq (TF et DF) en un seul parcours du corpus (TD6 - 2.4 & 2.5)."""
        if not self.vocabulaire:
            self.construire_vocabulaire()

        tf_counter = Counter()
        df_counter = Counter()

        for doc in self.id2doc.values():
            texte_nettoye = nettoyer_texte(doc.texte)
            mots = texte_nettoye.split()
            tf_counter.update(mots)
            df_counter.update(set(mots))

        mots_vocab = sorted(self.vocabulaire.keys())
        self.freq = pd.DataFrame({
            "term_frequency": [tf_counter[m] for m in mots_vocab],
            "document_frequency": [df_counter[m] for m in mots_vocab],
        }, index=pd.Index(mots_vocab, name="mot"))

        self.freq = self.freq.sort_values(by="term_frequency", ascending=False)
        return self.freq

    def stats(self, n: int = 10) -> pd.DataFrame:
        """Affiche le nombre de mots différents et les n mots les plus fréquents (TD6 - Partie 2)."""
        if self.freq is None:
            self.construire_tableau_frequence()

        nb_mots_differents = len(self.freq)
        print(f"--- Statistiques du corpus '{self.nom}' ---")
        print(f"Nombre de mots différents : {nb_mots_differents}")
        print(f"Les {n} mots les plus fréquents :")
        top_n = self.freq.head(n)
        print(top_n.to_string())
        return top_n

    @staticmethod
    def _parse_date(date_val: str) -> datetime:
        if not date_val:
            return datetime.now()
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
