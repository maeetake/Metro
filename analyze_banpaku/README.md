# 交通データ分析スクリプト

日付ソート済み交通乗降客データ (`sorted_output.csv`) を分析し，万博来場者数との相関を探る．

## 共通データ

以下のCSVファイルを入力とする．

- `sorted_output.csv`: 乗降客の移動記録データ．

---

## スクリプト詳細

### 1. `fig_yumeshima.py`

#### 目的
「なかもず」駅と「夢洲」駅間の1日ごとの利用者数を方向別に集計し、その推移を折れ線グラフで可視化する．

#### 処理フロー
1. `pandas` を使用して `sorted_output.csv` を読み込む．
2. 「なかもず → 夢洲」および「夢洲 → なかもず」の双方向のデータを抽出する．
3. 日付ごとに利用者数を集計する．
4. `matplotlib` を用いて、両方向の利用者数推移を一つのグラフに描画する．

#### 実行方法
```bash
python fig_yumeshima.py
```

---

### 2. `figs_nakamozu_pairs.py`

#### 目的
「なかもず」駅と、データ内に存在する他のすべての駅との間の1日ごとの利用者数推移を、駅のペアごとにグラフ化し、画像ファイルとして保存する．

#### 処理フロー
1. `pandas` を使用して `sorted_output.csv` を読み込む．
2. データに含まれる全駅から「なかもず」駅を除いたリストを作成する．
3. 各駅に対してループ処理を行い、「なかもず」駅との間の双方向（往路・復路）の利用者数を日付ごとに集計する．利用者数が0人の日もプロット対象となる．
4. `matplotlib` を用いて、各駅ペアの利用者数推移を折れ線グラフとして描画する．
5. 生成されたグラフを `figs_nakamozu_pairs/` ディレクトリ内に `なかもず-{相手駅名}.png` というファイル名で保存する．

#### 実行方法
```bash
python figs_nakamozu_pairs.py
```

#### 出力
`figs_nakamozu_pairs` ディレクトリ（自動作成）に、各駅ペアの利用者数推移を示したPNG画像が生成される．