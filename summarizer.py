"""
summarizer.py
=============
Partie 2 : Résumé intelligent des articles via l'API Google Gemini (gratuit).

Workflow :
  Article brut → build_prompt() → API Gemini → parse_response() → résumé enrichi

Chaque article ressort avec :
  - summary    : résumé en 2-3 phrases, en français
  - keywords   : liste de 3-5 mots-clés financiers
  - sentiment  : "positif" | "négatif" | "neutre"
  - importance : score 1-5 (5 = très important pour les marchés)

Obtenir une clé gratuite : https://aistudio.google.com  (sans CB)
"""

import json
import logging
import os
import re
import time
from typing import Optional

from google import genai

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────
logger = logging.getLogger(__name__)

MODEL        = "gemini-2.0-flash"   # rapide, gratuit, 1500 req/jour
MAX_RETRIES  = 1                    # 1 retry en cas d'erreur transitoire
RETRY_DELAY  = 2                    # secondes entre les tentatives
MAX_TEXT_LEN = 800                  # troncature du texte d'entrée

# Initialisation du client Gemini (lit GEMINI_API_KEY dans l'env)
_api_key = os.environ.get("GEMINI_API_KEY", "")
_client  = genai.Client(api_key=_api_key) if _api_key else None


# ──────────────────────────────────────────────
# 1. Construction du prompt
# ──────────────────────────────────────────────
def build_prompt(article: dict) -> str:
    """
    Construit le prompt envoyé à Gemini pour résumer un article.

    Cas limite : texte trop long → tronqué à MAX_TEXT_LEN caractères
    pour éviter de dépasser la fenêtre de contexte et maîtriser les coûts.
    """
    title  = article.get("title", "Sans titre")
    text   = article.get("summary", "")
    source = article.get("source", "Inconnue")

    # Cas limite : contenu trop long
    if len(text) > MAX_TEXT_LEN:
        text = text[:MAX_TEXT_LEN] + "…"
        logger.debug(f"Texte tronqué à {MAX_TEXT_LEN} chars pour : {title[:40]}")

    prompt = f"""Tu es un analyste financier senior. Résume l'article suivant de façon concise et structurée.

SOURCE : {source}
TITRE  : {title}
TEXTE  : {text}

Réponds UNIQUEMENT avec un objet JSON valide (sans markdown, sans backticks), respectant exactement ce format :
{{
  "summary":    "Résumé en 2-3 phrases maximum, en français, centré sur l'impact marché.",
  "keywords":   ["mot-clé1", "mot-clé2", "mot-clé3"],
  "sentiment":  "positif" | "négatif" | "neutre",
  "importance": 3
}}

Règles :
- summary    : 2-3 phrases max, factuel, sans opinion personnelle
- keywords   : 3 à 5 mots-clés financiers pertinents (entreprise, indice, thème...)
- sentiment  : impact perçu pour les marchés financiers
- importance : entier de 1 (anecdotique) à 5 (événement majeur de marché)
"""
    return prompt


# ──────────────────────────────────────────────
# 2. Appel à l'API Gemini
# ──────────────────────────────────────────────
def call_gemini(prompt: str, retries: int = MAX_RETRIES) -> Optional[str]:
    """
    Envoie le prompt à Gemini et retourne le texte brut de la réponse.

    Cas limites gérés :
    - Clé API absente                  → fallback immédiat (mode sans IA)
    - Clé invalide (401/403)           → message clair + fallback
    - Quota dépassé (429)              → fallback None (résumé brut utilisé)
    - Timeout / erreur réseau          → retry une fois, puis None
    - Erreur générique                 → log + None
    """
    # Cas limite : clé API non configurée
    if not _api_key or _client is None:
        logger.warning("GEMINI_API_KEY absente — passage en mode fallback (résumé brut)")
        return None

    for attempt in range(retries + 1):
        try:
            response = _client.models.generate_content(
                model=MODEL,
                contents=prompt,
            )
            return response.text

        except Exception as e:
            error_str = str(e).lower()

            # Cas limite : clé API invalide
            if "401" in error_str or "403" in error_str or "api_key" in error_str or "invalid" in error_str:
                logger.error("Clé API Gemini invalide — vérifie GEMINI_API_KEY")
                return None

            # Cas limite : quota journalier dépassé
            if "429" in error_str or "quota" in error_str or "resource_exhausted" in error_str:
                logger.warning("Quota Gemini dépassé — passage en mode fallback")
                return None

            # Cas limite : timeout ou erreur réseau → on retente
            if attempt < retries:
                logger.warning(f"Erreur Gemini, nouvelle tentative ({attempt + 1}/{retries}) : {e}")
                time.sleep(RETRY_DELAY)
            else:
                logger.error(f"Erreur Gemini persistante : {e}")
                return None

    return None


# ──────────────────────────────────────────────
# 3. Parsing de la réponse JSON
# ──────────────────────────────────────────────
def parse_response(raw_text: str, article: dict) -> dict:
    """
    Extrait le JSON structuré retourné par Gemini.

    Cas limites gérés :
    - JSON valide directement         → parsing standard
    - JSON entouré de backticks       → nettoyage puis parsing
    - JSON invalide / réponse vide    → fallback avec valeurs par défaut
    - Champs manquants dans le JSON   → complétion avec valeurs par défaut
    """
    fallback = {
        "summary":    article.get("summary", "")[:300],
        "keywords":   [],
        "sentiment":  "neutre",
        "importance": 1,
        "_fallback":  True,
    }

    if not raw_text or not raw_text.strip():
        logger.warning("Réponse API vide — fallback activé")
        return fallback

    # Cas limite : Gemini a parfois ajouté des balises ```json … ```
    cleaned = re.sub(r"```(?:json)?\s*", "", raw_text).replace("```", "").strip()

    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError:
        # Cas limite : JSON malformé → extraction par regex
        match = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if match:
            try:
                data = json.loads(match.group())
            except json.JSONDecodeError:
                logger.warning("JSON introuvable dans la réponse — fallback activé")
                return fallback
        else:
            logger.warning("Pas de JSON dans la réponse — fallback activé")
            return fallback

    # Cas limite : champs manquants → valeurs par défaut
    return {
        "summary":    str(data.get("summary",   fallback["summary"])),
        "keywords":   list(data.get("keywords",  [])),
        "sentiment":  str(data.get("sentiment",  "neutre")),
        "importance": _safe_importance(data.get("importance", 1)),
        "_fallback":  False,
    }


# ──────────────────────────────────────────────
# 4. Résumé d'un seul article
# ──────────────────────────────────────────────
def summarize_article(article: dict) -> dict:
    """
    Pipeline complet pour un article : build_prompt → call_gemini → parse_response.
    Retourne l'article original enrichi avec les champs IA.
    """
    prompt = build_prompt(article)
    raw    = call_gemini(prompt)

    if raw is None:
        ai_fields = {
            "summary":    article.get("summary", "")[:300],
            "keywords":   [],
            "sentiment":  "neutre",
            "importance": 1,
            "_fallback":  True,
        }
    else:
        ai_fields = parse_response(raw, article)

    return {**article, **ai_fields}


# ──────────────────────────────────────────────
# 5. Résumé d'une liste d'articles
# ──────────────────────────────────────────────
def summarize_all(articles: list[dict], delay: float = 0.5) -> list[dict]:
    """
    Résume tous les articles en séquence avec un délai entre chaque appel
    pour respecter le rate limit de l'API Gemini gratuite (15 req/min).

    Args:
        articles : liste issue de collector.collect_news()
        delay    : pause en secondes entre chaque appel API
    """
    results        = []
    total          = len(articles)
    fallback_count = 0

    for i, article in enumerate(articles, 1):
        logger.info(f"Résumé {i}/{total} : {article['title'][:50]}…")

        enriched = summarize_article(article)
        results.append(enriched)

        if enriched.get("_fallback"):
            fallback_count += 1

        if i < total:
            time.sleep(delay)

    logger.info(
        f"Résumés terminés : {total} articles "
        f"({fallback_count} en mode fallback)"
    )
    return results


# ──────────────────────────────────────────────
# Helper interne
# ──────────────────────────────────────────────
def _safe_importance(value) -> int:
    """
    Convertit la valeur d'importance en entier entre 1 et 5.
    Cas limite : valeur hors range ou non numérique → 1
    """
    try:
        v = int(value)
        return max(1, min(5, v))
    except (ValueError, TypeError):
        return 1


# ──────────────────────────────────────────────
# Test rapide (python summarizer.py)
# ──────────────────────────────────────────────
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

    test_article = {
        "title":     "La BCE maintient ses taux directeurs à 4,5%",
        "summary":   (
            "La Banque centrale européenne a décidé lors de sa réunion de jeudi "
            "de maintenir ses taux directeurs inchangés à 4,5%, conformément aux "
            "attentes des marchés. Christine Lagarde a indiqué que la politique "
            "monétaire resterait restrictive aussi longtemps que nécessaire pour "
            "ramener l'inflation vers l'objectif de 2%."
        ),
        "source":    "Reuters Finance",
        "link":      "https://reuters.com/example",
        "published": "2025-05-26",
    }

    print("Test du summarizer Gemini avec un article fictif...\n")
    result = summarize_article(test_article)

    print(f"Titre     : {result['title']}")
    print(f"Résumé IA : {result['summary']}")
    print(f"Mots-clés : {result['keywords']}")
    print(f"Sentiment : {result['sentiment']}")
    print(f"Importance: {result['importance']}/5")
    print(f"Fallback  : {result['_fallback']}")