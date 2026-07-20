import json
import logging
import random
import time
from pathlib import Path

from pydantic import BaseModel, Field

from app.config import settings

logger = logging.getLogger(__name__)


class ParameterScore(BaseModel):
    score_out_of_100: int = Field(description="The score assigned for this specific parameter (0-100).")
    feedback: str = Field(description="Specific, actionable feedback explaining the score. 1-2 sentences.")


class VisualPresence(BaseModel):
    eye_contact_consistency_30pct: ParameterScore
    posture_and_alignment_25pct: ParameterScore
    hand_gestures_20pct: ParameterScore
    facial_expressions_15pct: ParameterScore
    spatial_awareness_10pct: ParameterScore


class VocalDelivery(BaseModel):
    pacing_25pct: ParameterScore
    vocal_variety_25pct: ParameterScore
    strategic_pausing_20pct: ParameterScore
    volume_and_projection_15pct: ParameterScore
    enunciation_15pct: ParameterScore


class ContentStructure(BaseModel):
    frameworks_and_data_25pct: ParameterScore
    opening_hook_20pct: ParameterScore
    logical_flow_20pct: ParameterScore
    actionable_conclusion_20pct: ParameterScore
    time_management_15pct: ParameterScore


class VerbalCommunication(BaseModel):
    filler_word_frequency_30pct: ParameterScore
    vocabulary_richness_25pct: ParameterScore
    conciseness_20pct: ParameterScore
    active_vs_passive_voice_15pct: ParameterScore
    grammar_and_syntax_10pct: ParameterScore


class AudienceEngagement(BaseModel):
    confidence_score_30pct: ParameterScore
    empathy_and_relatability_25pct: ParameterScore
    rhetorical_questions_20pct: ParameterScore
    storytelling_15pct: ParameterScore
    qa_readiness_10pct: ParameterScore


class PresentationEvaluation(BaseModel):
    visual_presence: VisualPresence
    vocal_delivery: VocalDelivery
    content_structure: ContentStructure
    verbal_communication: VerbalCommunication
    audience_engagement: AudienceEngagement
    overall_summary: str = Field(description="A brief executive summary of the student's overall performance.")


ANALYSIS_PROMPT = """You are an expert executive communications coach for MBA and Master's students.
Analyze the attached presentation video. Evaluate the student's performance strictly according to the schema provided.

For each parameter, provide a score from 0 to 100 based on standard executive presence benchmarks,
and write 1-2 sentences of highly specific, actionable feedback referencing exact moments or quotes
from the video where possible."""

CATEGORY_WEIGHTS = {
    "visual_presence": 0.25,
    "vocal_delivery": 0.20,
    "content_structure": 0.25,
    "verbal_communication": 0.15,
    "audience_engagement": 0.15,
}

CATEGORY_PARAMS = {
    "visual_presence": [
        ("eye_contact_consistency_30pct", 0.30),
        ("posture_and_alignment_25pct", 0.25),
        ("hand_gestures_20pct", 0.20),
        ("facial_expressions_15pct", 0.15),
        ("spatial_awareness_10pct", 0.10),
    ],
    "vocal_delivery": [
        ("pacing_25pct", 0.25),
        ("vocal_variety_25pct", 0.25),
        ("strategic_pausing_20pct", 0.20),
        ("volume_and_projection_15pct", 0.15),
        ("enunciation_15pct", 0.15),
    ],
    "content_structure": [
        ("frameworks_and_data_25pct", 0.25),
        ("opening_hook_20pct", 0.20),
        ("logical_flow_20pct", 0.20),
        ("actionable_conclusion_20pct", 0.20),
        ("time_management_15pct", 0.15),
    ],
    "verbal_communication": [
        ("filler_word_frequency_30pct", 0.30),
        ("vocabulary_richness_25pct", 0.25),
        ("conciseness_20pct", 0.20),
        ("active_vs_passive_voice_15pct", 0.15),
        ("grammar_and_syntax_10pct", 0.10),
    ],
    "audience_engagement": [
        ("confidence_score_30pct", 0.30),
        ("empathy_and_relatability_25pct", 0.25),
        ("rhetorical_questions_20pct", 0.20),
        ("storytelling_15pct", 0.15),
        ("qa_readiness_10pct", 0.10),
    ],
}


def compute_overall_score(data: dict) -> float:
    total = 0.0
    for category_key, params in CATEGORY_PARAMS.items():
        cat = data[category_key]
        cat_weight = CATEGORY_WEIGHTS[category_key]
        cat_score = sum(cat[p]["score_out_of_100"] * w for p, w in params)
        total += cat_score * cat_weight
    return round(total / 10, 1)


def _mock_score() -> dict:
    return {
        "score_out_of_100": random.randint(55, 95),
        "feedback": "Mock feedback. Good use of structure, but consider varying your pacing more during key transitions.",
    }


def _mock_analyze(file_path: Path) -> dict:
    logger.info("MOCK AI: Returning fake scores for %s", file_path.name)
    time.sleep(1)
    return {
        "visual_presence": {

            "eye_contact_consistency_30pct": _mock_score(),
            "posture_and_alignment_25pct": _mock_score(),
            "hand_gestures_20pct": _mock_score(),
            "facial_expressions_15pct": _mock_score(),
            "spatial_awareness_10pct": _mock_score(),
        },
        "vocal_delivery": {

            "pacing_25pct": _mock_score(),
            "vocal_variety_25pct": _mock_score(),
            "strategic_pausing_20pct": _mock_score(),
            "volume_and_projection_15pct": _mock_score(),
            "enunciation_15pct": _mock_score(),
        },
        "content_structure": {

            "frameworks_and_data_25pct": _mock_score(),
            "opening_hook_20pct": _mock_score(),
            "logical_flow_20pct": _mock_score(),
            "actionable_conclusion_20pct": _mock_score(),
            "time_management_15pct": _mock_score(),
        },
        "verbal_communication": {

            "filler_word_frequency_30pct": _mock_score(),
            "vocabulary_richness_25pct": _mock_score(),
            "conciseness_20pct": _mock_score(),
            "active_vs_passive_voice_15pct": _mock_score(),
            "grammar_and_syntax_10pct": _mock_score(),
        },
        "audience_engagement": {

            "confidence_score_30pct": _mock_score(),
            "empathy_and_relatability_25pct": _mock_score(),
            "rhetorical_questions_20pct": _mock_score(),
            "storytelling_15pct": _mock_score(),
            "qa_readiness_10pct": _mock_score(),
        },
        "overall_summary": "Mock summary. The student showed strong logical structure and confident delivery. Key areas for improvement include vocal variety during transitions and more deliberate hand gestures to reinforce key points.",
    }


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
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PresentationEvaluation,
                temperature=0.2,
            ),
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

    return result
