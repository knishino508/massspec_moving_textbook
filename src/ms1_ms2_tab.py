import pandas as pd
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import ScalarFormatter
from matplotlib.gridspec import GridSpec

import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Yu Gothic'

class MS1MS2Tab(QWidget):
    def __init__(self):
        super().__init__()
        self.df = None
        self.current_scan = None
        self.all_scans = []
        self.scan_line = None
        self.ms2_shading_ms1 = None
        self.ms2_shading_ms2 = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI要素の初期化"""
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        
        layout = QVBoxLayout(self)
        
        # コントロールパネル
        control_layout = QHBoxLayout()
        
        self.status_label = QLabel("データが読み込まれていません")
        self.process_button = QPushButton("データ表示")
        self.process_button.clicked.connect(self.process_data)
        self.process_button.setEnabled(False)
        
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()
        control_layout.addWidget(self.process_button)
        
        layout.addLayout(control_layout)
        
        # メインエリア：左側に説明文、右側にプロット
        main_layout = QHBoxLayout()
        
        # 左側：説明文エリア（全体の1/4）
        self.create_description_area()
        main_layout.addWidget(self.description_widget, 1)  # 比率1
        
        # 右側：プロットエリア（全体の3/4）
        plot_widget = QWidget()
        plot_layout = QVBoxLayout(plot_widget)
        
        # 図全体を作成
        self.figure = Figure(figsize=(9, 10))  # 横幅をさらに調整
        self.canvas = FigureCanvas(self.figure)

        # 3行 × 1列のグリッドを用意
        gs = GridSpec(3, 1, figure=self.figure, left=0.07, 
                      height_ratios=[1, 1.5, 1.5],
                      hspace=0.55,
                      top = 0.95,
                      bottom = 0.08)

        # 上段：クロマトグラム
        self.ax_chrom = self.figure.add_subplot(gs[0, :])
        
        # 中段：MS1スペクトル
        self.ax_ms1 = self.figure.add_subplot(gs[1, 0])
        
        # 下段：MS2スペクトル
        self.ax_ms2 = self.figure.add_subplot(gs[2, 0])
        
        plot_layout.addWidget(self.canvas)
        main_layout.addWidget(plot_widget, 3)  # 比率3
        
        layout.addLayout(main_layout)
        
        # 初期状態の表示
        self.show_initial_plots()
        
        # イベント接続
        self.canvas.mpl_connect("button_press_event", self.on_click)
        
    def create_description_area(self):
        """説明文エリアを作成"""
        from PySide6.QtWidgets import QTextEdit
        from PySide6.QtCore import Qt
        
        self.description_widget = QWidget()
        desc_layout = QVBoxLayout(self.description_widget)
        
        # タイトル
        title_label = QLabel("MS1/MS2 スペクトル表示")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #2c3e50;")
        desc_layout.addWidget(title_label)
        
        # 説明文
        description_text = QTextEdit()
        description_text.setReadOnly(True)
        description_text.setMaximumHeight(600)
        
        # 説明文の内容（ここを編集してください）
        description_content = """
<h3>使用方法</h3>
<p><b>1. データ処理</b><br>
「データ読み込み」タブでparqetファイルを読み込み「データ表示」をクリック</p>

<p><b>2. スペクトル表示</b><br>
クロマトグラム上をクリックすると、そのスキャンのスペクトルが表示されます。</p>

<p><b>3. キーボード操作</b><br>
← → キーでスキャン間を移動できます。</p>

<h3>表示内容</h3>
<p><b>上段:</b> クロマトグラム（全MS強度）<br>
<b>中段:</b> MS1スペクトル（青色）<br>
<b>下段:</b> MS2スペクトル（黒色）</p>

<h3>ハイライトの説明</h3>
• MS1スペクトルの<span style="background-color: yellow;">黄色</span>はIsolation Windowの幅です。<br>
• MS2スペクトルの<span style="background-color: red; color: white;">赤色</span>はPrecursor ionです。</p>

<h3>Y軸スケール</h3>
<p>• <b>クロマトグラム:</b> 固定スケール<br>
• <b>MS1:</b> 固定スケール（比較用）<br>
• <b>MS2:</b> 可変スケール（各スペクトルの最大値に自動調整）</p>

<h3>特徴</h3>
<p>• スペクトルは同レベルの次のスペクトルまで保持<br>
• m/z < 200 のデータのみ表示</p>
        """
        
        description_text.setHtml(description_content)
        description_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                padding: 10px;
                font-size: 11px;
            }
        """)
        
        desc_layout.addWidget(description_text)
        desc_layout.addStretch()
        
    def show_initial_plots(self):
        """初期状態のプロット表示"""
        self.ax_chrom.text(0.5, 0.5, 'データを表示してください', 
                          ha='center', va='center', transform=self.ax_chrom.transAxes,
                          fontsize=14)
        self.ax_chrom.set_title("クロマトグラム（Scan number、Intensity）")
        
        self.ax_ms1.text(0.5, 0.5, 'データなし', 
                        ha='center', va='center', transform=self.ax_ms1.transAxes)
        self.ax_ms1.set_title("MS1 Spectrum")
        
        self.ax_ms2.text(0.5, 0.5, 'データなし', 
                        ha='center', va='center', transform=self.ax_ms2.transAxes)
        self.ax_ms2.set_title("MS2 Spectrum")
        
        self.figure.subplots_adjust(left = 0.07)
        self.canvas.draw()
        
    def set_data(self, df):
        """外部からデータをセット"""
        self.df = df.copy()
        self.status_label.setText(f"データ受信完了 ({len(df)} 行) - MS1/MS2データを処理してください")
        self.process_button.setEnabled(True)
        
    def process_data(self):
        """MS1/MS2データの処理"""
        if self.df is None:
            QtWidgets.QMessageBox.warning(self, "警告", "データが読み込まれていません")
            return
            
        try:
            # 必要な列の確認
            required_cols = {"scan_number", "intensity", "ms_level", "mz"}
            if not required_cols.issubset(self.df.columns):
                QtWidgets.QMessageBox.critical(self, "エラー", 
                                             f"必要な列が見つかりません: {required_cols}")
                return

            
            # クロマトグラムの作成
            chrom_df = self.df.groupby("scan_number")["intensity"].sum().reset_index()
            chrom_df = chrom_df.sort_values("scan_number")
            self.all_scans = chrom_df["scan_number"].tolist()

            # Y軸の最大値を事前に計算して固定
            self.chrom_max_intensity = chrom_df["intensity"].max() * 1.05  # 5%マージン

            # MS2は可変にするため、ここでは設定しない

            self.ax_chrom.clear()
            self.ax_chrom.plot(chrom_df["scan_number"], chrom_df["intensity"], color="black")
            self.ax_chrom.set_title("Chromatogram (All MS Levels)", fontsize = 10)
            self.ax_chrom.set_xlabel("Scan Number")
            self.ax_chrom.set_ylabel("Total Intensity")
            self.ax_chrom.grid(True)
            self.ax_chrom.set_ylim(0, self.chrom_max_intensity)  # Y軸固定

            # m/z範囲の設定
            ms1_data = self.df[self.df['ms_level'] == 1]
            if not ms1_data.empty:
                self.all_mz_min = ms1_data['mz'].min() - 10
                self.all_mz_max = ms1_data['mz'].max() + 10
            else:
                # PRMデータなどMS1がない場合は全データから計算
                self.all_mz_min = self.df['mz'].min() - 10
                self.all_mz_max = self.df['mz'].max() + 10


            # 科学的記数法のフォーマッタ
            formatter = ScalarFormatter(useMathText=True)
            formatter.set_scientific(True)
            formatter.set_powerlimits((-3, 3))
            self.ax_chrom.yaxis.set_major_formatter(formatter)

            # 初期のスペクトルプロット設定
            self.setup_spectrum_plots()

            self.figure.subplots_adjust(left=0.07)
            self.canvas.draw()

            self.status_label.setText(f"処理完了 - スキャン数: {len(self.all_scans)} (クロマトグラムをクリックしてください)")

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "処理エラー", f"データの処理中にエラーが発生しました:\n{str(e)}")
            
    def setup_spectrum_plots(self):
        """スペクトルプロットの初期設定"""
        self.ax_ms1.clear()
        self.ax_ms1.set_title("MS1 Spectrum", fontsize=10)
        self.ax_ms1.set_xlabel("m/z", fontsize=5)
        self.ax_ms1.set_ylabel("Intensity")
        self.ax_ms1.grid(True)
        
        self.ax_ms2.clear()
        self.ax_ms2.set_title("MS2 Spectrum", fontsize=10)
        self.ax_ms2.set_xlabel("m/z", fontsize=5)
        self.ax_ms2.set_ylabel("Intensity")
        self.ax_ms2.grid(True)

    def keyPressEvent(self, event):
        """キー操作でスキャン移動"""
        if self.current_scan is None or not self.all_scans:
            return
        idx = self.all_scans.index(self.current_scan)
        if event.key() == QtCore.Qt.Key_Left and idx > 0:
            self.update_scan(self.all_scans[idx - 1])
        elif event.key() == QtCore.Qt.Key_Right and idx < len(self.all_scans) - 1:
            self.update_scan(self.all_scans[idx + 1])

    def safe_remove_artist(self, artist):
        """アーティストを安全に削除する関数"""
        if artist is not None:
            try:
                artist.remove()
            except (NotImplementedError, ValueError):
                pass
        return None

    def find_ms1_scan(self, target_scan):
        """指定されたスキャン以下で最初に見つかるMS1スキャンを返す"""
        candidate_scans = [scan for scan in self.all_scans if scan <= target_scan]
        candidate_scans.sort(reverse=True)
        
        for scan in candidate_scans:
            scan_data = self.df[self.df['scan_number'] == scan]
            ms1_data = scan_data[scan_data['ms_level'] == 1]
            if not ms1_data.empty:
                return scan
        
        return None

    def on_click(self, event):
        """クロマトグラムクリック時の処理"""
        if self.df is None or event.inaxes != self.ax_chrom:
            return
        x_clicked = event.xdata
        if x_clicked is None:
            return
        if not self.all_scans:
            return
            
        nearest_scan = round(x_clicked)
        
        # 存在しないスキャン番号の場合は最も近いものを選ぶ
        if nearest_scan not in self.all_scans:
            nearest_scan = min(self.all_scans, key=lambda x: abs(x - nearest_scan))
        
        # シンプルにクリックしたスキャンの表示を更新
        self.update_scan(nearest_scan)

    def update_scan_with_ms1_priority(self, clicked_scan, ms1_scan):
        """クリックしたスキャンとMS1スキャンを使って表示を更新"""
        self.current_scan = clicked_scan
        
        # クリックしたスキャンのMS2データを取得
        clicked_spec_data = self.df[self.df['scan_number'] == clicked_scan]
        ms2_data = clicked_spec_data[clicked_spec_data['ms_level'] == 2]
        
        # MS1スキャンのMS1データを取得（MS1スキャンが存在する場合のみ）
        ms1_data = pd.DataFrame()
        if ms1_scan is not None:
            ms1_spec_data = self.df[self.df['scan_number'] == ms1_scan]
            ms1_data = ms1_spec_data[ms1_spec_data['ms_level'] == 1]

        # 赤い縦線の更新（クリックした位置）
        self.scan_line = self.safe_remove_artist(self.scan_line)
        self.scan_line = self.ax_chrom.axvline(clicked_scan, color='red', linestyle='--', linewidth=1)

        # MS1の更新
        if not ms1_data.empty:
            self.ax_ms1.clear()
            self.ax_ms1.set_title(f"MS1 Spectrum - Scan {ms1_scan}", fontsize=10)
            self.ax_ms1.set_xlabel("m/z", fontsize=10)
            self.ax_ms1.set_ylabel("Intensity")
            self.ax_ms1.grid(True)
            self.ax_ms1.vlines(ms1_data['mz'], 0, ms1_data['intensity'], color='blue', linewidth=1, alpha=0.7)
            self.ax_ms1.set_xlim(self.all_mz_min, self.all_mz_max)
            self.ax_ms1.set_ylim(0, 1e7)
        else:
            # MS1データが存在しない場合（PRMデータなど）
            self.ax_ms1.clear()
            self.ax_ms1.set_title("MS1 Spectrum - No MS1 data available", fontsize=10)
            self.ax_ms1.set_xlabel("m/z", fontsize=10)
            self.ax_ms1.set_ylabel("Intensity")
            self.ax_ms1.grid(True)
            self.ax_ms1.set_xlim(self.all_mz_min, self.all_mz_max)

        # MS2ハイライトを消す（元のスクリプトと同じタイミング）
        self.ms2_shading_ms1 = self.safe_remove_artist(self.ms2_shading_ms1)

        # MS2の更新と Precursor m/z 塗りつぶし
        if not ms2_data.empty:
            self.ax_ms2.clear()
            self.ax_ms2.set_title(f"MS2 Spectrum - Scan {clicked_scan}", fontsize=10)
            self.ax_ms2.set_xlabel("m/z", fontsize=10)
            self.ax_ms2.set_ylabel("Intensity")
            self.ax_ms2.grid(True)
            self.ax_ms2.vlines(ms2_data['mz'], 0, ms2_data['intensity'], color='black', linewidth=1, alpha=0.7)
            self.ax_ms2.set_xlim(self.all_mz_min, self.all_mz_max)

            # プリカーサーm/zのハイライト処理
            if 'precursor_mz' in ms2_data.columns:
                precursor_mz = ms2_data['precursor_mz'].iloc[0]
                mz_min = precursor_mz - 1.5
                mz_max = precursor_mz + 1.5

                # MS2スペクトルにハイライト追加
                self.ms2_shading_ms2 = self.ax_ms2.axvspan(
                    mz_min+1.45, mz_max-1.45, color='red', alpha=1
                )

                # MS1データがある場合のみMS1スペクトルにもハイライト追加
                if not ms1_data.empty:
                    self.ms2_shading_ms1 = self.ax_ms1.axvspan(
                        mz_min, mz_max, color='yellow', alpha=0.8
                    )
        else:
            # MS2データがない場合はMS2プロットをクリア
            self.ax_ms2.clear()
            self.ax_ms2.set_title(f"MS2 Spectrum - Scan {clicked_scan} (No MS2 data)")
            self.ax_ms2.set_xlabel("m/z")
            self.ax_ms2.set_ylabel("Intensity")
            self.ax_ms2.grid(True)
            self.ax_ms2.set_xlim(self.all_mz_min, self.all_mz_max)

        self.figure.subplots_adjust(left=0.07)
        self.canvas.draw()
        
        # ステータス更新
        ms1_info = f"MS1: Scan {ms1_scan}" if ms1_scan else "MS1: なし"
        ms2_info = f"MS2: Scan {clicked_scan}" if not ms2_data.empty else "MS2: なし"
        self.status_label.setText(f"{ms1_info}, {ms2_info} (←→キーで移動可能)")

    def update_scan(self, scan_number):
        """クリックしたスキャンの表示を更新"""
        self.current_scan = scan_number
        spec_data = self.df[self.df['scan_number'] == scan_number]
        ms1_data = spec_data[spec_data['ms_level'] == 1]
        ms2_data = spec_data[spec_data['ms_level'] == 2]

        # 赤い縦線の更新
        self.scan_line = self.safe_remove_artist(self.scan_line)
        self.scan_line = self.ax_chrom.axvline(scan_number, color='red', linestyle='--', linewidth=1)

        # MS1の更新（MS1データがある場合のみ更新）
        if not ms1_data.empty:
            # MS1ハイライトを削除してからMS1スペクトルを更新
            self.ms2_shading_ms1 = self.safe_remove_artist(self.ms2_shading_ms1)

            #Y軸は各Scanデータの最大Intensityの25％程度にして、ノイズを取り込んでる様子を可視化
            self.ms1_max_intensity = ms1_data['intensity'].max() / 10

            self.ax_ms1.clear()
            self.ax_ms1.set_title(f"MS1 Spectrum - Scan {scan_number}")
            self.ax_ms1.set_xlabel("m/z")
            self.ax_ms1.set_ylabel("Intensity")
            self.ax_ms1.grid(True)
            self.ax_ms1.vlines(ms1_data['mz'], 0, ms1_data['intensity'], color='blue', linewidth=1, alpha=0.7)
            self.ax_ms1.set_xlim(self.all_mz_min, self.all_mz_max)
            self.ax_ms1.set_ylim(0, self.ms1_max_intensity)  # 固定Y軸
            
            # MS1のY軸も科学的記数法に統一
            ms1_formatter = ScalarFormatter(useMathText=True)
            ms1_formatter.set_scientific(True)
            ms1_formatter.set_powerlimits((-3, 3))
            self.ax_ms1.yaxis.set_major_formatter(ms1_formatter)

        # MS2の更新（MS2データがある場合のみ更新）
        if not ms2_data.empty:
            # MS2ハイライトを削除してからMS2スペクトルを更新
            self.ms2_shading_ms2 = self.safe_remove_artist(self.ms2_shading_ms2)
            self.ms2_mz_min = ms2_data['mz'].min()-10
            self.ms2_mz_max = ms2_data['mz'].max()+10

            self.ax_ms2.clear()
            self.ax_ms2.set_title(f"MS2 Spectrum - Scan {scan_number}")
            self.ax_ms2.set_xlabel("m/z")
            self.ax_ms2.set_ylabel("Intensity")
            self.ax_ms2.grid(True)
            self.ax_ms2.vlines(ms2_data['mz'], 0, ms2_data['intensity'], color='black', linewidth=1, alpha=0.7)
            self.ax_ms2.set_xlim(self.ms2_mz_min, self.ms2_mz_max)
            
            # MS2は現在のスペクトルに応じて可変Y軸
            current_ms2_max = ms2_data['intensity'].max() * 1.05  # 5%マージン
            self.ax_ms2.set_ylim(0, current_ms2_max)
            
            # MS2のY軸を科学的記数法に統一
            ms2_formatter = ScalarFormatter(useMathText=True)
            ms2_formatter.set_scientific(True)
            ms2_formatter.set_powerlimits((-3, 3))
            self.ax_ms2.yaxis.set_major_formatter(ms2_formatter)

            # プリカーサーm/zのハイライト
            if 'precursor_mz' in ms2_data.columns:
                precursor_mz = ms2_data['precursor_mz'].iloc[0]
                mz_min = precursor_mz - 1.5
                mz_max = precursor_mz + 1.5

                # MS2スペクトルにハイライト
                self.ms2_shading_ms2 = self.ax_ms2.axvspan(
                    mz_min+1.45, mz_max-1.45, color='red', alpha=1
                )

                # 現在表示されているMS1スペクトルがある場合のみハイライト追加
                if self.ax_ms1.get_title() and "No MS1 data" not in self.ax_ms1.get_title():
                    self.ms2_shading_ms1 = self.ax_ms1.axvspan(
                        mz_min, mz_max, color='yellow', alpha=0.8
                    )

        self.figure.subplots_adjust(left=0.07)
        self.canvas.draw()
        
        # ステータス更新
        ms1_info = "MS1: 新規表示" if not ms1_data.empty else "MS1: 保持"
        ms2_info = "MS2: 新規表示" if not ms2_data.empty else "MS2: 保持"
        self.status_label.setText(f"Scan {scan_number} - {ms1_info}, {ms2_info} (←→キーで移動可能)")