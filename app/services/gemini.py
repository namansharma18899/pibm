import json
import logging
import random
import time
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

ANALYSIS_PROMPT = """You are an expert public speaking coach analyzing a student's speech video.

Evaluate the speaker on the following criteria, scoring each from 1.0 to 10.0:

1. Fluency - How smooth and natural is the speech flow? Consider pauses, filler words (um, uh), and stuttering.
2. Word Choice - How appropriate and rich is the vocabulary? Is the language suitable for the context?
3. Sentence Formation - How well-structured are the sentences? Consider grammar, coherence, and logical flow.
4. Clarity - How clear and understandable is the speech? Consider pronunciation, articulation, and enunciation.
5. Confidence - How confident does the speaker appear? Consider vocal tone, pace, volume, and steadiness.
6. Overall Score - A weighted overall assessment of the speech quality.

Also provide:
- Summary: A 2-3 sentence overall assessment
- Strengths: 2-3 specific things the speaker did well
- Areas for Improvement: 2-3 specific, actionable suggestions

Respond ONLY with valid JSON in this exact format:
{
  "fluency": <number>,
  "word_choice": <number>,
  "sentence_formation": <number>,
  "clarity": <number>,
  "confidence": <number>,
  "overall_score": <number>,
  "summary": "<string>",
  "strengths": "<string>",
  "improvements": "<string>"
}"""

REQUIRED_KEYS = {"fluency", "word_choice", "sentence_formation", "clarity", "confidence", "overall_score", "summary", "strengths", "improvements"}


def _mock_analyze(file_path: Path) -> dict:
    logger.info("MOCK AI: Returning fake scores for %s", file_path.name)
    time.sleep(1)
    scores = {k: round(random.uniform(5.0, 9.5), 1) for k in ["fluency", "word_choice", "sentence_formation", "clarity", "confidence"]}
    scores["overall_score"] = round(sum(scores.values()) / len(scores), 1)
    scores["summary"] = "This is a mock analysis. The speaker demonstrated reasonable speaking skills across all dimensions."
    scores["strengths"] = "Good pacing and clear articulation. Maintained steady eye contact throughout the presentation."
    scores["improvements"] = "Consider varying vocal tone to emphasize key points. Reduce filler words like 'um' and 'uh'."
    return scores


def analyze_video(file_path: Path) -> dict:
    if settings.mock_ai:
        return _mock_analyze(file_path)

    if not settings.gemini_api_key:
        raise ValueError("Gemini API key not configured. Set GEMINI_API_KEY in .env")

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)

    logger.info("Uploading file to Gemini: %s (%d bytes)", file_path.name, file_path.stat().st_size)
    uploaded = client.files.upload(file=file_path)
    logger.info("File uploaded: name=%s, state=%s", uploaded.name, uploaded.state)

    timeout = 120
    start = time.time()
    while uploaded.state == "PROCESSING":
        elapsed = time.time() - start
        if elapsed > timeout:
            raise ValueError("Video processing timed out after 120 seconds")
        logger.info("File still processing (%.0fs elapsed), polling...", elapsed)
        time.sleep(2)
        uploaded = client.files.get(name=uploaded.name)
        logger.info("File state: %s", uploaded.state)

    if uploaded.state == "FAILED":
        raise ValueError("Gemini failed to process the video file")

    try:
        logger.info("Sending generate_content request to model=gemini-3.5-flash")
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=[uploaded, ANALYSIS_PROMPT],
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        logger.info("Received response from Gemini (%d chars)", len(response.text or ""))
        result = json.loads(response.text)
    except json.JSONDecodeError:
        logger.error("Failed to parse response as JSON: %s", response.text[:500])
        raise ValueError("Failed to parse AI response as JSON")
    except Exception as e:
        logger.error("Gemini API error: %s", e)
        raise
    finally:
        try:
            client.files.delete(name=uploaded.name)
        except Exception:
            pass

    missing = REQUIRED_KEYS - set(result.keys())
    if missing:
        raise ValueError(f"AI response missing fields: {', '.join(missing)}")

    for key in ["fluency", "word_choice", "sentence_formation", "clarity", "confidence", "overall_score"]:
        score = float(result[key])
        result[key] = max(1.0, min(10.0, score))

    return result
