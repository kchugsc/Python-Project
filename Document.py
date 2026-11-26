from __future__ import annotations
from datetime import datetime

class Document:
    def __init__(self, titre: str, auteur: str, date: datetime | str, url: str, texte: str, origine: str = "", doc_type: str = ""):
        self.titre = titre
        self.auteur = auteur
        self.date = date
        self.url = url
        self.texte = texte
        self.origine = origine
        self.type = doc_type or origine

    def getType(self) -> str:
        return self.type

    def afficher(self) -> None:
        """Affiche toutes les informations de l'instance."""
        date_str = self.date.strftime("%Y-%m-%d %H:%M:%S") if isinstance(self.date, datetime) else str(self.date)
        print(f"Titre   : {self.titre}")
        print(f"Auteur  : {self.auteur}")
        print(f"Date    : {date_str}")
        print(f"URL     : {self.url}")
        if self.getType():
            print(f"Type    : {self.getType()}")
        print(f"Texte   : {self.texte}")

    def __str__(self) -> str:
        return self.titre

    def __repr__(self) -> str:
        date_str = self.date.strftime("%Y-%m-%d") if isinstance(self.date, datetime) else str(self.date)
        return f"Document(titre={self.titre!r}, auteur={self.auteur!r}, date={date_str!r}, type={self.getType()!r})"


class HackerNewsDocument(Document):
    def __init__(self, titre: str, auteur: str, date: datetime | str, url: str, texte: str, nb_comments: int = 0, origine: str = "Hacker News"):
        super().__init__(titre=titre, auteur=auteur, date=date, url=url, texte=texte, origine=origine, doc_type="Hacker News")
        self.nb_comments = nb_comments

    def get_nb_comments(self) -> int:
        return self.nb_comments

    def set_nb_comments(self, nb_comments: int) -> None:
        self.nb_comments = nb_comments

    def getType(self) -> str:
        return "Hacker News"

    def __str__(self) -> str:
        return f"{self.titre} ({self.nb_comments} commentaires)"


class ArxivDocument(Document):
    def __init__(self, titre: str, auteur: str, date: datetime | str,
        url: str,
        texte: str,
        co_auteurs: list[str] | None = None,
        origine: str = "Arxiv",
    ):
        super().__init__(titre=titre, auteur=auteur, date=date, url=url, texte=texte, origine=origine, doc_type="Arxiv")
        self.co_auteurs: list[str] = co_auteurs if co_auteurs is not None else []

    def get_co_auteurs(self) -> list[str]:
        return self.co_auteurs

    def set_co_auteurs(self, co_auteurs: list[str]) -> None:
        self.co_auteurs = co_auteurs

    def getType(self) -> str:
        return "Arxiv"

    def __str__(self) -> str:
        if self.co_auteurs:
            co_auteurs_str = ", ".join(self.co_auteurs)
            return f"{self.titre} (Co-auteurs : {co_auteurs_str})"
        return f"{self.titre} (Aucun co-auteur)"


class DocumentFactory:
    """Créer des instances de Document selon leur source."""

    @staticmethod
    def create_document(doc_type: str, titre: str, auteur: str, date: datetime | str, url: str, texte: str, **kwargs ) -> Document:
        norm_type = doc_type.strip().lower()
        if norm_type in ("hackernews", "hacker news", "hn"):
            return HackerNewsDocument(titre=titre, auteur=auteur,date=date, url=url, texte=texte, nb_comments=int(kwargs.get("nb_comments", 0)))
        elif norm_type == "arxiv":
            return ArxivDocument(titre=titre, auteur=auteur, date=date, url=url, texte=texte, co_auteurs=kwargs.get("co_auteurs", []))
        else:
            return Document(titre=titre,auteur=auteur,date=date,url=url,texte=texte,origine=doc_type,doc_type=doc_type)
