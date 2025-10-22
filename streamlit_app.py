# streamlit_app.py
import streamlit as st
import random, time, math, json
import pandas as pd
import numpy as np
import gspread
from datetime import datetime
from google.oauth2.service_account import Credentials

# Page
st.set_page_config(page_title="SPI 模擬テスト（本番版）", layout="centered")

# ---------- Config ----------
TIME_LIMIT_MIN = 50
NUM_VERBAL_TOTAL = 80
NUM_NONVERBAL_TOTAL = 80
NUM_VERBAL_PICK = 35
NUM_NONVERBAL_PICK = 35
TOTAL_PICK = NUM_VERBAL_PICK + NUM_NONVERBAL_PICK

# Google Sheet URL or Key (your sheet)
SHEET_URL = "https://docs.google.com/spreadsheets/d/17cM5v1-ejrYmycHJbuGsJhlGGzTX3g_spXj1YFIOOiM/edit?usp=sharing"
# name of the worksheet (first sheet typically)
SHEET_INDEX = 0

# scopes for Google API
SCOPES = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]

# ---------- Helpers: Google sheets ----------
def get_gsheet_client():
    try:
        # expects st.secrets["google"] to be present (service account json fields)
        info = st.secrets["google"]
        creds = Credentials.from_service_account_info(info, scopes=SCOPES)
        client = gspread.authorize(creds)
        return client
    except Exception as e:
        st.error("Google Sheets 認証に失敗しました。Secretsにservice account情報が登録されているか確認してください。")
        st.exception(e)
        return None

def append_row_safe(client, url, row):
    try:
        sh = client.open_by_url(url)
        ws = sh.get_worksheet(SHEET_INDEX)
        ws.append_row(row)
        return True, None
    except Exception as e:
        return False, str(e)

def fetch_history_total_pct(client, url):
    """If sheet has 'total_pct' column, return list of floats, else empty list"""
    try:
        sh = client.open_by_url(url)
        ws = sh.get_worksheet(SHEET_INDEX)
        records = ws.get_all_records()
        if not records:
            return []
        df = pd.DataFrame(records)
        # try find a total_pct-like column
        for col in ["total_pct", "総合%","total_pct (%)","total_pct_pct"]:
            if col in df.columns:
                return pd.to_numeric(df[col], errors="coerce").dropna().tolist()
        # try last column heuristics: if there is a numeric column with plausible pct values
        for c in df.columns[::-1]:
            vals = pd.to_numeric(df[c], errors="coerce")
            if vals.notna().sum() > 0 and vals.min() >= 0 and vals.max() <= 100:
                return vals.dropna().tolist()
        return []
    except Exception:
        return []

# ---------- Build problem pool (approx. SPI-style) ----------
@st.cache_data
def build_problem_pool():
    pool = []
    qid = 1
    # Verbal (80)
    synonym_pairs = [
        ("迅速","すばやい"),("頑強","たくましい"),("簡潔","短くまとめる"),
        ("綿密","細かく計画する"),("慎重","注意深い"),("傲慢","高慢"),
        ("冷淡","無関心"),("堅牢","丈夫"),("緩和","和らげる"),("融通","柔軟性")
    ]
    antonym_pairs = [
        ("善良","悪質"),("多忙","暇"),("肯定","否定"),("昇進","降格")
    ]
    for i in range(NUM_VERBAL_TOTAL):
        typ = random.choice(["syn","ant","order","vocab"])
        if typ == "syn":
            w,corr = random.choice(synonym_pairs)
            distractors = ["遅い","弱い","無関心","複雑","おおざっぱ","長い","短い","穏やか"]
            choices = [corr] + random.sample(distractors,3)
            random.shuffle(choices)
            pool.append({
                "id": qid, "section":"verbal",
                "question": f"語の意味に最も近いものを選べ — 「{w}」",
                "choice1": choices[0], "choice2": choices[1], "choice3": choices[2], "choice4": choices[3],
                "answer": choices.index(corr)+1
            })
        elif typ == "ant":
            a,b = random.choice(antonym_pairs)
            correct = b
            distractors = ["多い","少ない","早い","遅い","肯定","否定","強い","弱い"]
            choices = [correct] + random.sample(distractors,3)
            random.shuffle(choices)
            pool.append({
                "id": qid, "section":"verbal",
                "question": f"次の語の反対語として最も適切なものを選べ — 「{a}」",
                "choice1": choices[0], "choice2": choices[1], "choice3": choices[2], "choice4": choices[3],
                "answer": choices.index(correct)+1
            })
        elif typ == "order":
            stems = [
                ("私は計画を立て、","実行に移した。"),
                ("実験の結果を踏まえて","手順を見直した。"),
                ("予算が不足したため","優先順位を変更した。")
            ]
            stem, corr = random.choice(stems)
            distractors = ["しかし失敗した。","その後放置した。","特に変化はなかった。"]
            choices = [corr] + random.sample(distractors,3)
            random.shuffle(choices)
            pool.append({
                "id": qid, "section":"verbal",
                "question": f"次に来る文として最も自然なものを選べ — 「{stem}」",
                "choice1": choices[0], "choice2": choices[1], "choice3": choices[2], "choice4": choices[3],
                "answer": choices.index(corr)+1
            })
        else:
            # vocabulary nuance
            word = random.choice(["明確","簡潔","慎重","革新的","抽象"])
            corr = random.choice(["はっきりしている","短く分かりやすい","注意深い","新しい","概念的"])
            distractors = ["不明瞭","長い","雑な","古い","細かい","確定的","曖昧"]
            choices = [corr] + random.sample(distractors,3)
            random.shuffle(choices)
            pool.append({
                "id": qid, "section":"verbal",
                "question": f"次の語の意味に最も近いものを選べ — 「{word}」",
                "choice1": choices[0], "choice2": choices[1], "choice3": choices[2], "choice4": choices[3],
                "answer": choices.index(corr)+1
            })
        qid += 1

    # Nonverbal (80)
    for i in range(NUM_NONVERBAL_TOTAL):
        typ = random.choice(["ratio","percent","graph","prob","logic"])
        if typ == "ratio":
            a = random.randint(2,12); b = random.randint(1,a-1)
            correct = f"{a}:{b}"
            choices = [correct, f"{b}:{a}", f"{a-b}:{b}", f"{a}:{a-b}"]
            random.shuffle(choices)
            pool.append({
                "id": qid, "section":"nonverbal",
                "question": f"Aが{a}個、Bが{b}個のとき、A:Bは？",
                "choice1": choices[0], "choice2": choices[1], "choice3": choices[2], "choice4": choices[3],
                "answer": choices.index(correct)+1
            })
        elif typ == "percent":
            base = random.choice([1000,1200,1500,2000]); pct = random.choice([10,15,20,25])
            disc = base * pct // 100
            correct = f"{disc}円"
            choices = [correct, f"{base-disc}円", f"{disc+50}円", f"{disc-50}円"]
            random.shuffle(choices)
            pool.append({
                "id": qid, "section":"nonverbal",
                "question": f"{base}円の商品が{pct}%引き。割引額はいくら？",
                "choice1": choices[0], "choice2": choices[1], "choice3": choices[2], "choice4": choices[3],
                "answer": choices.index(correct)+1
            })
        elif typ == "graph":
            days = random.randint(2,5)
            vals = [random.randint(5,60) for _ in range(days)]
            total = sum(vals)
            correct = f"{total}個"
            choices = [correct, f"{total+3}個", f"{total-2}個", f"{max(total-5,1)}個"]
            random.shuffle(choices)
            pool.append({
                "id": qid, "section":"nonverbal",
                "question": f"{days}日間でそれぞれ{', '.join(str(v)+'個' for v in vals)}売れました。合計はいくつ？",
                "choice1": choices[0], "choice2": choices[1], "choice3": choices[2], "choice4": choices[3],
                "answer": choices.index(correct)+1
            })
        elif typ == "prob":
            r = random.randint(1,5); b = random.randint(1,6)
            p = round(r/(r+b)*100,1)
            correct = f"{p}%"
            choices = [correct, f"{round((r+1)/(r+b)*100,1)}%", f"{round((r)/(r+b+1)*100,1)}%", f"{round((r-1)/(r+b)*100 if r>1 else 0,1)}%"]
            random.shuffle(choices)
            pool.append({
                "id": qid, "section":"nonverbal",
                "question": f"袋に赤{r}、青{b}。1個取り出すとき赤が出る確率は？（小数1位％）",
                "choice1": choices[0], "choice2": choices[1], "choice3": choices[2], "choice4": choices[3],
                "answer": choices.index(correct)+1
            })
        else:
            a = random.randint(2,12); b = random.randint(1,a-1)
            correct = str(a+b)
            choices = [correct, str(a*b), str(abs(a-b)), str(max(a,b))]
            random.shuffle(choices)
            pool.append({
                "id": qid, "section":"nonverbal",
                "question": f"Aが{a}個、Bが{b}個。合わせるといくつ？",
                "choice1": choices[0], "choice2": choices[1], "choice3": choices[2], "choice4": choices[3],
                "answer": choices.index(correct)+1
            })
        qid += 1

    df = pd.DataFrame(pool)
    return df

# ---------- Load or build ----------
df_pool = build_problem_pool()

# ---------- UI: start ----------
st.title("🧠 SPI 模擬テスト（本番版）")
st.write("言語35問 + 非言語35問 をランダム出題します（合計70問）。制限時間：%d分" % TIME_LIMIT_MIN)
st.write("※このテストは学習用です。実際のSPI問題のコピーではありません。")

with st.expander("テスト設定（管理者）"):
    st.write(f"問題プール: 言語{len(df_pool[df_pool['section']=='verbal'])} / 非言語{len(df_pool[df_pool['section']=='nonverbal'])}")

name = st.text_input("氏名（必須）")
email = st.text_input("メール（任意）")
start = st.button("テストを開始する")

if "started" not in st.session_state:
    st.session_state.started = False

if start:
    if not name:
        st.warning("氏名を入力してください。")
    else:
        vpool = df_pool[df_pool['section']=='verbal'].sample(frac=1, random_state=random.randint(1,999999))
        npool = df_pool[df_pool['section']=='nonverbal'].sample(frac=1, random_state=random.randint(1,999999))
        vpick = vpool.iloc[:NUM_VERBAL_PICK] if len(vpool)>=NUM_VERBAL_PICK else vpool
        npick = npool.iloc[:NUM_NONVERBAL_PICK] if len(npool)>=NUM_NONVERBAL_PICK else npool
        picked = pd.concat([vpick, npick]).sample(frac=1, random_state=random.randint(1,999999)).reset_index(drop=True)
        st.session_state.questions = picked.to_dict(orient="records")
        st.session_state.current = 0
        st.session_state.answers = [None]*len(st.session_state.questions)
        st.session_state.correct = [False]*len(st.session_state.questions)
        st.session_state.started = True
        st.session_state.start_time = time.time()
        st.session_state.time_limit = TIME_LIMIT_MIN * 60
        st.session_state.name = name
        st.session_state.email = email

# ---------- During test ----------
if st.session_state.started:
    qlist = st.session_state.questions
    idx = st.session_state.current
    total_q = len(qlist)
    elapsed = time.time() - st.session_state.start_time
    remaining = max(0, st.session_state.time_limit - elapsed)
    mins = int(remaining//60); secs = int(remaining%60)
    st.metric("残り時間", f"{mins}分{secs}秒")
    st.progress((idx)/total_q)

    q = qlist[idx]
    st.subheader(f"Q{idx+1}/{total_q}  （{q['section']}）")
    st.write(q['question'])
    opts = [q['choice1'], q['choice2'], q['choice3'], q['choice4']]
    key = f"q_{idx}"
    default = st.session_state.answers[idx] if isinstance(st.session_state.answers[idx], int) else 0
    sel = st.radio("選択肢を選んでください", opts, index=default, key=key)

    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("前へ"):
            if idx>0:
                st.session_state.current -= 1
                st.experimental_rerun()
    with col2:
        if st.button("次へ"):
            sel_idx = opts.index(sel)
            st.session_state.answers[idx] = sel_idx
            st.session_state.correct[idx] = (sel_idx+1 == int(q['answer']))
            if st.session_state.current < total_q-1:
                st.session_state.current += 1
                st.experimental_rerun()
    with col3:
        if st.button("提出して採点"):
            st.session_state.started = False
            st.experimental_rerun()

    if remaining <= 0:
        st.warning("時間切れです。自動で採点します。")
        st.session_state.started = False
        st.experimental_rerun()

    st.write(f"回答済み: {sum(1 for a in st.session_state.answers if a is not None)} / {total_q}")

# ---------- Result ----------
if (not st.session_state.started) and ("questions" in st.session_state):
    qlist = st.session_state.questions
    total_q = len(qlist)
    corrects = sum(1 for c in st.session_state.correct if c)
    dfq = pd.DataFrame(qlist)
    dfq['correct'] = st.session_state.correct
    verbal_correct = int(dfq[dfq['section']=='verbal']['correct'].sum())
    nonverbal_correct = int(dfq[dfq['section']=='nonverbal']['correct'].sum())
    total_pct = (corrects/total_q)*100 if total_q>0 else 0

    # compute T-score from history if possible
    t_score = None
    hist_n = 0
    client = get_gsheet_client()
    if client:
        hist = fetch_history_total_pct(client, SHEET_URL)
        if len(hist) >= 20:
            mean = np.mean(hist); sd = np.std(hist, ddof=0)
            if sd > 0:
                t_score = 50 + 10 * ((total_pct - mean)/sd)
                hist_n = len(hist)

    if t_score is None:
        sim = np.random.normal(60,12,size=1000)
        t_score = 50 + 10 * ((total_pct - sim.mean())/sim.std(ddof=0))

    st.header("✅ 結果")
    st.write(f"氏名: {st.session_state.get('name','(非登録)')}")
    st.write(f"メール: {st.session_state.get('email','')}")
    st.write(f"言語: {verbal_correct} / {NUM_VERBAL_PICK} ({verbal_correct/NUM_VERBAL_PICK*100:.1f}%)")
    st.write(f"非言語: {nonverbal_correct} / {NUM_NONVERBAL_PICK} ({nonverbal_correct/NUM_NONVERBAL_PICK*100:.1f}%)")
    st.write(f"総合: {corrects} / {total_q} ({total_pct:.1f}%)")
    st.write(f"偏差値（参考）: T = {t_score:.1f}")
    if hist_n>0:
        st.write(f"(シート内の過去{hist_n}件を基に算出)")

    # histogram
    hist_data = hist if (client and len(hist)>=1) else np.random.normal(60,12,1000)
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.hist(hist_data, bins=30)
    ax.axvline(total_pct, color='r', linestyle='--', label=f"あなた: {total_pct:.1f}%")
    ax.set_xlabel("正答率 (%)")
    ax.legend()
    st.pyplot(fig)

    # prepare row to save
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    answers_verbal = ";".join(str(a+1) if a is not None else "" for i,a in enumerate(st.session_state.answers) if qlist[i]['section']=='verbal')
    answers_nonverbal = ";".join(str(a+1) if a is not None else "" for i,a in enumerate(st.session_state.answers) if qlist[i]['section']=='nonverbal')
    row = [
        timestamp,
        st.session_state.get('name',''),
        st.session_state.get('email',''),
        verbal_correct,
        NUM_VERBAL_PICK,
        nonverbal_correct,
        NUM_NONVERBAL_PICK,
        corrects,
        total_q,
        round(total_pct,1),
        round(t_score,1),
        answers_verbal,
        answers_nonverbal
    ]

    if client:
        ok, err = append_row_safe(client, SHEET_URL, row)
        if ok:
            st.success("✅ 結果をスプレッドシートに記録しました。")
        else:
            st.error(f"スプレッドシート保存に失敗しました: {err}")
    else:
        st.info("スプレッドシートに接続できません。結果は画面で確認してください。")

    if st.button("もう一度受ける"):
        for k in ["questions","current","answers","correct","started","start_time","time_limit","name","email"]:
            if k in st.session_state: del st.session_state[k]
        st.experimental_rerun()
