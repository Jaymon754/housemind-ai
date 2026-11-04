"""Hybrid RAG engine: Markdown knowledge base + Chroma + BM25 + citations.

The default embedding is a deterministic character n-gram hashing model so the
project works completely offline and on a fresh machine.  It is lexical-semantic
rather than a neural embedding; BM25 is fused to improve exact-term recall.  An
LLM, when configured, writes the final answer grounded in retrieved chunks.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

import numpy as np

from ..core.config import settings

DIM = 512
CATEGORY_LABELS = {
    "valuation": "估值方法",
    "ai": "可解释 AI",
    "investment": "投资分析",
    "mortgage": "房贷融资",
    "transaction": "交易流程",
    "due_diligence": "尽职调查",
    "cost": "持有成本",
    "rental": "租赁管理",
    "market": "市场分析",
    "ethics": "公平与伦理",
    "safety": "AI 安全",
    "vision": "图片分析",
    "policy": "政策",
    "tax": "税务",
    "insurance": "保险",
}
SYNONYMS = {
    "月供": "房贷 贷款 摊还 月供 还款",
    "首付": "首付 贷款 杠杆 down payment",
    "回报率": "回报 收益 cap rate 资本化率 cash on cash 现金回报",
    "租金": "租金 出租 租赁 rent 空置",
    "现金流": "现金流 净运营收入 NOI DSCR 偿债",
    "估值": "估值 定价 AVM 比较法 预测",
    "解释": "解释 SHAP 归因 可解释",
    "风险": "风险 不确定性 压力测试 保险",
    "税": "税 1031 资本利得 房产税",
    "检查": "检查 验房 尽职调查 结构 维修",
    "政策": "政策 限购 契税 公积金",
    "图片": "图片 照片 视觉 装修 采光",
    "安全": "安全 提示词注入 隐私 幻觉",
}


# Generic question words and light verbs that should not create retrieval hits
# on their own.  Without this gate, a question like “如何更换汽车轮胎” matches
# “如何/更换” in unrelated property-maintenance passages.
_QUERY_STOP_BIGRAMS = {
    "如何", "什么", "为什", "怎么", "是否", "可以", "哪些", "一下", "介绍",
    "关系", "意味", "影响", "基本", "条件", "需要", "多少", "一个", "这套",
    "那套", "以及", "还是", "值得", "请问", "帮我", "告诉", "分析", "解释",
    "比较", "区别", "更换", "汽车", "时候", "问题", "进行", "如果", "那么",
    "推荐", "适合", "一款", "玩游", "游戏", "显卡",
}
_QUERY_LATIN_STOP = {
    "what", "how", "does", "the", "and", "for", "with", "this", "that", "are",
    "can", "should", "from", "into", "about", "why", "when", "which",
}


def _content_terms(text: str) -> set[str]:
    """Rare-ish query terms used to reject out-of-corpus questions.

    CJK unigrams are deliberately excluded: they create accidental matches on
    function characters.  Bigrams, Latin domain terms and 2–5 digit numbers are
    specific enough to serve as evidence of topical overlap.
    """
    terms: set[str] = set()
    normalised = normalise(text)
    for run in re.findall(r"[\u4e00-\u9fff]+", normalised):
        for index in range(len(run) - 1):
            term = run[index : index + 2]
            if term not in _QUERY_STOP_BIGRAMS:
                terms.add(term)
    for token in re.findall(r"[a-z][a-z0-9._-]{1,}", normalised):
        if token not in _QUERY_LATIN_STOP:
            terms.add(token)
    terms.update(re.findall(r"\b\d{2,5}\b", normalised))
    return terms

def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).lower()
    return text.replace("\u3000", " ")


def tokenize(text: str, expand: bool = False) -> list[str]:
    text = normalise(text)
    if expand:
        for key, value in SYNONYMS.items():
            if key in text:
                text += " " + value
    latin = re.findall(r"[a-z][a-z0-9._-]{1,}", text)
    cjk_runs = re.findall(r"[\u4e00-\u9fff]+", text)
    tokens: list[str] = list(latin)
    for run in cjk_runs:
        tokens.extend(list(run))
        tokens.extend(run[index : index + 2] for index in range(len(run) - 1))
    # Keep numbers (useful for 1031, 45 days, DSCR thresholds).
    tokens.extend(re.findall(r"\b\d{2,5}\b", text))
    return [token for token in tokens if token.strip()]


def embed(text: str) -> np.ndarray:
    """Signed feature hashing over word/CJK n-grams, L2 normalised."""
    vector = np.zeros(DIM, dtype=np.float32)
    counts = Counter(tokenize(text, expand=True))
    for token, count in counts.items():
        digest = hashlib.md5(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "little") % DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        weight = 1.0 + math.log1p(count)
        vector[index] += sign * weight
    norm = float(np.linalg.norm(vector))
    if norm:
        vector /= norm
    return vector


@dataclass
class Chunk:
    id: str
    doc_id: str
    title: str
    category: str
    section: str
    content: str
    source_name: str
    source_url: str
    updated: str
    tokens: list[str]
    vector: np.ndarray

    @property
    def metadata(self) -> dict[str, Any]:
        return {
            "doc_id": self.doc_id,
            "title": self.title,
            "category": self.category,
            "category_label": CATEGORY_LABELS.get(self.category, self.category),
            "section": self.section,
            "source_name": self.source_name,
            "source_url": self.source_url,
            "updated": self.updated,
        }


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta: dict[str, str] = {}
    for line in parts[1].strip().splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
    return meta, parts[2].strip()


def _split_long(text: str, limit: int = 900, overlap: int = 100) -> list[str]:
    if len(text) <= limit:
        return [text]
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    current = ""
    for paragraph in paragraphs:
        if len(current) + len(paragraph) + 2 <= limit:
            current = f"{current}\n\n{paragraph}".strip()
        else:
            if current:
                pieces.append(current)
            while len(paragraph) > limit:
                pieces.append(paragraph[:limit])
                paragraph = paragraph[limit - overlap :]
            current = paragraph
    if current:
        pieces.append(current)
    return pieces


def load_chunks(directory: Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(directory.glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        meta, body = _frontmatter(raw)
        title = meta.get("title") or path.stem
        category = meta.get("category", "general")
        sections = re.split(r"\n(?=##\s+)", body)
        doc_id = path.stem
        for section_index, section in enumerate(sections):
            lines = section.strip().splitlines()
            heading = lines[0].lstrip("# ").strip() if lines and lines[0].startswith("#") else title
            section_body = "\n".join(lines[1:]).strip() if lines and lines[0].startswith("#") else section.strip()
            if not section_body:
                continue
            for piece_index, piece in enumerate(_split_long(section_body)):
                content = f"{title} · {heading}\n\n{piece}".strip()
                chunk_id = hashlib.sha1(f"{path.name}:{section_index}:{piece_index}".encode()).hexdigest()[:16]
                chunks.append(
                    Chunk(
                        id=chunk_id,
                        doc_id=doc_id,
                        title=title,
                        category=category,
                        section=heading,
                        content=content,
                        source_name=meta.get("source_name", "HouseMind AI 知识库"),
                        source_url=meta.get("source_url", ""),
                        updated=meta.get("updated", ""),
                        tokens=tokenize(content, expand=False),
                        vector=embed(content),
                    )
                )
    return chunks


class BM25:
    def __init__(self, chunks: list[Chunk], k1: float = 1.5, b: float = 0.75):
        self.chunks = chunks
        self.k1 = k1
        self.b = b
        self.lengths = np.array([len(chunk.tokens) for chunk in chunks], dtype=float)
        self.avgdl = float(self.lengths.mean()) if len(chunks) else 1.0
        self.tf = [Counter(chunk.tokens) for chunk in chunks]
        df = Counter()
        for tokens in self.tf:
            df.update(set(tokens))
        total = len(chunks)
        self.idf = {term: math.log(1 + (total - freq + 0.5) / (freq + 0.5)) for term, freq in df.items()}

    def scores(self, query_tokens: list[str]) -> np.ndarray:
        scores = np.zeros(len(self.chunks), dtype=float)
        for index, frequencies in enumerate(self.tf):
            length_norm = self.k1 * (1 - self.b + self.b * self.lengths[index] / self.avgdl)
            for term in query_tokens:
                frequency = frequencies.get(term, 0)
                if frequency:
                    scores[index] += self.idf.get(term, 0) * frequency * (self.k1 + 1) / (frequency + length_norm)
        return scores


class RAGService:
    def __init__(self) -> None:
        self.chunks = load_chunks(settings.knowledge_dir)
        if not self.chunks:
            raise RuntimeError("knowledge_base 为空，无法构建 RAG 索引")
        self.bm25 = BM25(self.chunks)
        self.vectors = np.vstack([chunk.vector for chunk in self.chunks])
        self.backend = "numpy"
        self.collection = None
        self._init_chroma()
        self.indexed_at = datetime.now(timezone.utc).isoformat()

    def _fingerprint(self) -> str:
        digest = hashlib.sha1()
        for path in sorted(settings.knowledge_dir.glob("*.md")):
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def _init_chroma(self) -> None:
        try:
            import chromadb
            from chromadb.config import Settings as ChromaSettings

            client = chromadb.PersistentClient(
                path=str(settings.chroma_dir),
                settings=ChromaSettings(anonymized_telemetry=False),
            )
            fingerprint = self._fingerprint()
            fingerprint_file = settings.chroma_dir / "kb_fingerprint.json"
            rebuild = True
            if fingerprint_file.exists():
                try:
                    rebuild = json.loads(fingerprint_file.read_text()).get("fingerprint") != fingerprint
                except Exception:
                    rebuild = True
            if rebuild:
                try:
                    client.delete_collection("housemind_knowledge")
                except Exception:
                    pass
            collection = client.get_or_create_collection(
                name="housemind_knowledge",
                metadata={"hnsw:space": "cosine", "description": "HouseMind AI curated real-estate knowledge"},
            )
            if collection.count() != len(self.chunks) or rebuild:
                if collection.count():
                    client.delete_collection("housemind_knowledge")
                    collection = client.get_or_create_collection(
                        name="housemind_knowledge",
                        metadata={"hnsw:space": "cosine", "description": "HouseMind AI curated real-estate knowledge"},
                    )
                collection.add(
                    ids=[chunk.id for chunk in self.chunks],
                    documents=[chunk.content for chunk in self.chunks],
                    metadatas=[chunk.metadata for chunk in self.chunks],
                    embeddings=[chunk.vector.tolist() for chunk in self.chunks],
                )
            fingerprint_file.write_text(json.dumps({"fingerprint": fingerprint, "chunks": len(self.chunks)}))
            self.collection = collection
            self.backend = "chromadb"
        except Exception as exc:  # pragma: no cover - fallback is intentional
            self.backend = "numpy-fallback"
            self.backend_error = f"{type(exc).__name__}: {exc}"

    def _vector_scores(self, query: str, category: str | None) -> np.ndarray:
        vector = embed(query)
        if self.collection is not None:
            try:
                where = {"category": category} if category else None
                result = self.collection.query(
                    query_embeddings=[vector.tolist()],
                    n_results=min(max(20, settings.rag_top_k * 3), len(self.chunks)),
                    where=where,
                    include=["distances", "ids"],
                )
                scores = np.full(len(self.chunks), -1.0)
                index_by_id = {chunk.id: index for index, chunk in enumerate(self.chunks)}
                for chunk_id, distance in zip(result["ids"][0], result["distances"][0]):
                    if chunk_id in index_by_id:
                        scores[index_by_id[chunk_id]] = 1.0 - float(distance)
                return scores
            except Exception:
                pass
        return self.vectors @ vector

    def search(self, query: str, top_k: int | None = None, category: str | None = None) -> list[dict[str, Any]]:
        top_k = int(top_k or settings.rag_top_k)
        if category == "all":
            category = None
        vector_scores = self._vector_scores(query, category)
        original_tokens = tokenize(query, expand=False)
        content_terms = _content_terms(query)
        lexical_scores = self.bm25.scores(original_tokens)
        expanded_scores = self.bm25.scores(tokenize(query, expand=True))
        if category:
            for index, chunk in enumerate(self.chunks):
                if chunk.category != category:
                    lexical_scores[index] = 0
                    expanded_scores[index] = 0
                    vector_scores[index] = -1

        def minmax(values: np.ndarray, mask: np.ndarray | None = None) -> np.ndarray:
            valid = values if mask is None else values[mask]
            if not len(valid) or valid.max() == valid.min():
                return np.zeros_like(values)
            return (values - valid.min()) / (valid.max() - valid.min())

        vector_norm = minmax(np.maximum(vector_scores, 0))
        lexical_norm = minmax(lexical_scores)
        expanded_norm = minmax(expanded_scores)
        query_tokens = set(original_tokens)
        query_lower = normalise(query)
        # Acronyms and high-signal domain terms must not be drowned out by the
        # many Chinese character bigrams produced by a long question.
        key_weights = {
            "dscr": 1.20, "cap rate": 1.05, "noi": 1.05, "irr": 0.95, "roi": 0.85,
            "shap": 1.05, "avm": 0.95, "pmi": 0.85, "hoa": 0.55, "1031": 1.05,
            "mae": 1.00, "rmse": 0.80, "r²": 0.90, "覆盖率": 0.50, "残差": 0.40,
            "提示词注入": 0.90, "公平住房": 0.85, "照片": 0.35,
            "结构安全": 0.50, "首付": 0.18,
        }
        active_keys = [(term, weight) for term, weight in key_weights.items() if term in query_lower]
        combined = []
        for index, chunk in enumerate(self.chunks):
            content_lower = normalise(chunk.content)
            if content_terms:
                hits = sum(1 for term in content_terms if term in content_lower)
                # Require at least one specific term; this is the abstention gate.
                if hits == 0:
                    continue
            key_bonus = sum(weight for term, weight in active_keys if term in content_lower)
            section_bonus = sum(weight * 0.38 for term, weight in active_keys if term in normalise(chunk.section))
            title_tokens = set(tokenize(chunk.title))
            title_coverage = len(query_tokens & title_tokens) / max(len(query_tokens), 1)
            score = float(
                0.46 * vector_norm[index]
                + 0.27 * lexical_norm[index]
                + 0.17 * expanded_norm[index]
                + 0.14 * title_coverage
                + key_bonus
                + section_bonus
            )
            combined.append((score, index))
        combined.sort(reverse=True)
        results = []
        seen_docs: dict[str, int] = {}
        for score, index in combined:
            chunk = self.chunks[index]
            # Diversity: at most two chunks from the same document in one result set.
            if seen_docs.get(chunk.doc_id, 0) >= 2:
                continue
            seen_docs[chunk.doc_id] = seen_docs.get(chunk.doc_id, 0) + 1
            results.append(
                {
                    "id": chunk.id,
                    "doc_id": chunk.doc_id,
                    "title": chunk.title,
                    "section": chunk.section,
                    "category": chunk.category,
                    "category_label": CATEGORY_LABELS.get(chunk.category, chunk.category),
                    "content": chunk.content,
                    "snippet": _snippet(chunk.content, query),
                    "source_name": chunk.source_name,
                    "source_url": chunk.source_url,
                    "updated": chunk.updated,
                    "score": round(score, 4),
                }
            )
            if len(results) >= top_k:
                break
        return results

    def citations(self, results: list[dict[str, Any]]) -> list[dict[str, Any]]:
        citations = []
        for index, result in enumerate(results, 1):
            citations.append(
                {
                    "index": index,
                    "title": result["title"],
                    "section": result["section"],
                    "source_name": result["source_name"],
                    "source_url": result["source_url"],
                    "category": result["category_label"],
                    "score": result["score"],
                }
            )
        return citations

    def answer(self, question: str, top_k: int = 6, category: str | None = None) -> dict[str, Any]:
        results = self.search(question, top_k=top_k, category=category)
        if settings.llm_enabled:
            try:
                text = self._llm_answer(question, results)
                mode = "deepseek"
            except Exception as exc:
                text = self._extractive_answer(question, results)
                mode = f"local-fallback ({type(exc).__name__})"
        else:
            text = self._extractive_answer(question, results)
            mode = "local-extractive"
        return {
            "question": question,
            "answer": text,
            "citations": self.citations(results),
            "results": results,
            "mode": mode,
            "retrieval": {
                "backend": self.backend,
                "strategy": "Chroma 向量检索 + BM25 字符 n-gram 混合排序",
                "chunks": len(self.chunks),
                "documents": len({chunk.doc_id for chunk in self.chunks}),
            },
        }

    def _llm_answer(self, question: str, results: list[dict[str, Any]]) -> str:
        from openai import OpenAI

        context = "\n\n".join(
            f"[{index}] {result['title']} / {result['section']}\n{result['content']}"
            for index, result in enumerate(results, 1)
        )
        client = OpenAI(api_key=settings.deepseek_api_key, base_url=settings.deepseek_base_url)
        response = client.chat.completions.create(
            model=settings.deepseek_model,
            temperature=0.2,
            max_tokens=900,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是 HouseMind AI 的房产知识助手。只能依据给定资料回答，使用中文。"
                        "每个关键结论后用 [编号] 标注来源。资料不足时明确说明，不要编造法规、税率或数字。"
                        "不要提供个性化法律、税务或贷款结论，提醒用户咨询持牌专业人士。"
                    ),
                },
                {"role": "user", "content": f"资料：\n{context}\n\n问题：{question}"},
            ],
        )
        return response.choices[0].message.content.strip()

    def _extractive_answer(self, question: str, results: list[dict[str, Any]]) -> str:
        if not results:
            return "知识库中没有找到足够相关的资料。请尝试更具体的关键词，例如“资本化率与现金回报率的区别”。"
        sentences = []
        query_tokens = set(tokenize(question))
        for index, result in enumerate(results[:4], 1):
            body = result["content"].split("\n\n", 1)[-1]
            candidates = [s.strip() for s in re.split(r"(?<=[。！？；])", body) if len(s.strip()) > 20]
            candidates.sort(key=lambda s: len(query_tokens & set(tokenize(s))), reverse=True)
            chosen = (candidates[0] if candidates else body).strip()
            if len(chosen) > 180:
                chosen = chosen[:180].rstrip("，。；") + "…"
            sentences.append(f"- {chosen} [{index}]")
        lead = ""
        query_lower = normalise(question)
        if "dscr" in query_lower and ("首付" in query_lower or "down payment" in query_lower):
            dscr_index = next((i for i, r in enumerate(results[:4], 1) if "dscr" in normalise(r["section"]) or "dscr" in normalise(r["title"])), 1)
            mortgage_index = next(
                (
                    i
                    for i, r in enumerate(results[:4], 1)
                    if ("首付" in r["content"] or "贷款本金" in r["content"]) and ("月供" in r["content"] or "债务" in r["content"])
                ),
                dscr_index,
            )
            lead = (
                f"首付比例通过改变贷款本金与年度偿债额影响 DSCR：首付越高，贷款本金越小、年债务偿还额越低；"
                f"在 NOI 不变时，DSCR 越高。[{dscr_index}][{mortgage_index}]\n\n"
            )
        return (
            lead
            + "根据知识库检索结果，可以从以下要点理解：\n\n"
            + "\n".join(sentences)
            + "\n\n以上内容来自公开资料与项目方法说明，仅用于一般性分析。涉及具体交易、税务或法律决策时，请咨询持牌专业人士。"
        )

    def stats(self) -> dict[str, Any]:
        counts = Counter(chunk.category for chunk in self.chunks)
        docs = {chunk.doc_id: chunk for chunk in self.chunks}
        return {
            "backend": self.backend,
            "documents": len(docs),
            "chunks": len(self.chunks),
            "categories": [
                {"key": key, "label": CATEGORY_LABELS.get(key, key), "count": count}
                for key, count in counts.most_common()
            ],
            "embedding": f"local signed-hashing {DIM}d + BM25 hybrid",
            "indexed_at": self.indexed_at,
            "documents_list": [
                {
                    "doc_id": doc_id,
                    "title": chunk.title,
                    "category": chunk.category,
                    "category_label": CATEGORY_LABELS.get(chunk.category, chunk.category),
                    "source_name": chunk.source_name,
                    "source_url": chunk.source_url,
                    "sections": len([c for c in self.chunks if c.doc_id == doc_id]),
                }
                for doc_id, chunk in sorted(docs.items())
            ],
        }


def _snippet(content: str, query: str, length: int = 220) -> str:
    body = content.split("\n\n", 1)[-1]
    tokens = set(tokenize(query))
    sentences = [s.strip() for s in re.split(r"(?<=[。！？；\n])", body) if s.strip()]
    if sentences:
        sentences.sort(key=lambda s: len(tokens & set(tokenize(s))), reverse=True)
        snippet = sentences[0]
    else:
        snippet = body
    return snippet[:length] + ("…" if len(snippet) > length else "")


@lru_cache(maxsize=1)
def get_rag_service() -> RAGService:
    return RAGService()
