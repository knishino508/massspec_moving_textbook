
# 質量分析'動く'教科書

質量分析データ（Parquet形式）を読み込んでスペクトルに関する理解を深めることができます。

## 特徴
- mzMLファイルをParquet形式に変換
- クロマトグラムとMSスペクトルの関係性
- MSスペクトルを拡大して、同位体や分解能を理解
- MS1/MS2スペクトルの可視化

## クイックスタート

1. このページの右側にある「Release and Demo date」から.exeファイルとデモデータをダウンロード
2. ダウンロード後に`Massspec_moving_textbook.exe`を実行
3. 起動したらデモデータ`AminoAcid_DDA.parquet`を読み込み
4. 各タブのデータ表示をクリックし、カーソルの右左で操作

## 開発者向けセットアップ

### 必要環境
- Python 3.8+
- Windows

### インストール方法
```bash
git clone https://github.com/knishino508/massspec_moving_textbook.git
cd massspec_moving_textbook
pip install -r requirements.txt
python src/main.py
```
