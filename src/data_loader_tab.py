import pandas as pd
import numpy as np
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                              QLabel, QTableWidget, QTableWidgetItem, QTextEdit,
                              QSplitter, QGroupBox, QFileDialog, QMessageBox,
                              QProgressBar, QCheckBox, QTabWidget, QFrame)
from PySide6.QtCore import Qt, Signal, QThread
import os
from datetime import datetime

# mzML変換に必要なライブラリ
try:
    from pyteomics import mzml
    import pyarrow as pa
    import pyarrow.parquet as pq
    MZML_AVAILABLE = True
except ImportError:
    MZML_AVAILABLE = False

class MzMLConversionThread(QThread):
    """mzML変換を別スレッドで実行するクラス"""
    progress_update = Signal(str)  # ログメッセージ
    conversion_finished = Signal(bool, str)  # 成功/失敗、メッセージ
    
    def __init__(self, mzml_file_path, parquet_file_path):
        super().__init__()
        self.mzml_file_path = mzml_file_path
        self.parquet_file_path = parquet_file_path
        
    def run(self):
        """mzML変換処理"""
        try:
            self.progress_update.emit(f"[{datetime.now().strftime('%H:%M:%S')}] mzML変換開始")
            self.progress_update.emit(f"入力ファイル: {os.path.basename(self.mzml_file_path)}")
            self.progress_update.emit(f"出力ファイル: {os.path.basename(self.parquet_file_path)}")
            
            # データを格納するリスト
            data_list = []
            
            self.progress_update.emit("mzMLファイルを読み込み中...")
            
            # mzMLファイルを読み込む
            with mzml.read(self.mzml_file_path) as reader:
                for spectrum in reader:
                    # スペクトルIDからスキャン番号を取得
                    scan_number = spectrum.get('index', 0)

                    # m/zとIntensityの配列を取得
                    mz_array = spectrum.get('m/z array', [])
                    intensity_array = spectrum.get('intensity array', [])
                    ms_level = spectrum.get('ms level', None)
                    
                    precursor_mz = None

                    if ms_level == 2:
                        precursor_info = spectrum.get('precursorList', {}).get('precursor', [{}])[0]
                        selected_ion = precursor_info.get('selectedIonList', {}).get('selectedIon', [{}])[0]
                        precursor_mz = selected_ion.get('selected ion m/z', None)

                    # 各ピークに対してデータを追加
                    for mz, intensity in zip(mz_array, intensity_array):
                        data_list.append({
                            'scan_number': scan_number,
                            'mz': mz,
                            'intensity': intensity,
                            'ms_level': ms_level,
                            'precursor_mz': precursor_mz
                        })

            self.progress_update.emit(f"総データ数: {len(data_list):,} ピーク")
            
            # DataFrameに変換
            self.progress_update.emit("DataFrameに変換中...")
            df = pd.DataFrame(data_list)
            
            # データ型を最適化
            self.progress_update.emit("データ型を最適化中...")
            df['scan_number'] = df['scan_number'].astype('int32')
            df['mz'] = df['mz'].astype('float64')
            df['intensity'] = df['intensity'].astype('float64')
            df['ms_level'] = df['ms_level'].astype('int32')
            
            # Parquetファイルに保存
            self.progress_update.emit("Parquetファイルに保存中...")
            df.to_parquet(self.parquet_file_path, engine='pyarrow', compression='snappy')
            
            self.progress_update.emit(f"[{datetime.now().strftime('%H:%M:%S')}] 変換完了!")
            self.progress_update.emit(f"保存先: {self.parquet_file_path}")
            self.progress_update.emit(f"ファイルサイズ: {os.path.getsize(self.parquet_file_path) / 1024 / 1024:.1f} MB")
            self.progress_update.emit("-" * 50)
            
            self.conversion_finished.emit(True, "変換が正常に完了しました")
            
        except Exception as e:
            error_msg = f"変換エラー: {str(e)}"
            self.progress_update.emit(f"[{datetime.now().strftime('%H:%M:%S')}] {error_msg}")
            self.progress_update.emit("-" * 50)
            self.conversion_finished.emit(False, error_msg)

class DataLoaderTab(QWidget):
    # データが読み込まれた時に発信するシグナル
    data_loaded = Signal(pd.DataFrame)
    
    def __init__(self):
        super().__init__()
        self.current_data = None
        self.conversion_thread = None
        self.setup_ui()
        
    def setup_ui(self):
        """UI要素の初期化"""
        layout = QVBoxLayout(self)
        
        # === 使い方説明セクション ===
        usage_group = QGroupBox("ソフトウェアの使い方")
        usage_layout = QVBoxLayout(usage_group)
        
        # 使い方テキスト
        usage_text = QTextEdit()
        usage_text.setReadOnly(True)
        usage_text.setMaximumHeight(450)  # 高さを制限
        
        usage_content = """
<b>使用方法 parquetファイル読み込み方法（まずはこっち）</b><br>
1.「paarquetファイルを選択」をクリック<br>
2. デモデータ「AminoAcid_DDA.parquet」ファイルを選択<br>
3. 各タブをクリックして、「データ表示」をクリック<br>
・ Y軸固定・可変タブ：マススペクトルのY軸を可変（左）と固定（右）を比べてクロマトグラムとMSスペクトルの関係性を確認します<br>
・ 拡大表示：マススペクトルを拡大し、同位体や分解能を可視化します<br>
・ DDAの可視化：MS1とMS2の関係性とIsolation windowを可視化します<br>
<br>
<b>使用方法 手持ちのmzMLを読み込む方法</b><br>
1.「mzMLファイルを変換」をクリック<br>
2. 手持ちのmzMLファイルを選択（DDAを想定）<br>
3. 変換完了と読み込みを承認すると、自動で読み込み、以降は同じ<br>
        """
        
        usage_text.setHtml(usage_content)
        usage_text.setStyleSheet("""
            QTextEdit {
                border: 1px solid #bee5eb;
                border-radius: 5px;
                padding: 8px;
                font-size: 11px;
            }
        """)
        
        usage_layout.addWidget(usage_text)
        layout.addWidget(usage_group)
        
        # 区切り線
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)
        
        # === ファイル読み込みセクション ===
        file_group = QGroupBox("ファイル操作")
        file_layout = QVBoxLayout(file_group)
        
        # ファイル選択行
        file_select_layout = QHBoxLayout()
        self.load_button = QPushButton("Parquetファイルを選択")
        self.load_button.clicked.connect(self.select_and_load_file)
        
        # mzML変換ボタン
        self.convert_button = QPushButton("mzMLファイルを変換")
        self.convert_button.clicked.connect(self.select_and_convert_mzml)
        if not MZML_AVAILABLE:
            self.convert_button.setEnabled(False)
            self.convert_button.setToolTip("pyteomicsライブラリがインストールされていません")
        
        self.file_path_label = QLabel("ファイルが選択されていません")
        self.file_path_label.setStyleSheet("color: gray;")
        
        file_select_layout.addWidget(self.load_button)
        file_select_layout.addWidget(self.convert_button)
        file_select_layout.addWidget(self.file_path_label, 1)
        
        # データ最適化オプション
        optimize_layout = QHBoxLayout()
        self.optimize_checkbox = QCheckBox("データ型を最適化する（推奨）")
        self.optimize_checkbox.setChecked(True)
        self.optimize_checkbox.setToolTip(
            "データ型を最適化してメモリ使用量と処理速度を改善します\n"
            "・scan_number: 整数型\n"
            "・mz, precursor_mz: float (小数点5桁)\n"
            "・intensity: 整数型\n"
            "・ms_level: 整数型"
        )
        
        optimize_layout.addWidget(self.optimize_checkbox)
        optimize_layout.addStretch()
        
        file_layout.addLayout(file_select_layout)
        file_layout.addLayout(optimize_layout)
        
        layout.addWidget(file_group)
        
        # プログレスバー（読み込み中表示用）
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # メインエリア（タブ付き）
        main_tabs = QTabWidget()
        
        # データ表示タブ
        data_tab = QWidget()
        data_layout = QVBoxLayout(data_tab)
        
        # データ表示エリア
        splitter = QSplitter(Qt.Horizontal)
        
        # 左側：データ情報とサマリー
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        
        # データ情報
        info_group = QGroupBox("データ情報")
        info_layout = QVBoxLayout(info_group)
        
        self.info_text = QTextEdit()
        self.info_text.setMaximumHeight(80)
        self.info_text.setReadOnly(True)
        info_layout.addWidget(self.info_text)
        
        left_layout.addWidget(info_group)
        
        # データサマリー
        summary_group = QGroupBox("列の統計情報")
        summary_layout = QVBoxLayout(summary_group)
        
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        summary_layout.addWidget(self.summary_text)
        
        left_layout.addWidget(summary_group)
        
        # 右側：データプレビュー
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        
        preview_group = QGroupBox("データプレビュー（最初の100行）")
        preview_layout = QVBoxLayout(preview_group)
        
        self.data_table = QTableWidget()
        preview_layout.addWidget(self.data_table)
        
        right_layout.addWidget(preview_group)
        
        # スプリッターに追加
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setSizes([800, 400])  # 左:右の比率
        
        data_layout.addWidget(splitter)
        main_tabs.addTab(data_tab, "データ表示")
        
        # ログタブ
        log_tab = QWidget()
        log_layout = QVBoxLayout(log_tab)
        
        # ログ表示エリア
        log_group = QGroupBox("変換ログ")
        log_group_layout = QVBoxLayout(log_group)
        
        # ログクリアボタン
        log_controls = QHBoxLayout()
        self.clear_log_button = QPushButton("ログをクリア")
        self.clear_log_button.clicked.connect(self.clear_log)
        log_controls.addWidget(self.clear_log_button)
        log_controls.addStretch()
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QtWidgets.QApplication.font())
        
        log_group_layout.addLayout(log_controls)
        log_group_layout.addWidget(self.log_text)
        
        log_layout.addWidget(log_group)
        main_tabs.addTab(log_tab, "変換ログ")
        
        layout.addWidget(main_tabs)
        
        # 初期メッセージ
        self.show_initial_message()
        
    def show_initial_message(self):
        """初期メッセージを表示"""
        self.info_text.setText("データファイルを選択してください。\n\nサポート形式: Parquet (.parquet)")
        self.summary_text.setText("データが読み込まれると、ここに統計情報が表示されます。")
        
        # 初期ログメッセージ
        if MZML_AVAILABLE:
            self.log_text.append("mzML変換機能が利用可能です。")
        else:
            self.log_text.append("注意: pyteomicsライブラリがインストールされていないため、mzML変換機能は無効です。")
            self.log_text.append("インストール方法: pip install pyteomics pandas pyarrow")
        
    def select_and_load_file(self):
        """ファイル選択ダイアログを開いてファイルを読み込み"""
        fname, _ = QFileDialog.getOpenFileName(
            self, 
            "Parquetファイルを選択", 
            filter="Parquet Files (*.parquet)"
        )
        if fname:
            self.load_file(fname)
            
    def select_and_convert_mzml(self):
        """mzMLファイル選択ダイアログを開いて変換を実行"""
        if not MZML_AVAILABLE:
            QMessageBox.warning(self, "機能無効", "pyteomicsライブラリがインストールされていません。")
            return
            
        fname, _ = QFileDialog.getOpenFileName(
            self, 
            "mzMLファイルを選択", 
            filter="mzML Files (*.mzML)"
        )
        if fname:
            self.convert_mzml_file(fname)
            
    def convert_mzml_file(self, mzml_file_path):
        """mzMLファイルを変換"""
        try:
            # 出力ファイルパスを生成（同じディレクトリ、同じファイル名、拡張子をparquetに変更）
            base_name = os.path.splitext(mzml_file_path)[0]
            parquet_file_path = base_name + ".parquet"
            
            # 変換スレッドを作成して実行
            self.conversion_thread = MzMLConversionThread(mzml_file_path, parquet_file_path)
            self.conversion_thread.progress_update.connect(self.update_log)
            self.conversion_thread.conversion_finished.connect(self.on_conversion_finished)
            
            # UI更新
            self.convert_button.setEnabled(False)
            self.convert_button.setText("変換中...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不定進行
            
            # 変換開始
            self.conversion_thread.start()
            
        except Exception as e:
            QMessageBox.critical(self, "変換エラー", f"変換処理の開始に失敗しました:\n{str(e)}")
            self.convert_button.setEnabled(True)
            self.convert_button.setText("mzMLファイルを変換")
            self.progress_bar.setVisible(False)
            
    def update_log(self, message):
        """ログを更新"""
        self.log_text.append(message)
        # 自動スクロール（より簡単な方法）
        self.log_text.ensureCursorVisible()
        
    def on_conversion_finished(self, success, message):
        """変換完了時の処理"""
        # UI復元
        self.convert_button.setEnabled(True)
        self.convert_button.setText("mzMLファイルを変換")
        self.progress_bar.setVisible(False)
        
        if success:
            QMessageBox.information(self, "変換完了", message)
            # 変換されたファイルを自動読み込みするか確認
            reply = QMessageBox.question(
                self, 
                "ファイル読み込み", 
                "変換されたParquetファイルを読み込みますか？",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                # 変換されたファイルのパスを取得
                parquet_path = self.conversion_thread.parquet_file_path
                self.load_file(parquet_path)
        else:
            QMessageBox.critical(self, "変換失敗", message)
            
    def clear_log(self):
        """ログをクリア"""
        self.log_text.clear()
        self.log_text.append(f"[{datetime.now().strftime('%H:%M:%S')}] ログをクリアしました")
            
    def load_file(self, file_path):
        """指定されたファイルを読み込み"""
        try:
            # プログレスバー表示
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不定進行
            QtWidgets.QApplication.processEvents()
            
            # ファイル読み込み
            self.info_text.setText("ファイルを読み込み中...")
            QtWidgets.QApplication.processEvents()
            
            self.current_data = pd.read_parquet(file_path)
            
            # データ型最適化
            if self.optimize_checkbox.isChecked():
                self.info_text.setText("データ型を最適化中...")
                QtWidgets.QApplication.processEvents()
                
                original_memory = self.current_data.memory_usage(deep=True).sum()
                self.current_data = self.optimize_data_types(self.current_data)
                optimized_memory = self.current_data.memory_usage(deep=True).sum()
                
                memory_reduction = (1 - optimized_memory / original_memory) * 100
                print(f"最適化完了 - メモリ使用量 {memory_reduction:.1f}% 削減")
            
            # UI更新
            self.file_path_label.setText(f"読み込み済み: {os.path.basename(file_path)}")
            self.file_path_label.setStyleSheet("color: green;")
            
            # データ情報表示
            self.display_data_info(file_path)
            
            # データプレビュー表示
            self.display_data_preview()
            
            # データサマリー表示
            self.display_data_summary()
            
            # プログレスバー非表示
            self.progress_bar.setVisible(False)
            
            # シグナル発信
            self.data_loaded.emit(self.current_data)
            
        except Exception as e:
            self.progress_bar.setVisible(False)
            QMessageBox.critical(self, "読み込みエラー", f"ファイルの読み込みに失敗しました:\n{str(e)}")
            self.file_path_label.setText("読み込み失敗")
            self.file_path_label.setStyleSheet("color: red;")
            
    def optimize_data_types(self, df):
        """データ型を最適化"""
        df = df.copy()
        
        # scan_number: 整数型
        if 'scan_number' in df.columns:
            df['scan_number'] = df['scan_number'].astype('int32')
        
        # mz: float32 (小数点5桁)
        if 'mz' in df.columns:
            df['mz'] = df['mz'].round(5).astype('float32')
        
        # intensity: 整数型 (小数点以下切り捨て)
        if 'intensity' in df.columns:
            df['intensity'] = df['intensity'].astype('int64')
        
        # ms_level: 整数型
        if 'ms_level' in df.columns:
            df['ms_level'] = df['ms_level'].astype('int8')
        
        # precursor_mz: float32 (小数点5桁、NaN対応)
        if 'precursor_mz' in df.columns:
            # NaNは保持しつつ、有効な値のみ丸める
            mask = df['precursor_mz'].notna()
            df.loc[mask, 'precursor_mz'] = df.loc[mask, 'precursor_mz'].round(5)
            df['precursor_mz'] = df['precursor_mz'].astype('float32')
        
        return df
            
    def display_data_info(self, file_path):
        """データの基本情報を表示"""
        if self.current_data is None:
            return
            
        info_text = f"""ファイル: {os.path.basename(file_path)}
行数: {len(self.current_data):,}
列数: {len(self.current_data.columns)}
メモリ使用量: {self.current_data.memory_usage(deep=True).sum() / 1024 / 1024:.1f} MB

列名:
{', '.join(self.current_data.columns.tolist())}

データ型:
{self.current_data.dtypes.to_string()}

最適化情報:
"""
        
        if self.optimize_checkbox.isChecked():
            info_text += "✓ データ型最適化が適用されました"
        else:
            info_text += "- データ型最適化は無効です"
        
        self.info_text.setText(info_text)
        
    def display_data_preview(self):
        """データプレビューをテーブルで表示"""
        if self.current_data is None:
            return
            
        # 最初の100行を表示
        preview_data = self.current_data.head(100)
        
        # テーブル設定
        self.data_table.setRowCount(len(preview_data))
        self.data_table.setColumnCount(len(preview_data.columns))
        self.data_table.setHorizontalHeaderLabels(preview_data.columns.tolist())
        
        # データ挿入
        for i, row in enumerate(preview_data.itertuples(index=False)):
            for j, value in enumerate(row):
                item = QTableWidgetItem(str(value))
                self.data_table.setItem(i, j, item)
                
        # 列幅自動調整
        self.data_table.resizeColumnsToContents()
        
    def display_data_summary(self):
        """データの統計サマリーを表示"""
        if self.current_data is None:
            return
            
        try:
            # 数値列の統計情報
            numeric_summary = self.current_data.describe()
            
            # 欠損値情報
            missing_info = self.current_data.isnull().sum()
            missing_info = missing_info[missing_info > 0]
            
            summary_text = "=== 数値列の統計情報 ===\n"
            summary_text += numeric_summary.to_string()
            
            if not missing_info.empty:
                summary_text += "\n\n=== 欠損値情報 ===\n"
                summary_text += missing_info.to_string()
            else:
                summary_text += "\n\n=== 欠損値情報 ===\n欠損値はありません"
                
            # ユニーク値の情報（カテゴリカル列）
            categorical_cols = self.current_data.select_dtypes(include=['object']).columns
            if len(categorical_cols) > 0:
                summary_text += "\n\n=== カテゴリカル列のユニーク値数 ===\n"
                for col in categorical_cols:
                    unique_count = self.current_data[col].nunique()
                    summary_text += f"{col}: {unique_count}\n"
            
            self.summary_text.setText(summary_text)
            
        except Exception as e:
            self.summary_text.setText(f"統計情報の生成中にエラーが発生しました:\n{str(e)}")
            
    def get_current_data(self):
        """現在読み込まれているデータを取得"""
        return self.current_data