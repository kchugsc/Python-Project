from __future__ import annotations
from Document import Document

class Author:

    def __init__(self, name: str, production: dict | None = None):
        self.name = name
        self.production: dict = production if production is not None else {}
        self.ndoc: int = len(self.production)

    def add(self, doc: Document, doc_id: int | str | None = None):
        if doc_id is None:
            doc_id = len(self.production)
        self.production[doc_id] = doc
        self.ndoc = len(self.production)

    def taille_moyenne_documents(self) -> float:
        """Calcule la taille moyenne (en caractères) des documents produits par l'auteur"""
        if self.ndoc == 0:
            return 0.0
        total_chars = sum(len(doc.texte) for doc in self.production.values())
        return total_chars / self.ndoc

    def afficher_statistiques(self) -> None:
        """Affiche le nombre de documents produits et la taille moyenne des documents"""
        moy_chars = self.taille_moyenne_documents()
        moy_mots = (
            sum(len(doc.texte.split()) for doc in self.production.values()) / self.ndoc
            if self.ndoc > 0
            else 0.0
        )
        print(f"Statistiques pour l'auteur '{self.name}' :")
        print(f"  - Nombre de documents produits : {self.ndoc}")
        print(f"  - Taille moyenne des documents : {moy_chars:.2f} caractères ({moy_mots:.2f} mots)")

    def __str__(self) -> str:
        return f"Auteur : {self.name} ({self.ndoc} document(s))"

    def __repr__(self) -> str:
        return f"Author(name={self.name!r}, ndoc={self.ndoc})"

