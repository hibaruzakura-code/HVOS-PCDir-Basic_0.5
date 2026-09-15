

import ctypes
import os
import threading
import tkinter as tk
from PIL import Image
import keyboard
import pyautogui
from google import genai

# ==========================================
# ターミナル画面を最背面へ移動＆フォーカス解除
# ==========================================
if os.name == "nt":
  hwnd = ctypes.windll.kernel32.GetConsoleWindow()
  if hwnd != 0:
    # HWND_BOTTOM (=1), SWP_NOSIZE(0x0001) | SWP_NOMOVE(0x0002) | SWP_NOACTIVATE(0x0010)
    flags = 0x0001 | 0x0002 | 0x0010
    ctypes.windll.user32.SetWindowPos(hwnd, 1, 0, 0, 0, 0, flags)

# ==========================================
# 🔑 APIキー設定（ここに取得したキーを貼り付けます）
# ==========================================
GEMINI_API_KEY = "あなたの api key"

# Gemini クライアントの初期化
genai_client = genai.Client(api_key=GEMINI_API_KEY)

# グローバル状態管理
target_side = "left"  # 初期値：画面の左側
is_processing = False


# ==========================================
# UI (tkinter) オーバーレイ画面の管理クラス
# ==========================================
class OverlayUI:

  def __init__(self):
    self.root = tk.Tk()
    self.root.title("HVOS PC Direct")

    # ウィンドウの見た目・動作設定
    self.root.attributes("-topmost", True)  # 常に最前面
    self.root.attributes("-alpha", 0.80)  # 80%の半透明
    self.root.configure(bg="#1e1e1e")  # ダークモード風背景
    self.root.geometry("600x1200+50+50")  # 幅600x高さ1200 (左上に配置)

    # タイトル・状態表示ラベル
    self.status_label = tk.Label(
        self.root,
        text="[HVOS Direct] ターゲット: 左の方 | 【1】キーで撮影",
        font=("メイリオ", 9, "bold"),
        fg="#4CAF50",
        bg="#1e1e1e",
    )
    self.status_label.pack(anchor="w", padx=10, pady=(10, 5))

    # Text と Scrollbar をまとめるフレーム
    frame = tk.Frame(self.root, bg="#1e1e1e")
    frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    # スクロールバーの配置（Canvasによるカスタム描画）
    self.scroll_canvas = tk.Canvas(
        frame, bg="#2d2d2d", width=16, highlightthickness=0, bd=0
    )
    self.scroll_canvas.pack(side=tk.RIGHT, fill=tk.Y)

    # 回答テキスト表示エリア（スクロール可能）
    self.text_area = tk.Text(
        frame,
        font=("メイリオ", 10),
        fg="#ffffff",
        bg="#2d2d2d",
        wrap=tk.WORD,
        bd=0,
        padx=10,
        pady=10,
        yscrollcommand=self.update_custom_scrollbar,
    )
    self.text_area.pack(fill=tk.BOTH, expand=True)

    # スクロールバーのイベントバインド
    self.scroll_canvas.bind("<B1-Motion>", self.on_scroll_drag)
    self.scroll_canvas.bind("<Button-1>", self.on_scroll_click)

    self.text_area.insert(
        tk.END,
        "画面上の解説したいエリア（← /"
        " →）を選び、【1】キーを押してください。",
    )
    self.text_area.config(state=tk.DISABLED)

  def update_custom_scrollbar(self, first, last):
    """テキストのスクロール位置に合わせてダークバーを描画"""
    self.text_area.yview_moveto(first)
    self.scroll_canvas.delete("all")

    f, l = float(first), float(last)
    if l - f >= 1.0:
      return  # スクロール不要な場合は非表示

    ch = self.scroll_canvas.winfo_height()
    y1 = f * ch
    y2 = l * ch

    # 幅16pxに合わせてバーの左右位置（2〜14）を調整して描画
    self.scroll_canvas.create_rectangle(
        2, y1, 14, y2, fill="#555555", outline=""
    )

  def on_scroll_drag(self, event):
    ch = self.scroll_canvas.winfo_height()
    if ch > 0:
      self.text_area.yview_moveto(event.y / ch)

  def on_scroll_click(self, event):
    ch = self.scroll_canvas.winfo_height()
    if ch > 0:
      self.text_area.yview_moveto(event.y / ch)

  def safe_update_status(self, text, color="#4CAF50"):
    """メインスレッドから安全にステータスラベルを更新"""
    self.root.after(0, lambda: self.status_label.config(text=text, fg=color))

  def safe_update_text(self, text):
    """メインスレッドから安全にテキストエリアを更新"""

    def _update():
      self.text_area.config(state=tk.NORMAL)
      self.text_area.delete("1.0", tk.END)
      self.text_area.insert(tk.END, text)
      self.text_area.config(state=tk.DISABLED)

    self.root.after(0, _update)


ui = None


# ==========================================
# キャプチャ ＆ Gemini API 呼び出し処理
# ==========================================
def capture_and_analyze():
  global is_processing, target_side
  if is_processing:
    return

  is_processing = True
  ui.safe_update_status("📸 キャプチャ中...", "#FF9800")
  ui.safe_update_text(
      "画像を切り出し、Gemini APIへ送信中...\nしばらくお待ちください。"
  )

  try:
    # 1. 画面全体のサイズ取得
    screen_width, screen_height = pyautogui.size()

# 2. 左右ターゲットに応じた範囲の切り出し
    if target_side == "left":
      left = int(screen_width * 0.01)
      top = int(screen_height * 0.01)
      width = int(screen_width * 0.48)
      height = int(screen_height * 0.98)
    else:
      left = int(screen_width * 0.51)
      top = int(screen_height * 0.01)
      width = int(screen_width * 0.48)
      height = int(screen_height * 0.98)

    screenshot = pyautogui.screenshot(region=(left, top, width, height))

    # 3. 一時保存
    img_path = "temp_capture.png"
    screenshot.save(img_path)

    ui.safe_update_status("🧠 Geminiが解析中...", "#2196F3")

    # 4. Gemini API 呼び出し
    prompt = (
        "あなたは最高のバーチャルツアーガイドです。このVR画像に写っている景色・場所について、以下の構成で600文字程度で魅力的に解説してください。\n\n"
        "1. 【場所の特定と概要】：ここがどこか、何という施設・景色か\n"
        "2."
        " 【歴史と背景】：この場所にまつわる深い歴史やストーリー、建築のこだわりなど\n"
        "3."
        " 【ここだけの魅力・おすすめポイント】：訪れた人が『ワクワクする』豆知識や見どころ\n"
        "4."
        " 【周囲のおすすめ・楽しみ方】：もし実際にここを歩くなら立ち寄るべき周辺スポットや楽しみ方\n\n"
        "語り口は親しみやすく、聞いているだけで旅に出たくなるようなワクワクする文章でまとめてください。文末には必ず『（文字数：〇〇文字）』と実際に生成した文字数を記載してください。"
    )

    img = Image.open(img_path)
    response = genai_client.models.generate_content(
        model="gemini-3.6-flash", contents=[prompt, img]
    )

    # 5. UIへ直出し描画
    ui.safe_update_text(response.text)
    ui.safe_update_status(
        f"✅ 解析完了 (ターゲット: {'左の方' if target_side == 'left' else '右の方'})",
        "#4CAF50",
    )

    # キャプチャ画像の削除
    if os.path.exists(img_path):
      os.remove(img_path)

  except Exception as e:
    ui.safe_update_text(f"エラーが発生しました:\n{str(e)}")
    ui.safe_update_status("❌ エラー発生", "#F44336")

  finally:
    is_processing = False


# ==========================================
# キーボードショートカットの監視（スレッド実行）
# ==========================================
def listen_keyboard():
  global target_side
  while True:
    if keyboard.is_pressed("left"):
      target_side = "left"
      ui.safe_update_status(
          "[HVOS Direct] ターゲット: 左の方 | 【1】キーで撮影", "#4CAF50"
      )
      pyautogui.sleep(0.3)
    elif keyboard.is_pressed("right"):
      target_side = "right"
      ui.safe_update_status(
          "[HVOS Direct] ターゲット: 右の方 | 【1】キーで撮影", "#4CAF50"
      )
      pyautogui.sleep(0.3)
    elif keyboard.is_pressed("1"):
      threading.Thread(target=capture_and_analyze, daemon=True).start()
      pyautogui.sleep(0.5)
    pyautogui.sleep(0.05)


# ==========================================
# メイン実行エリア
# ==========================================
if __name__ == "__main__":
  ui = OverlayUI()
  # キーボード監視をバックグラウンドスレッドで起動
  threading.Thread(target=listen_keyboard, daemon=True).start()
  # tkinterのメインループ実行
  ui.root.mainloop()