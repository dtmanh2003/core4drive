"""
NeuroAI — Offline rule-based AI (no internet required).
Covers: greetings, math, car info, navigation, weather, media,
        general casual chat, and a smart fallback.
Returns a (response: str, confident: bool) tuple so NeuroCore
can decide whether to escalate to the online Claude API.
"""
import re
import random
from datetime import datetime


class NeuroAI:

    # ── Helpers ───────────────────────────────────────────────────────────────
    @staticmethod
    def _p(options: list) -> str:
        return random.choice(options)

    @staticmethod
    def _m(text: str, keywords: list) -> bool:
        return any(k in text for k in keywords)

    @classmethod
    def respond(cls, query: str, speed: int, risk: int, habits) -> tuple:
        """
        Returns (response_text, confident).
        confident=True  → use this offline answer directly.
        confident=False → try online Claude first, use this as fallback.
        """
        ql    = query.strip().lower()
        dest  = habits.habits.get("frequent_destination", "HAL東京") if hasattr(habits, "habits") else "HAL東京"
        music = habits.habits.get("preferred_music", "Lo-fi Beats") if hasattr(habits, "habits") else "Lo-fi Beats"
        hour  = datetime.now().hour
        now   = datetime.now().strftime("%H:%M")

        # ── Math (always offline, always confident) ───────────────────────────
        math_result = cls._try_math(query)
        if math_result is not None:
            return (math_result, True)

        # ── Greetings ─────────────────────────────────────────────────────────
        if cls._m(ql, ["こんにちは", "おはよう", "こんばんは", "hello", "hi", "やあ", "よろしく", "元気"]):
            if hour < 12:
                return (cls._p(["おはよう！今日も一緒に頑張ろう〜", "おはようございます！いい朝だね。"]), True)
            if hour < 18:
                return (cls._p(["やあ！どこ行くの？", "こんにちは！何か手伝えることある？"]), True)
            return (cls._p(["こんばんは！夜のドライブだね。気をつけてね。", "お疲れ様！どこ行くの？"]), True)

        # ── Thanks ────────────────────────────────────────────────────────────
        if cls._m(ql, ["ありがとう", "thanks", "thank", "助かった", "サンキュー", "ありがと"]):
            return (cls._p(["どういたしまして！", "いつでも！", "お役に立てて良かった〜"]), True)

        # ── Bye ───────────────────────────────────────────────────────────────
        if cls._m(ql, ["バイバイ", "またね", "さようなら", "おやすみ", "bye", "じゃあね"]):
            return (cls._p(["またね！気をつけて〜", "お疲れ様でした！", "またいつでも呼んでね。"]), True)

        # ── Speed ─────────────────────────────────────────────────────────────
        if cls._m(ql, ["速度", "スピード", "何キロ", "speed", "時速", "どのくらい速"]):
            if speed == 0:
                return ("今は停車中だよ。", True)
            feel = ("ゆっくり走ってるね。" if speed < 60 else
                    "いい感じのペースだよ！" if speed < 100 else
                    "ちょっと速いかな。気をつけてね。" if speed < 130 else
                    "かなり飛ばしてる！安全運転でいこう。")
            return (cls._p([f"今{speed}km/hだよ。{feel}", f"{speed}km/h走行中。{feel}"]), True)

        # ── Risk ─────────────────────────────────────────────────────────────
        if cls._m(ql, ["リスク", "危険度", "事故リスク", "risk", "どのくらい危"]):
            if risk < 30:
                return (f"リスク{risk}%。全然大丈夫！安全だよ。", True)
            if risk < 60:
                return (f"リスク{risk}%。まあ普通かな。周囲に注意してね。", True)
            return (f"リスク{risk}%。ちょっと高めだよ。気をつけて！", True)

        if cls._m(ql, ["安全", "大丈夫", "危ない"]):
            if risk < 50 and speed < 100:
                return (cls._p(["うん、今は安全だよ！心配しないで。", "問題ないよ。いい感じ！"]), True)
            return (f"リスク{risk}%あるから少し注意した方がいいかな。", True)

        # ── Navigation ────────────────────────────────────────────────────────
        if cls._m(ql, ["ナビ", "案内", "目的地", "行き方", "道", "帰り", "帰る", "どこ行"]):
            mins = random.randint(10, 22)
            return (cls._p([f"{dest}に向かうね！約{mins}分で着くよ〜",
                             f"OK！{dest}まで案内するね。{mins}分くらいかな。"]), True)

        # ── Weather ───────────────────────────────────────────────────────────
        if cls._m(ql, ["天気", "気温", "weather", "雨", "晴", "曇", "温度", "暑", "寒"]):
            wx = cls._p([("晴れで24°C", "ドライブ日和だね！"),
                          ("くもりで21°C", "過ごしやすい感じ。"),
                          ("晴れ時々くもり、26°C", "日差し強いから気をつけてね。")])
            return (f"今日は{wx[0]}だよ。{wx[1]}", True)

        # ── Music ─────────────────────────────────────────────────────────────
        if cls._m(ql, ["音楽", "music", "曲", "再生", "止めて", "次", "ラジオ", "ミュージック", "歌"]):
            if cls._m(ql, ["止めて", "停止", "stop", "pause"]): return ("止めたよ！", True)
            if cls._m(ql, ["次", "スキップ", "next", "変えて"]):  return ("次の曲にするね！", True)
            if cls._m(ql, ["何", "どんな", "なに"]):             return (f"今は{music}を流してるよ！", True)
            return (cls._p([f"{music}流すね！", f"了解！{music}をどうぞ〜"]), True)

        # ── Vehicle ───────────────────────────────────────────────────────────
        if cls._m(ql, ["エンジン", "燃料", "ガソリン", "バッテリー", "タイヤ", "状態", "点検"]):
            return (cls._p(["エンジン正常、燃料65%、バッテリー85%。全部OK！",
                             "車の調子はいいよ！燃料65%、バッテリー85%。"]), True)

        # ── Traffic ───────────────────────────────────────────────────────────
        if cls._m(ql, ["渋滞", "交通", "混んで", "混雑", "traffic"]):
            return (cls._p(["前方3.5kmあたりに渋滞あるよ。迂回する？",
                             "ちょっと先が混んでるみたい。別ルート行く？"]), True)

        # ── Time ─────────────────────────────────────────────────────────────
        if cls._m(ql, ["時間", "何時", "到着", "あと何分", "いつ着く"]):
            mins = random.randint(8, 20)
            return (f"今{now}だよ。{dest}まであと約{mins}分くらいかな！", True)

        # ── Calls / Phone ─────────────────────────────────────────────────────
        if cls._m(ql, ["電話", "call", "メッセージ", "連絡", "かけて", "line"]):
            return ("走行中だから、停まってからにしようね。安全第一！", True)

        # ── Parking ───────────────────────────────────────────────────────────
        if cls._m(ql, ["駐車", "parking", "止める", "park", "停める"]):
            return ("近くに駐車場3箇所あるよ！どこがいい？", True)

        # ── Emergency ─────────────────────────────────────────────────────────
        if cls._m(ql, ["緊急", "助けて", "sos", "emergency", "事故った", "ぶつかった", "気分悪"]):
            return ("緊急モード起動！安全な場所に停車して。緊急連絡先に通知するよ！", True)

        # ── Fatigue / Rest ────────────────────────────────────────────────────
        if cls._m(ql, ["疲れた", "つかれた", "しんどい", "眠い", "ねむい", "眠たい"]):
            return (cls._p(["お疲れ！少し休憩しようか？安全が一番だよ。",
                             "眠いなら休んで！近くにコンビニあるよ〜"]), True)

        # ── Hungry ───────────────────────────────────────────────────────────
        if cls._m(ql, ["お腹", "腹減", "食べたい", "腹すい", "腹ペコ", "ランチ", "ご飯"]):
            return (cls._p(["近くにコンビニあるよ！寄ってく？",
                             f"もうすぐ{dest}に着くから、そこで食べよう！"]), True)

        # ── Temperature ──────────────────────────────────────────────────────
        if cls._m(ql, ["暑い", "あつい", "熱い"]): return (cls._p(["エアコン強くしようか？", "冷房つけるね！"]), True)
        if cls._m(ql, ["寒い", "さむい", "冷え"]):  return (cls._p(["暖房上げようか？", "ヒーターつけるね！"]), True)

        # ── Bored ────────────────────────────────────────────────────────────
        if cls._m(ql, ["暇", "退屈", "つまらない", "話しかけて", "話して", "何か話"]):
            return (cls._p(["じゃあ、今日どこ行くの？",
                             f"そうだ、{dest}に着いたら何するの？",
                             "音楽でも流そうか？ドライブが楽しくなるよ！"]), True)

        # ── About Neuro ───────────────────────────────────────────────────────
        if cls._m(ql, ["neuro", "ニューロ", "あなた誰", "何ができる", "機能", "自己紹介"]):
            return ("私Neuro！君のドライブを手伝う車内AIだよ。ナビ、天気、音楽、会話、なんでも任せて！", True)

        # ── Simple affirmations ───────────────────────────────────────────────
        if cls._m(ql, ["はい", "yes", "うん", "そう", "お願い", "頼む", "して"]):
            return (cls._p(["了解！", "OK！", "任せて！"]), True)
        if cls._m(ql, ["いいえ", "no", "いや", "やめて", "キャンセル", "結構"]):
            return (cls._p(["分かった！", "OK、やめとくね。", "了解〜"]), True)

        # ── Safety-critical fallback (always confident) ───────────────────────
        if risk >= 75:
            return ("今ちょっと危ない状況だから、運転に集中してね！", True)
        if speed >= 120:
            return ("飛ばしてるね〜！安全運転でいこう。", True)

        # ── General fallback (NOT confident → try online first) ───────────────
        fallbacks = [
            "ごめん、よく分からなかった。もう一回言って？",
            "うーん、聞き取れなかったかも。「ナビ」「天気」「音楽」とか言ってみて！",
            "何だって？もう一回教えて〜",
        ]
        return (random.choice(fallbacks), False)   # ← confident=False

    # ── Math evaluator ────────────────────────────────────────────────────────
    @staticmethod
    def _try_math(text: str) -> str | None:
        """Detect and evaluate simple arithmetic. Returns result string or None."""
        # Normalize Japanese operators
        expr = (text.strip()
                .replace("×", "*").replace("÷", "/")
                .replace("＋", "+").replace("－", "-")
                .replace("は", "").replace("いくら", "").replace("?", "").replace("？", "")
                .replace(" ", ""))
        # Only allow safe characters
        if not re.fullmatch(r'[\d+\-*/().]+', expr):
            return None
        if len(expr) < 3:
            return None
        try:
            result = eval(expr)  # safe: only digits and operators allowed
            if isinstance(result, float) and result.is_integer():
                result = int(result)
            return f"{expr.replace('*','×').replace('/',  '÷')} = {result} だよ！"
        except Exception:
            return None
