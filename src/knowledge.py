import re
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

import numpy as np
from docx import Document
from PyPDF2 import PdfReader
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "but", "by", "for", "from", "has",
    "he", "i", "in", "is", "it", "its", "of", "on", "or", "that", "the", "their",
    "there", "they", "this", "to", "was", "were", "will", "with", "you", "your",
    "about", "after", "again", "all", "also", "because", "can", "could", "do", "does",
    "did", "each", "few", "into", "just", "make", "more", "most", "not", "now",
    "out", "over", "same", "some", "such", "than", "then", "too", "under", "up",
    "very", "what", "when", "where", "which", "who", "why", "how", "our", "we"
}


class KnowledgeEngine:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(stop_words="english")

    @staticmethod
    def clean_text(text: str) -> str:
        return re.sub(r"\s+", " ", text or "").strip()

    @staticmethod
    def split_sentences(text: str) -> List[str]:
        text = KnowledgeEngine.clean_text(text)
        parts = re.split(r"(?<=[.!?])\s+", text)
        return [part.strip() for part in parts if part.strip()]

    @staticmethod
    def extract_keywords(text: str, top_n: int = 10) -> List[str]:
        text = KnowledgeEngine.clean_text(text).lower()
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", text)
        counts: dict[str, int] = {}
        for word in words:
            if word in STOPWORDS or len(word) <= 2:
                continue
            counts[word] = counts.get(word, 0) + 1

        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        return [word for word, _ in ranked[:top_n]]

    @staticmethod
    def suggest_tags(title: str, content: str, limit: int = 5) -> List[str]:
        combined = f"{title} {content}"
        keywords = KnowledgeEngine.extract_keywords(combined, top_n=limit * 2)
        if not keywords:
            return []
        return keywords[:limit]

    @staticmethod
    def summarize_text(text: str, max_sentences: int = 3) -> str:
        sentences = KnowledgeEngine.split_sentences(text)
        if not sentences:
            return ""
        if len(sentences) <= max_sentences:
            return " ".join(sentences)

        keyword_scores = {}
        for sentence in sentences:
            words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", sentence.lower())
            filtered = [w for w in words if w not in STOPWORDS and len(w) > 2]
            if not filtered:
                continue
            keyword_scores[sentence] = len(set(filtered))

        ranked = sorted(
            sentences,
            key=lambda sentence: (keyword_scores.get(sentence, 0), len(sentence)),
            reverse=True,
        )

        selected = []
        for sentence in ranked:
            if len(selected) >= max_sentences:
                break
            selected.append(sentence)

        selected.sort(key=lambda sentence: sentences.index(sentence))
        return " ".join(selected)

    @staticmethod
    def extract_text_from_file(file_path: str | Path) -> str:
        file_path = Path(file_path)
        extension = file_path.suffix.lower()

        if extension == ".txt":
            return file_path.read_text(encoding="utf-8", errors="ignore")

        if extension == ".pdf":
            reader = PdfReader(str(file_path))
            pages = []
            for page in reader.pages:
                text = page.extract_text() or ""
                pages.append(text)
            return "\n".join(pages)

        if extension == ".docx":
            doc = Document(str(file_path))
            paragraphs = [paragraph.text for paragraph in doc.paragraphs]
            return "\n".join(paragraphs)

        raise ValueError(f"Unsupported file type: {extension}")

    def answer_question(self, question: str, notes: Iterable[dict]) -> dict:
        notes = list(notes)
        if not notes:
            return {
                "answer": "I do not have any notes yet. Add a note or upload a document first.",
                "source_title": "No source",
                "score": 0.0,
            }

        clean_question = KnowledgeEngine.clean_text(question)
        if not clean_question:
            return {
                "answer": "Please enter a question to search the notes.",
                "source_title": "No source",
                "score": 0.0,
            }

        doc_texts = [f"{item.get('title', '')} {item.get('content', '')} {item.get('summary', '')}" for item in notes]
        matrix = self.vectorizer.fit_transform([clean_question] + doc_texts)
        similarities = cosine_similarity(matrix[0:1], matrix[1:])[0]
        best_index = int(np.argmax(similarities))
        best_score = float(similarities[best_index])
        best_note = notes[best_index]

        if best_score <= 0:
            return {
                "answer": "I could not find a strong answer in your notes. Try a different question or add more content.",
                "source_title": best_note.get("title", "Unknown note"),
                "score": best_score,
            }

        source_text = best_note.get("summary") or best_note.get("content") or ""
        answer_text = KnowledgeEngine.summarize_text(source_text, max_sentences=2)
        if not answer_text:
            answer_text = best_note.get("content", "")[:400]

        return {
            "answer": answer_text,
            "source_title": best_note.get("title", "Unknown note"),
            "score": best_score,
        }

    @staticmethod
    def related_notes(notes: List[dict], focus_note_id: Optional[int], limit: int = 5) -> List[dict]:
        if not notes or focus_note_id is None:
            return []

        target = next((note for note in notes if note.get("id") == focus_note_id), None)
        if target is None:
            return []

        focus_text = f"{target.get('title', '')} {target.get('content', '')}"
        items: List[Tuple[float, dict]] = []
        vectorizer = TfidfVectorizer(stop_words="english")
        document_texts = [f"{note.get('title', '')} {note.get('content', '')}" for note in notes]
        if len(document_texts) <= 1:
            return []

        matrix = vectorizer.fit_transform(document_texts)
        focus_vector = vectorizer.transform([focus_text])
        similarities = cosine_similarity(focus_vector, matrix)[0]

        for index, note in enumerate(notes):
            if note.get("id") == focus_note_id:
                continue
            items.append((float(similarities[index]), note))

        items.sort(key=lambda p: p[0], reverse=True)
        return [note for _, note in items[:limit]]
