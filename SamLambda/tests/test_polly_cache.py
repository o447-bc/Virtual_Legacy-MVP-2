"""
Unit tests for Polly caching in speech.py (text_to_speech).

Turn 0 uses a shared cache key: polly-cache/{question_id}/{voice_id}-{engine}.mp3
  - Cache hit  → presigned URL returned, Polly NOT called
  - Cache miss → synthesize via Polly, store at cache key with KMS encryption

Turn 1+ always synthesizes via Polly (no cache check).

Uses importlib to import speech.py with a unique module name to avoid
collision with other test files that import different 'app' modules.
"""

import importlib
import importlib.util
import io
import os
import sys
from unittest.mock import MagicMock, patch

import pytest
from hypothesis import given, settings, HealthCheck
from hypothesis import strategies as st

# ---------------------------------------------------------------------------
# Import speech.py via importlib to avoid module-name collisions
# ---------------------------------------------------------------------------

_SPEECH_PATH = os.path.join(
    os.path.dirname(__file__),
    "..",
    "functions",
    "conversationFunctions",
    "wsDefault",
    "speech.py",
)

_spec = importlib.util.spec_from_file_location("speech_module", _SPEECH_PATH)
speech = importlib.util.module_from_spec(_spec)

# Patch boto3 before exec_module so module-level clients are mocks
_mock_boto3 = MagicMock()
with patch.dict(sys.modules, {"boto3": _mock_boto3, "botocore.client": MagicMock()}):
    _spec.loader.exec_module(speech)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUCKET = "virtual-legacy"
KMS_ARN = "arn:aws:kms:us-east-1:123456789012:key/test-key-id"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

class _ClientError(Exception):
    """Stand-in for botocore ClientError raised on S3 head_object miss."""

    def __init__(self):
        super().__init__("Not Found")
        self.response = {"Error": {"Code": "404", "Message": "Not Found"}}


def _audio_stream(data: bytes = b"fake-mp3-data"):
    """Return a mock Polly AudioStream."""
    stream = MagicMock()
    stream.read.return_value = data
    return stream


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def _env_and_clients(monkeypatch):
    """Patch module-level clients and env vars for every test."""
    monkeypatch.setattr(speech, "S3_BUCKET", BUCKET)

    # Fresh mocks each test
    mock_polly = MagicMock()
    mock_s3 = MagicMock()

    # Wire up ClientError so `except s3_client.exceptions.ClientError` works
    mock_s3.exceptions.ClientError = _ClientError

    monkeypatch.setattr(speech, "polly", mock_polly)
    monkeypatch.setattr(speech, "s3_client", mock_s3)

    # Default: Polly returns audio
    mock_polly.synthesize_speech.return_value = {
        "AudioStream": _audio_stream(),
    }

    # Default: S3 presigned URL
    mock_s3.generate_presigned_url.return_value = "https://s3.example.com/presigned"

    yield mock_polly, mock_s3


@pytest.fixture()
def polly_mock(_env_and_clients):
    return _env_and_clients[0]


@pytest.fixture()
def s3_mock(_env_and_clients):
    return _env_and_clients[1]


# ===================================================================
# 1. Turn 0 — cache hit
# ===================================================================

class TestTurn0CacheHit:
    """When turn_number=0 and S3 head_object succeeds, return presigned URL
    without calling Polly or uploading anything."""

    def test_returns_presigned_url(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            s3_mock.head_object.return_value = {}  # cache hit

            url = speech.text_to_speech(
                text="Hello",
                user_id="u1",
                question_id="q1",
                turn_number=0,
                voice_id="Joanna",
                engine="neural",
            )

        assert url == "https://s3.example.com/presigned"

    def test_polly_not_called(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            s3_mock.head_object.return_value = {}

            speech.text_to_speech("Hi", "u1", "q1", 0, "Joanna", "neural")

        polly_mock.synthesize_speech.assert_not_called()

    def test_put_object_not_called(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            s3_mock.head_object.return_value = {}

            speech.text_to_speech("Hi", "u1", "q1", 0, "Joanna", "neural")

        s3_mock.put_object.assert_not_called()


# ===================================================================
# 2. Turn 0 — cache miss → synthesize + upload
# ===================================================================

class TestTurn0CacheMiss:
    """When turn_number=0 and head_object raises ClientError,
    synthesize via Polly and store at the cache key."""

    def test_polly_called(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            s3_mock.head_object.side_effect = _ClientError()

            speech.text_to_speech("Hi", "u1", "q1", 0, "Joanna", "neural")

        polly_mock.synthesize_speech.assert_called_once_with(
            Text="Hi",
            OutputFormat="mp3",
            VoiceId="Joanna",
            Engine="neural",
        )

    def test_put_object_uses_cache_key(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            s3_mock.head_object.side_effect = _ClientError()

            speech.text_to_speech("Hi", "u1", "q1", 0, "Joanna", "neural")

        call_kwargs = s3_mock.put_object.call_args.kwargs
        assert call_kwargs["Key"] == "polly-cache/q1/Joanna-neural.mp3"
        assert call_kwargs["Bucket"] == BUCKET


# ===================================================================
# 3. Turn 0 cache miss — KMS encryption on put_object
# ===================================================================

class TestTurn0CacheMissKMS:
    """Verify that the cached object is stored with KMS encryption."""

    def test_kms_encryption_params(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            s3_mock.head_object.side_effect = _ClientError()

            speech.text_to_speech("Hi", "u1", "q1", 0, "Joanna", "neural")

        call_kwargs = s3_mock.put_object.call_args.kwargs
        assert call_kwargs["ServerSideEncryption"] == "aws:kms"
        assert call_kwargs["SSEKMSKeyId"] == KMS_ARN


# ===================================================================
# 4. Turn 1 — always synthesize, no cache check
# ===================================================================

class TestTurn1:
    """Turn 1 always calls Polly and never checks the cache."""

    def test_polly_called(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            speech.text_to_speech("Reply", "u1", "q1", 1, "Joanna", "neural")

        polly_mock.synthesize_speech.assert_called_once()

    def test_head_object_not_called(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            speech.text_to_speech("Reply", "u1", "q1", 1, "Joanna", "neural")

        s3_mock.head_object.assert_not_called()

    def test_uses_per_user_key(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            speech.text_to_speech("Reply", "u1", "q1", 1, "Joanna", "neural")

        call_kwargs = s3_mock.put_object.call_args.kwargs
        key = call_kwargs["Key"]
        assert key.startswith("conversations/u1/q1/ai-audio/turn-1-")
        assert key.endswith(".mp3")


# ===================================================================
# 5. Turn 2, 3 — same behaviour as turn 1
# ===================================================================

class TestHigherTurns:
    """Turns 2+ behave identically to turn 1."""

    @pytest.mark.parametrize("turn", [2, 3])
    def test_polly_always_called(self, turn, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            speech.text_to_speech("More", "u1", "q1", turn, "Joanna", "neural")

        polly_mock.synthesize_speech.assert_called_once()

    @pytest.mark.parametrize("turn", [2, 3])
    def test_head_object_not_called(self, turn, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            speech.text_to_speech("More", "u1", "q1", turn, "Joanna", "neural")

        s3_mock.head_object.assert_not_called()

    @pytest.mark.parametrize("turn", [2, 3])
    def test_uses_per_user_key(self, turn, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            speech.text_to_speech("More", "u1", "q1", turn, "Joanna", "neural")

        key = s3_mock.put_object.call_args.kwargs["Key"]
        assert key.startswith(f"conversations/u1/q1/ai-audio/turn-{turn}-")


# ===================================================================
# 6. Same inputs → same cache key (deterministic)
# ===================================================================

class TestCacheKeyDeterministic:
    """Same (question_id, voice_id, engine) must always produce the same key."""

    def test_same_inputs_same_key(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            s3_mock.head_object.side_effect = _ClientError()

            speech.text_to_speech("A", "u1", "q1", 0, "Joanna", "neural")
            key1 = s3_mock.put_object.call_args.kwargs["Key"]

            s3_mock.put_object.reset_mock()
            s3_mock.head_object.side_effect = _ClientError()

            speech.text_to_speech("A", "u2", "q1", 0, "Joanna", "neural")
            key2 = s3_mock.put_object.call_args.kwargs["Key"]

        assert key1 == key2


# ===================================================================
# 7. Different question_id → different cache key
# ===================================================================

class TestCacheKeyVariesByQuestion:
    """Different question_id must produce a different cache key."""

    def test_different_question_different_key(self, s3_mock, polly_mock):
        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            s3_mock.head_object.side_effect = _ClientError()

            speech.text_to_speech("A", "u1", "q1", 0, "Joanna", "neural")
            key1 = s3_mock.put_object.call_args.kwargs["Key"]

            s3_mock.put_object.reset_mock()
            s3_mock.head_object.side_effect = _ClientError()

            speech.text_to_speech("A", "u1", "q2", 0, "Joanna", "neural")
            key2 = s3_mock.put_object.call_args.kwargs["Key"]

        assert key1 != key2


# ===================================================================
# Property test — cache key determinism via Hypothesis
# ===================================================================

# Strategies for realistic IDs
_question_ids = st.text(
    alphabet=st.characters(whitelist_categories=("L", "N"), whitelist_characters="-_"),
    min_size=1,
    max_size=40,
)
_voice_ids = st.text(
    alphabet=st.characters(whitelist_categories=("L",)),
    min_size=1,
    max_size=20,
)
_engines = st.sampled_from(["neural", "standard", "long-form", "generative"])


class TestCacheKeyProperty:
    """Property: cache key is a pure function of (question_id, voice_id, engine)."""

    @given(qid=_question_ids, voice=_voice_ids, engine=_engines)
    @settings(
        max_examples=200,
        suppress_health_check=[HealthCheck.function_scoped_fixture],
    )
    def test_deterministic_cache_key(self, qid, voice, engine, _env_and_clients):
        """Two calls with the same (Q, V, E) must produce identical cache keys."""
        _, s3_mock = _env_and_clients

        with patch.object(speech.os, "environ", {"KMS_KEY_ARN": KMS_ARN}):
            s3_mock.head_object.side_effect = _ClientError()
            s3_mock.put_object.reset_mock()

            speech.text_to_speech("txt", "u1", qid, 0, voice, engine)
            key1 = s3_mock.put_object.call_args.kwargs["Key"]

            s3_mock.put_object.reset_mock()
            s3_mock.head_object.side_effect = _ClientError()

            speech.text_to_speech("txt", "u2", qid, 0, voice, engine)
            key2 = s3_mock.put_object.call_args.kwargs["Key"]

        expected = f"polly-cache/{qid}/{voice}-{engine}.mp3"
        assert key1 == expected
        assert key2 == expected
