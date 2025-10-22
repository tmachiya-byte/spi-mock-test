import streamlit as st
import random
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# Google Sheets 連携設定
scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["google"], scopes=scope)
gc = gspread.authorize(credentials)
sheet = gc.open_by_url("https://docs.google.com/spreadsheets/d/17cM5v1-ejrYmycHJbuGsJhlGGzTX3g_spXj1YFIOOiM/edit?usp=sharing").sheet1

st.title("🧭 SPI模擬試験（本番体験版）")

# 受験者情報
st.header("受験者情報を入力してください")
name = st.text_input("氏名")
email = st.text_input("メールアドレス（任意）")

# 問題データ（ここでは仮の問題を例示。後で160問入れる）
verbal_questions = [
    {"q": "「迅速」の意味は？", "options": ["早い", "遅い", "静か", "強い"], "a": "早い"},
    {"q": "「堅実」の意味は？", "options": ["派手", "確実", "弱い", "粗い"], "a": "確実"},
]

math_questions = [
    {"q": "3×8÷4＝？", "options": ["6", "8", "9", "12"], "a": "6"},
    {"q": "25%を小数で表すと？", "options": ["0.2", "0.25", "0.3", "2.5"], "a": "0.25"},
]

# ランダム抽出（各35問に後で拡張）
questions = random.sample(verbal_questions, len(verbal_questions)) + random.sample(math_questions, len(math_questions))
random.shuffle(questions)

# 回答セクション
st.header("試験開始")
answers = []
for i, q in enumerate(questions, 1):
    st.subheader(f"第{i}問：{q['q']}")
    answer = st.radio("選択肢を選んでください", q["options"], key=i)
    answers.append({"question": q["q"], "answer": answer, "correct": q["a"]})

# 提出
if st.button("提出する"):
    correct_count = sum([a["answer"] == a["correct"] for a in answers])
    total = len(answers)
    score = int((correct_count / total) * 100)

    st.success(f"お疲れさまでした！正答率：{score}%（{correct_count}/{total}問）")

    # Google Sheetsに記録
    sheet.append_row([
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        name,
        email,
        score,
        correct_count,
        total
    ])
    st.info("結果をスプレッドシートに記録しました。")
