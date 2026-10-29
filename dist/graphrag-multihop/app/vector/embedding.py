"""Real CPU inference in one supervised local worker; no runtime network or fallback."""

import importlib.metadata
import math
import multiprocessing
import os
import threading
import time

from app.extraction.models import stable_id
from app.vector.models import VectorFailure

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
# Immutable upstream commit; preparation downloads this revision, inference is cache-only.
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
DIMENSION = 384
MAX_TOKENS = 256


def validate_vector(vector):
    if (
        not isinstance(vector, (list, tuple))
        or len(vector) != DIMENSION
        or any(
            isinstance(v, bool) or not isinstance(v, (float, int)) or not math.isfinite(v)
            for v in vector
        )
    ):
        raise VectorFailure("invalid_embedding")
    norm = math.sqrt(sum(v * v for v in vector))
    if not math.isclose(norm, 1, abs_tol=1e-4):
        raise VectorFailure("invalid_embedding")
    return [float(v) for v in vector]


def _worker(pipe, threads):
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    os.environ["TOKENIZERS_PARALLELISM"] = "false"
    try:
        import torch
        from sentence_transformers import SentenceTransformer

        torch.set_num_threads(threads)
        torch.manual_seed(0)
        model = SentenceTransformer(
            MODEL, revision=REVISION, device="cpu", local_files_only=True, trust_remote_code=False
        )
        if model.get_embedding_dimension() != DIMENSION or model.max_seq_length != MAX_TOKENS:
            raise ValueError("Unexpected model configuration")
        pipe.send(("ready", None))
        while True:
            texts = pipe.recv()
            if texts is None:
                break
            counts = [len(model.tokenizer.encode(t, truncation=False)) for t in texts]
            if any(n > MAX_TOKENS for n in counts):
                pipe.send(("error", "embedding_token_limit"))
                continue
            vectors = model.encode(
                texts, batch_size=32, normalize_embeddings=True, show_progress_bar=False
            ).tolist()
            pipe.send(("vectors", vectors))
    except (EOFError, BrokenPipeError):
        pass
    except Exception:
        try:
            pipe.send(("error", "embedding_model_unavailable"))
        except (EOFError, BrokenPipeError, OSError):
            pass
    finally:
        pipe.close()


class MiniLM:
    def __init__(self, startup_timeout=180, inference_timeout=30, threads=2):
        self.version = stable_id(
            "embedding",
            MODEL,
            REVISION,
            "normalized-float32-cpu-v1",
            MAX_TOKENS,
            importlib.metadata.version("sentence-transformers"),
            importlib.metadata.version("transformers"),
            importlib.metadata.version("torch"),
        )
        self.startup_timeout = startup_timeout
        self.inference_timeout = inference_timeout
        self.threads = threads
        self.lock = threading.Lock()
        self.process = self.pipe = None
        self.cold_start_ms = None

    def _receive(self, timeout):
        if not self.pipe.poll(timeout):
            self._stop()
            raise VectorFailure("embedding_timeout")
        try:
            kind, value = self.pipe.recv()
        except (EOFError, OSError) as exc:
            self._stop()
            raise VectorFailure("embedding_model_unavailable") from exc
        if kind == "error":
            raise VectorFailure(value)
        return kind, value

    def _start(self):
        if self.process and self.process.is_alive():
            return
        self._stop()
        started = time.perf_counter()
        context = multiprocessing.get_context("spawn")
        self.pipe, child = context.Pipe()
        self.process = context.Process(target=_worker, args=(child, self.threads), daemon=True)
        self.process.start()
        child.close()
        try:
            if self._receive(self.startup_timeout)[0] != "ready":
                raise VectorFailure("embedding_model_unavailable")
        except Exception:
            self._stop()
            raise
        self.cold_start_ms = (time.perf_counter() - started) * 1000

    def encode(self, texts):
        if (
            not texts
            or len(texts) > 32
            or any(not isinstance(t, str) or not t.strip() for t in texts)
        ):
            raise VectorFailure("invalid_embedding_input")
        if not self.lock.acquire(timeout=self.inference_timeout):
            raise VectorFailure("embedding_busy")
        try:
            self._start()
            try:
                self.pipe.send(texts)
                kind, values = self._receive(self.inference_timeout)
            except (OSError, EOFError) as exc:
                self._stop()
                raise VectorFailure("embedding_model_unavailable") from exc
            if kind != "vectors" or len(values) != len(texts):
                raise VectorFailure("invalid_embedding")
            return [validate_vector(v) for v in values]
        finally:
            self.lock.release()

    def _stop(self):
        if self.process:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=3)
            self.process.close()
        if self.pipe:
            self.pipe.close()
        self.process = self.pipe = None

    def close(self):
        with self.lock:
            self._stop()
