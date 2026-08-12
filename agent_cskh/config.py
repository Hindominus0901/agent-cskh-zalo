"""Cau hinh tap trung. Doc tu .env, validate mot lan luc khoi dong.

Nguyen tac: khong module nao khac duoc doc os.environ truc tiep.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # ---------- Che do ----------
    # tra_cuu — 0 dong, khong can API key nao. Bot tra loi bang cach tim trang
    #           trong kho tri thuc (regex bo dau, khong phai embedding), theo ba
    #           nguong tin cay. Khong hieu ngu canh nhieu luot, khong suy luan.
    # ai      — Claude. Harness day du: vong lap, cong cu, skill, ba lop guard.
    #
    # MAC DINH LA tra_cuu, va do la mot lua chon co chu dich. Mot nguoi vua nhan
    # repo nay chua chac da co the tin dung ngay, va cung chua chac muon tra tien
    # API truoc khi thay bot chay. Ho phai thay no chay TRUOC.
    #
    # Hai che do dung CHUNG mot `knowledge/`. Doi che do la doi mot dong o day,
    # khong phai lam lai kho tri thuc.
    che_do: Literal["tra_cuu", "ai"] = "tra_cuu"

    # ---------- Zalo ----------
    zalo_bot_token: SecretStr = SecretStr("")
    zalo_api_base: str = "https://bot-api.zaloplatforms.com"
    transport: Literal["polling", "webhook"] = "polling"
    webhook_url: str = ""
    webhook_secret: SecretStr = SecretStr("")

    zalo_monthly_quota: int = 3000
    quota_warn_pct: int = 80
    quota_hard_pct: int = 95

    # ---------- LLM (chi dung khi che_do = "ai") ----------
    anthropic_api_key: SecretStr = SecretStr("")
    claude_model: str = "claude-sonnet-5"
    daily_cost_limit_usd: float = 2.0

    # ---------- Quyen ----------
    # NoDecode: khong de pydantic-settings thu json.loads truoc validator ben duoi.
    owner_user_ids: Annotated[list[str], NoDecode] = Field(default_factory=list)
    alert_chat_id: str = ""

    # ---------- Harness ----------
    max_iterations: int = 8
    turn_timeout: int = 180
    llm_timeout: int = 90
    tool_timeout: int = 30
    # Gioi han cung cua sendMessage la 2000 ky tu.
    max_reply_chars: int = 2000
    max_concurrent_turns: int = 8
    rate_limit_per_min: int = 12

    # ---------- Tim kiem ----------
    # KHONG co cau hinh embedding: kho tri thuc chay bang LLM Wiki (Markdown +
    # danh muc trong prompt duoc cache), con tim tin nhan cu chay bang FTS5.
    # Ca hai deu khong dung vector. Xem ghi chu trong pyproject.toml.

    # ---------- Van hanh ----------
    log_level: str = "INFO"
    log_json: bool = False
    timezone: str = "Asia/Ho_Chi_Minh"

    # ---------- Duong dan (suy ra, khong doc tu env) ----------
    @property
    def data_dir(self) -> Path:
        return ROOT / "data"

    @property
    def db_path(self) -> Path:
        return self.data_dir / "app.db"

    @property
    def media_dir(self) -> Path:
        return self.data_dir / "media"

    @property
    def outbox_dir(self) -> Path:
        return self.data_dir / "outbox"

    @property
    def log_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def knowledge_dir(self) -> Path:
        return ROOT / "knowledge"

    @property
    def skills_dir(self) -> Path:
        return ROOT / "skills"

    @property
    def fixtures_dir(self) -> Path:
        return ROOT / "tests" / "fixtures" / "updates"

    @field_validator("owner_user_ids", mode="before")
    @classmethod
    def _split_ids(cls, v: object) -> object:
        if isinstance(v, str):
            return [x.strip() for x in v.split(",") if x.strip()]
        return v

    @field_validator("max_reply_chars")
    @classmethod
    def _cap_reply(cls, v: int) -> int:
        # Zalo tu choi tin > 2000 ky tu. Khong cho cau hinh vuot.
        return min(v, 2000)

    # ---------- Tien ich ----------
    @property
    def token(self) -> str:
        return self.zalo_bot_token.get_secret_value()

    def api_url(self, method: str) -> str:
        """https://bot-api.zaloplatforms.com/bot<TOKEN>/<method>"""
        return f"{self.zalo_api_base}/bot{self.token}/{method}"

    def redact(self, text: str) -> str:
        """Che token trong bat ky chuoi nao truoc khi log."""
        tok = self.token
        return text.replace(tok, "<TOKEN>") if tok else text

    def ensure_dirs(self) -> None:
        for d in (
            self.data_dir,
            self.media_dir,
            self.outbox_dir,
            self.log_dir,
            self.knowledge_dir / "wiki" / "public",
            self.knowledge_dir / "wiki" / "hocvien",
            self.knowledge_dir / "wiki" / "internal",
            self.fixtures_dir,
        ):
            d.mkdir(parents=True, exist_ok=True)

    def problems(self) -> list[str]:
        """Tien dieu kien de dua bot len ZALO. Rong = san sang chay tren Zalo.

        KHONG kiem cho `agent-cskh chat`. Chat trong terminal o che do tra_cuu
        khong can token nao, khong can key nao — va do chinh la duong di ma
        nguoi moi nhan repo se di dau tien.
        """
        out: list[str] = []
        if not self.token:
            out.append("ZALO_BOT_TOKEN trong — tao bot trong app Zalo qua OA \"Zalo Bot Manager\", xem docs/01-noi-zalo.md")
        elif ":" not in self.token:
            out.append("ZALO_BOT_TOKEN sai dinh dang (phai co dang <id>:<secret>)")
        # Thieu key o che do `ai` la loi CHAN CHAY, khong phai canh bao.
        #
        # Truoc 11/08/2026 cho nay chi kiem khi `che_do == "ai"` va `che_do` lai
        # khong duoc doc o dau trong duong chay Zalo — nen dat `tra_cuu` roi chay
        # thi bot van goi Claude ma khong ai bao gi, roi chet luc goi model that.
        # Gio `app.py` da re nhanh theo `che_do`, va dieu kien nay dung tro lai.
        if self.che_do == "ai" and not self.anthropic_api_key.get_secret_value():
            out.append(
                "CHE_DO=ai nhung ANTHROPIC_API_KEY trong "
                "— lay tai https://console.anthropic.com, hoac doi ve CHE_DO=tra_cuu "
                "de chay mien phi bang kho tri thuc"
            )
        if self.transport == "webhook" and not self.webhook_url:
            out.append("TRANSPORT=webhook nhung WEBHOOK_URL trong")
        if not self.owner_user_ids:
            out.append("OWNER_USER_IDS trong — chay bot roi gui /whoami de lay user_id cua ban")
        return out


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
