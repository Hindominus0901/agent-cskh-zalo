/* Widget chat CSKH — nhung bang MOT dong vao bat ky trang nao:
 *
 *   <script src="https://may-chu-cua-ban/widget.js" defer></script>
 *
 * Tuy bien bang thuoc tinh data-* tren chinh the script do:
 *
 *   data-ten     ten hien o thanh tieu de   (mac dinh "Trợ lý")
 *   data-mau     mau chu dao                (mac dinh "#0068ff" — xanh Zalo)
 *   data-chao    cau chao dau tien
 *   data-goc     "trai" de doi sang goc trai
 *
 * Nguyen tac: KHONG dung khung nao ca, khong tai them file nao. Landing page
 * cua khach thuong da nang san — widget CSKH khong duoc lam no nang them.
 * Toan bo CSS nam trong Shadow DOM nen khong bao gio da nhau voi giao dien trang.
 */
(function () {
  "use strict";

  var GOC = "__GOC__";
  var script = document.currentScript;
  var d = script ? script.dataset : {};
  var TEN = d.ten || "Trợ lý";
  var MAU = d.mau || "#0068ff";
  var CHAO = d.chao || "Dạ em có thể giúp gì cho anh/chị ạ?";
  var BEN = d.goc === "trai" ? "left" : "right";

  var boc = document.createElement("div");
  boc.setAttribute("aria-live", "polite");
  document.body.appendChild(boc);
  var goc = boc.attachShadow({ mode: "open" });

  goc.innerHTML =
    "<style>" +
    ":host{all:initial}" +
    "*{box-sizing:border-box;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif}" +
    ".nut{position:fixed;bottom:20px;" + BEN + ":20px;width:56px;height:56px;border-radius:50%;" +
    "background:" + MAU + ";border:0;cursor:pointer;box-shadow:0 4px 16px rgba(0,0,0,.25);" +
    "display:flex;align-items:center;justify-content:center;z-index:2147483000}" +
    ".nut svg{width:26px;height:26px;fill:#fff}" +
    ".khung{position:fixed;bottom:88px;" + BEN + ":20px;width:360px;max-width:calc(100vw - 32px);" +
    "height:520px;max-height:calc(100vh - 120px);background:#fff;border-radius:14px;" +
    "box-shadow:0 8px 40px rgba(0,0,0,.22);display:none;flex-direction:column;overflow:hidden;" +
    "z-index:2147483000}" +
    ".khung.mo{display:flex}" +
    ".dau{background:" + MAU + ";color:#fff;padding:14px 16px;font-weight:600;font-size:15px;" +
    "display:flex;justify-content:space-between;align-items:center}" +
    ".dong{background:none;border:0;color:#fff;font-size:22px;cursor:pointer;line-height:1;padding:0 4px}" +
    ".than{flex:1;overflow-y:auto;padding:14px;background:#f4f6f8}" +
    ".d{margin-bottom:10px;display:flex}" +
    ".d.toi{justify-content:flex-end}" +
    ".bong{max-width:80%;padding:9px 13px;border-radius:14px;font-size:14px;line-height:1.5;" +
    "white-space:pre-wrap;word-wrap:break-word}" +
    ".bot .bong{background:#fff;color:#111;border-bottom-left-radius:4px;box-shadow:0 1px 2px rgba(0,0,0,.08)}" +
    ".toi .bong{background:" + MAU + ";color:#fff;border-bottom-right-radius:4px}" +
    ".cho .bong{color:#888;font-style:italic}" +
    ".chan{display:flex;padding:10px;gap:8px;background:#fff;border-top:1px solid #e6e8eb}" +
    ".chan input{flex:1;border:1px solid #d8dce0;border-radius:20px;padding:10px 14px;font-size:14px;outline:0}" +
    ".chan input:focus{border-color:" + MAU + "}" +
    ".chan button{background:" + MAU + ";border:0;border-radius:50%;width:38px;height:38px;" +
    "cursor:pointer;display:flex;align-items:center;justify-content:center;flex-shrink:0}" +
    ".chan button svg{width:18px;height:18px;fill:#fff}" +
    ".chan button:disabled{opacity:.45;cursor:default}" +
    "@media(max-width:480px){.khung{bottom:0;right:0;left:0;width:100%;max-width:100%;height:100%;" +
    "max-height:100%;border-radius:0}}" +
    "</style>" +
    '<button class="nut" aria-label="Mở khung chat">' +
    '<svg viewBox="0 0 24 24"><path d="M20 2H4a2 2 0 00-2 2v18l4-4h14a2 2 0 002-2V4a2 2 0 00-2-2z"/></svg>' +
    "</button>" +
    '<div class="khung" role="dialog" aria-label="Khung chat">' +
    '<div class="dau"><span></span><button class="dong" aria-label="Đóng">&times;</button></div>' +
    '<div class="than"></div>' +
    '<form class="chan"><input type="text" placeholder="Nhập câu hỏi…" autocomplete="off" ' +
    'maxlength="1000" aria-label="Câu hỏi"><button type="submit" aria-label="Gửi">' +
    '<svg viewBox="0 0 24 24"><path d="M2 21l21-9L2 3v7l15 2-15 2v7z"/></svg></button></form>' +
    "</div>";

  var nut = goc.querySelector(".nut");
  var khung = goc.querySelector(".khung");
  var than = goc.querySelector(".than");
  var form = goc.querySelector(".chan");
  var o = goc.querySelector("input");
  var gui = goc.querySelector('button[type="submit"]');
  goc.querySelector(".dau span").textContent = TEN;

  function them(ai, text) {
    var d = document.createElement("div");
    d.className = "d " + ai;
    var b = document.createElement("div");
    b.className = "bong";
    b.textContent = text;
    d.appendChild(b);
    than.appendChild(d);
    than.scrollTop = than.scrollHeight;
    return d;
  }

  var daMo = false;
  function bat() {
    khung.classList.toggle("mo");
    if (khung.classList.contains("mo")) {
      if (!daMo) {
        daMo = true;
        them("bot", CHAO);
      }
      o.focus();
    }
  }
  nut.addEventListener("click", bat);
  goc.querySelector(".dong").addEventListener("click", bat);

  var dangGui = false;
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = o.value.trim();
    if (!text || dangGui) return;

    them("toi", text);
    o.value = "";
    dangGui = true;
    gui.disabled = true;
    var cho = them("bot cho", "đang trả lời…");

    fetch(GOC + "/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      credentials: "include", // cookie phien — thieu no la moi cau mot nguoi la
      body: JSON.stringify({ text: text, trang: location.href })
    })
      .then(function (r) {
        return r.json().catch(function () {
          return { tra_loi: [] };
        });
      })
      .then(function (j) {
        cho.remove();
        var ds = (j && j.tra_loi) || [];
        if (!ds.length) ds = ["Dạ em chưa nhận được câu trả lời ạ. Anh/chị thử lại giúp em nhé."];
        ds.forEach(function (t) {
          them("bot", t);
        });
      })
      .catch(function () {
        cho.remove();
        them("bot", "Dạ mạng đang trục trặc ạ. Anh/chị thử lại giúp em nhé.");
      })
      .finally(function () {
        dangGui = false;
        gui.disabled = false;
        o.focus();
      });
  });
})();
