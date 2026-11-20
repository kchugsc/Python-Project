from datetime import datetime
from pathlib import Path
import pandas as pd
from Author import Author
from Document import Document, HackerNewsDocument, ArxivDocument, DocumentFactory


def singleton(cls):
    """Décorateur implémentant le patron de conception Singleton (4.1)."""
    instances = {}

    def get_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]

    return get_instance


@singleton
class Corpus:
    """Représentation d'un corpus de documents et d'auteurs (Singleton)"""

    def __init__(self,nom: str, authors: dict[str, Author] | None = None, id2doc: dict[int, Document] | None = None, ndoc: int = 0, naut: int = 0):
        self.nom = nom
        self.authors: dict[str, Author] = authors if authors is not None else {}
        self.id2doc: dict[int, Document] = id2doc if id2doc is not None else {}
        self.ndoc: int = ndoc if ndoc else len(self.id2doc)
        self.naut: int = naut if naut else len(self.authors)

    def add(self, doc: Document, doc_id: int | None = None) -> None:
        """Ajoute un document au corpus et met à jour les dictionnaires id2doc et authors"""
        if doc_id is None:
            doc_id = self.ndoc
            while doc_id in self.id2doc:
                doc_id += 1

        self.id2doc[doc_id] = doc
        self.ndoc = len(self.id2doc)

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

        for idx, row in df.iterrows():
            doc_id = int(row["id"]) if "id" in row and pd.notna(row["id"]) else int(idx)
            titre = str(row["titre"]) if "titre" in row and pd.notna(row["titre"]) else ""
            auteur = str(row["auteur"]) if "auteur" in row and pd.notna(row["auteur"]) else "Inconnu"
            raw_date = str(row["date"]) if "date" in row and pd.notna(row["date"]) else ""
            url = str(row["url"]) if "url" in row and pd.notna(row["url"]) else ""
            texte = str(row["texte"]) if "texte" in row and pd.notna(row["texte"]) else ""
            origine = str(row["origine"]) if "origine" in row and pd.notna(row["origine"]) else ""

            date_obj = self._parse_date(raw_date)
            doc = DocumentFactory.create_document( doc_type=origine, titre=titre, auteur=auteur, date=date_obj, url=url, texte=texte)
            self.add(doc, doc_id=doc_id)

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
