"""Offline validation of speech-to-text output before canonical transcript intake.

Does not invoke a provider, transcribe audio, persist content, or grant review rights.
"""
import hashlib
from .csf_v02 import CSFValidationError
from .csf_source_intake import prepare_source

def validate_transcription(segments, *, document_id, expected_sha256):
    if not isinstance(segments, list) or not segments or len(segments) > 100000:
        raise CSFValidationError("transcription segments required")
    last_end = 0
    texts = []
    for item in segments:
        if not isinstance(item, dict) or set(item) != {"start_ms", "end_ms", "text"}:
            raise CSFValidationError("invalid transcription segment")
        start, end, text = item["start_ms"], item["end_ms"], item["text"]
        if (type(start) is not int or type(end) is not int
                or start < last_end or end <= start
                or not isinstance(text, str) or not text.strip()):
            raise CSFValidationError("invalid transcription timing or text")
        texts.append(text)
        last_end = end
    # This normalized text is NOT equivalent to raw provider output or audio.
    transcript = "\n".join(texts)
    digest = hashlib.sha256(transcript.encode("utf-8")).hexdigest()
    if digest != expected_sha256:
        raise CSFValidationError("transcript digest mismatch")
    result = prepare_source(transcript, document_id=document_id, expected_sha256=digest)
    return dict(result, transcription_segments=len(segments),
                transcription_duration_ms=last_end,
                audio_verified=False, transcription_accuracy_verified=False)
