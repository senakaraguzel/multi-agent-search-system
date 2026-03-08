"""
ExecutionTracer — Singleton çalışma izi toplayıcısı.

Her ajan bu modülü import edip global `tracer` nesnesini kullanır:
    from agents.utils.execution_tracer import tracer
    tracer.log("agent_name", "adım mesajı")
    tracer.set_results("agent_name", results_list)

main.py sonunda:
    tracer.save(user_query, "data/sorgu_output.json")
"""

import json
import os
import threading
from datetime import datetime


class ExecutionTracer:
    """
    Thread-safe, singleton tarzı çalışma izi toplayıcısı.
    Her ajan kendi bloğunu yazar; main.py tümünü birleştirir.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._agents: dict[str, dict] = {}

    # ── Dahili: ajan bloğunu hazırla ─────────────────────────────────────────
    def _ensure_agent(self, agent_key: str) -> None:
        if agent_key not in self._agents:
            self._agents[agent_key] = {
                "results_count": 0,
                "results": [],
                "execution_trace": [],
            }

    # ── Adım logu yaz ────────────────────────────────────────────────────────
    def log(
        self,
        agent_key: str,
        message: str,
        status: str = "info",
        data: dict | None = None,
    ) -> None:
        """
        Bir ajan adımını (execution_trace) kaydeder.

        Args:
            agent_key : Ajan adı (örn: "agent_1_planner")
            message   : İnsan okunabilir adım mesajı
            status    : "info" | "success" | "warning" | "error"
            data      : Opsiyonel ek yapısal veri
        """
        entry: dict = {
            "timestamp": datetime.now().isoformat(timespec="seconds"),
            "status": status,
            "message": message,
        }
        if data:
            entry["data"] = data

        with self._lock:
            self._ensure_agent(agent_key)
            self._agents[agent_key]["execution_trace"].append(entry)

        # Konsola da yansıt (mevcut print düzenini bozmamak için)
        prefix = {"info": "ℹ", "success": "✓", "warning": "⚠", "error": "✗"}.get(status, "•")
        print(f"  [{agent_key}] {prefix} {message}")

    # ── Sonuçları kaydet ─────────────────────────────────────────────────────
    def set_results(
        self,
        agent_key: str,
        results: list,
        extra_meta: dict | None = None,
    ) -> None:
        """
        Bir ajanın ürettiği sonuç listesini ve isteğe bağlı meta verisini kaydeder.

        Args:
            agent_key  : Ajan adı
            results    : Sonuç listesi (dict veya str öğelerden oluşan)
            extra_meta : Opsiyonel ek meta (örn: {"pipeline": "Spesifik", ...})
        """
        with self._lock:
            self._ensure_agent(agent_key)
            self._agents[agent_key]["results"] = results
            self._agents[agent_key]["results_count"] = len(results)
            if extra_meta:
                self._agents[agent_key]["meta"] = extra_meta

    # ── Tek ajan bloğunu al ─────────────────────────────────────────────────
    def get_agent(self, agent_key: str) -> dict:
        with self._lock:
            return dict(self._agents.get(agent_key, {}))

    # ── Tüm veriyi birleştir ─────────────────────────────────────────────────
    def to_dict(self, query: str) -> dict:
        """Tüm ajan verilerini kullanıcı sorgusuna bağlı tek JSON yapısında döner."""
        with self._lock:
            return {
                "sorgu": query,
                "traced_at": datetime.now().isoformat(timespec="seconds"),
                "agents": dict(self._agents),
            }

    # ── Diske kaydet ─────────────────────────────────────────────────────────
    def save(self, query: str, path: str = "data/sorgu_output.json") -> None:
        """
        Birleşik çalışma izini JSON dosyasına yazar.

        Args:
            query : Orijinal kullanıcı sorgusu
            path  : Çıktı dosyası yolu
        """
        output = self.to_dict(query)
        os.makedirs(os.path.dirname(path), exist_ok=True)

        json_str = json.dumps(output, ensure_ascii=False, indent=4)
        safe_str = json_str.encode("utf-8", "replace").decode("utf-8")

        with open(path, "w", encoding="utf-8") as f:
            f.write(safe_str)

        total_traces = sum(
            len(v.get("execution_trace", [])) for v in output["agents"].values()
        )
        print(
            f"\n[ExecutionTracer] ✓ {len(output['agents'])} ajan, "
            f"{total_traces} iz adımı → {path}"
        )

    # ── Sıfırla (yeni oturum için) ───────────────────────────────────────────
    def reset(self) -> None:
        """Yeni bir sorgu oturumu öncesinde tüm veriyi temizler."""
        with self._lock:
            self._agents.clear()


# ─── Global singleton ─────────────────────────────────────────────────────────
tracer = ExecutionTracer()
