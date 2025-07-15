# 駅周辺の学校検索・可視化ツール

## 概要

指定した鉄道駅の周辺にある中学校および高等学校を検索し，その結果を地図上で視覚的に確認するためのツール群.

一連のスクリプトを実行することで，以下の処理を自動的に行う．
1.  テキストファイルに列挙した駅名から，緯度・経度情報を取得する．
2.  各駅を中心とした指定半径（デフォルト800m=徒歩 10 分（不動産の表示に関する公正競争規約））内に存在する中学校・高等学校・大学を検索する．
3.  駅，指定半径の円，および範囲内の学校をGoogle Earthなどで表示可能なKMLファイルとして出力する．

## 動作要件

*   Python 3.8以上
*   必要なライブラリは `requirements.txt` を参照．

## セットアップ

1.  **Python仮想環境の作成と有効化（推奨）:**
    ```bash
    python -m venv venv
    # Windows
    .\venv\Scripts\activate
    # macOS / Linux
    source venv/bin/activate
    ```

2.  **必要なライブラリのインストール:**
    ```bash
    pip install -r requirements.txt
    ```

## 使い方

### Step 1: 駅の座標を取得する

1.  プロジェクトのルートにある `駅名.txt` ファイルを編集し，座標を取得したい駅名を1行に1つずつ記述する．

    **`駅名.txt` の例:**
    ```
    梅田
    京都
    三ノ宮
    ```

2.  以下のコマンドを実行する．
    ```bash
    python get_station_loc.py
    ```

    これにより `駅名.txt` が読み込まれ，[Overpass API](https://overpass-api.de/) に問い合わせて各駅の緯度・経度を取得する．
    成功すると，結果が `station_coordinates_157.csv` という名前のCSVファイルに出力される．
    157は[大阪メトロ公式駅数](https://subway.osakametro.co.jp/guide/routemap.php)に表示されている駅数．
    （提供してもらったcsv内の全駅数は170駅）

    * スクリプトは関西地方（大阪府, 京都府, 奈良県, 兵庫県）の駅を対象としている．`get_station_loc.py` 内の `PREFECTURES` 定数を編集することで対象地域を変更可能．

### Step 2: 駅周辺の学校を検索する

次に，Step 1で取得した駅の座標を基に，周辺の学校を検索する．

    ```bash
    python find_schools_within_radius.py
    ```
このスクリプトは，`station_coordinates_157.csv` を読み込み，各駅の半径800m以内にある中学校・高等学校・大学を検索する．検索はデフォルトでOverpass APIをリアルタイムで利用する（`--live` モード）．

*   **主なオプション:**
    *   `-s, --stations`: 駅座標が記載されたCSVファイルを指定する．（デフォルト: `station_coordinates_157.csv`）
    *   `-r, --radius`: 検索半径をメートル単位で指定する．（デフォルト: `800.0`）
    *   `-o, --outfile`: 出力するCSVファイル名を指定する．（デフォルト: `schools_within_{半径}m.csv`）
    *   `--live`: Overpass APIを使用してリアルタイムで学校情報を取得する．
    *   `-c, --schools`: 事前に用意した学校の座標CSVファイルを使い，オフラインで検索を実行する．（今回は未実装）

成功すると，結果が `schools_within_800m.csv` のようなファイル名で出力される．

### Step 3: KMLファイルを生成して結果を可視化する

ここまでの結果を地図上で確認するためのKMLファイルを生成する．

```bash
python build_station_school_kml.py
```

このスクリプトは `station_coordinates_157.csv` と `schools_within_800m.csv` を読み込み，以下の要素を含む `stations_schools_800m.kml` を生成する．

*   **駅のピン:** 赤いピン
*   **検索範囲の円:** 各駅を中心とした半透明な青い円．
*   **学校のピン:** 黄色いピン．クリックで最寄り駅からの距離を確認可能．

*   **主なオプション:**
    *   `-s, --stations`: 駅座標CSVファイルを指定．
    *   `-w, --within`: `find_schools_within_radius.py` が出力した学校リストCSVを指定．
    *   `-o, --outfile`: 出力KMLファイル名を指定．
    *   `-r, --radius`: KMLに描画する円の半径を指定．

---

## 各ファイルの概要まとめ

*   `get_station_loc.py`:
    *   `駅名.txt` から駅名リストを読み込み，Overpass APIを介して緯度・経度を取得し，CSVとして保存する．

*   `find_schools_within_radius.py`:
    *   駅の座標リストを基に，周辺（デフォルト半径800m）にある中学校・高等学校を検索する．
    *   `--live` オプション（デフォルト）では，Overpass APIにリアルタイムで問い合わせを行う．
    *   `is_target_name()` 関数で，施設名に「中学校」または「高等学校」が含まれるかを判定する．

*   `build_station_school_kml.py`:
    *   `simplekml` ライブラリを使用し，駅，検索範囲の円，範囲内の学校の位置情報を含んだKMLファイルを生成する．
    *   アイコンのスタイルや円の透過度などを設定し，視覚的に分かりやすい地図を作成する．

*   `駅名.txt`:
    *   座標を検索したい駅名を記述する入力ファイル．

*   `station_coordinates_157.csv`:
    *   `get_station_loc.py` の出力．駅名と緯度・経度が含まれる．

*   `schools_within_800m.csv`:
    *   `find_schools_within_radius.py` の出力．駅名，学校名，駅からの距離，学校の緯度・経度が含まれる．

*   `results.kml` / `stations_schools_800m.kml`:
    *   `build_station_school_kml.py` の出力．Google Earthなどで表示可能な最終成果物．

*   `requirements.txt`:
    *   プロジェクトの実行に必要なPythonライブラリのリスト．
