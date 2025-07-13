import pandas as pd
import numpy as np
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.ticker import ScalarFormatter
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import FormatStrFormatter

import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Yu Gothic'

class ZoomViewerTab(QWidget):
    def __init__(self):
        super().__init__()
        self.df = None
        self.current_scan = None
        self.all_scans = []
        self.max_spectrum_intensity = 0
        self.max_spectrum_mz_center = 0
        self.scan_line = None
        
        self.setup_ui()
        
    def setup_ui(self):
        """UI要素の初期化"""
        self.setFocusPolicy(QtCore.Qt.StrongFocus)
        
        layout = QVBoxLayout(self)
        
        # コントロールパネル
        control_layout = QHBoxLayout()
        
        self.status_label = QLabel("データが読み込まれていません")
        self.process_button = QPushButton("データ表示")
        self.process_button.clicked.connect(self.process_ms1_data)
        self.process_button.setEnabled(False)
        
        control_layout.addWidget(self.status_label)
        control_layout.addStretch()
        control_layout.addWidget(self.process_button)
        
        layout.addLayout(control_layout)
        
        # Figure & Axes (2段構成)
        self.figure = Figure(figsize=(12, 8))
        self.canvas = FigureCanvas(self.figure)
        
        gs = GridSpec(2, 3, figure=self.figure)

        # 上段：クロマトグラム
        self.ax_chrom = self.figure.add_subplot(2, 1, 1)
        
        # 下段：左・中央・右のMS1スペクトル
        self.ax_ms1_var   = self.figure.add_subplot(gs[1, 0])  # 左
        self.ax_ms1_fixed = self.figure.add_subplot(gs[1, 1])  # 中央
        self.ax_ms1_zoom  = self.figure.add_subplot(gs[1, 2])  # 右
        
        layout.addWidget(self.canvas)
        
        # 初期状態の表示
        self.show_initial_plots()
        
        # イベント接続
        self.canvas.mpl_connect("button_press_event", self.on_click)
        
    def show_initial_plots(self):
        """初期状態のプロット表示"""
        self.ax_chrom.text(0.5, 0.5, 'データを読み込んでください', 
                          ha='center', va='center', transform=self.ax_chrom.transAxes,
                          fontsize=14)
        self.ax_chrom.set_title("MS1 Chromatogram")
        
        self.ax_ms1_var.text(0.5, 0.5, 'データなし', 
                            ha='center', va='center', transform=self.ax_ms1_var.transAxes)
        self.ax_ms1_var.set_title("MS1 Spectrum (Variable Height)")
        
        self.ax_ms1_fixed.text(0.5, 0.5, 'データなし', 
                              ha='center', va='center', transform=self.ax_ms1_fixed.transAxes)
        self.ax_ms1_fixed.set_title("MS1 Spectrum (Fixed Height)")
        
        self.ax_ms1_zoom.text(0.5, 0.5, 'データなし', 
                             ha='center', va='center', transform=self.ax_ms1_zoom.transAxes)
        self.ax_ms1_zoom.set_title("MS1 Spectrum (Zoom)")
        
        self.figure.tight_layout()
        self.canvas.draw()
        
    def set_data(self, df):
        """外部からデータをセット"""
        self.df = df.copy()
        self.status_label.setText(f"データ受信完了 ({len(df)} 行) - MS1データを処理してください")
        self.process_button.setEnabled(True)
        
    def process_ms1_data(self):
        """MS1データの処理"""
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

            # MS1データのみフィルタリング
            self.df = self.df[self.df['ms_level'] == 1]
            
            if self.df.empty:
                QtWidgets.QMessageBox.critical(self, "エラー", "MS1データが見つかりません")
                return

            # スキャン番号を連番に振り直し
            unique_scans = sorted(self.df['scan_number'].unique())
            scan_mapping = {old_scan: new_scan for new_scan, old_scan in enumerate(unique_scans, 1)}
            self.df['scan_number'] = self.df['scan_number'].map(scan_mapping)

            # Max列を追加：各スキャンで最も強度の高いスペクトルに1、それ以外は0
            self.df['Max'] = 0
            max_intensity_idx = self.df.groupby('scan_number')['intensity'].idxmax()
            self.df.loc[max_intensity_idx, 'Max'] = 1

            # Max列が1のスペクトルの最大強度とm/z範囲を計算
            max_spectra = self.df[self.df['Max'] == 1]
            self.max_spectrum_intensity = max_spectra['intensity'].max()
            
            if not max_spectra.empty:
                self.max_spectrum_mz_center = max_spectra['mz'].iloc[0]
            else:
                self.max_spectrum_mz_center = self.df['mz'].mean()

            # クロマトグラムの作成
            chrom_df = self.df.groupby("scan_number")["intensity"].sum().reset_index()
            chrom_df = chrom_df.sort_values("scan_number")
            self.all_scans = chrom_df["scan_number"].tolist()

            self.ax_chrom.clear()
            self.ax_chrom.plot(chrom_df["scan_number"], chrom_df["intensity"], color="black")
            self.ax_chrom.set_title("MS1 Chromatogram")
            self.ax_chrom.set_xlabel("Scan Number")
            self.ax_chrom.set_ylabel("Total Intensity")
            self.ax_chrom.grid(True)

            # m/z範囲の設定
            self.all_mz_min = self.df['mz'].min() - 10
            self.all_mz_max = self.df['mz'].max() + 10

            # 科学的記数法のフォーマッタ
            formatter = ScalarFormatter(useMathText=True)
            formatter.set_scientific(True)
            formatter.set_powerlimits((-3, 3))
            self.ax_chrom.yaxis.set_major_formatter(formatter)

            # 初期のMS1スペクトルプロット（空）
            self.setup_spectrum_plots()

            self.figure.tight_layout()
            self.canvas.draw()

            self.status_label.setText(f"MS1処理完了 - スキャン数: {len(self.all_scans)} (クロマトグラムをクリックしてください)")
            
            # 自動的に中央のスキャンを表示
            if self.all_scans:
                middle_scan = self.all_scans[len(self.all_scans)//2]
                self.update_scan(middle_scan)

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "処理エラー", f"MS1データの処理中にエラーが発生しました:\n{str(e)}")
            
    def setup_spectrum_plots(self):
        """スペクトルプロットの初期設定"""
        self.ax_ms1_var.clear()
        self.ax_ms1_var.set_title("MS1 Spectrum (Variable Height)")
        self.ax_ms1_var.set_xlabel("m/z")
        self.ax_ms1_var.set_ylabel("Intensity (%)")
        self.ax_ms1_var.grid(True)
        self.ax_ms1_var.set_xlim(self.all_mz_min, self.all_mz_max)

        self.ax_ms1_fixed.clear()
        self.ax_ms1_fixed.set_title("MS1 Spectrum (Fixed Height)")
        self.ax_ms1_fixed.set_xlabel("m/z")
        self.ax_ms1_fixed.set_ylabel("Intensity (%)")
        self.ax_ms1_fixed.grid(True)
        zoom_min = self.max_spectrum_mz_center - 0.5
        zoom_max = self.max_spectrum_mz_center + 2.5
        self.ax_ms1_fixed.set_xlim(zoom_min, zoom_max)
        self.ax_ms1_fixed.set_ylim(0, 100)

        self.ax_ms1_zoom.clear()
        self.ax_ms1_zoom.set_title("MS1 Spectrum (Zoom)")
        self.ax_ms1_zoom.set_xlabel("m/z")
        self.ax_ms1_zoom.set_ylabel("Intensity (%)")
        self.ax_ms1_zoom.grid(True)
        zoom_min = self.max_spectrum_mz_center - 0.1
        zoom_max = self.max_spectrum_mz_center + 0.5
        self.ax_ms1_zoom.set_xlim(zoom_min, zoom_max)
        self.ax_ms1_zoom.set_ylim(0, 100)

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
        self.update_scan(nearest_scan)

    def update_scan(self, scan_number):
        """指定されたスキャンのスペクトルを表示"""
        self.current_scan = scan_number
        
        scan_data = self.df[self.df['scan_number'] == scan_number]
        
        if scan_data.empty:
            return

        # 赤い縦線の更新
        self.scan_line = self.safe_remove_artist(self.scan_line)
        self.scan_line = self.ax_chrom.axvline(scan_number, color='red', linestyle='--', linewidth=2)

        current_max_intensity = scan_data['intensity'].max()
        mz_values = scan_data['mz'].values
        intensity_values = scan_data['intensity'].values

        # Max列が1のデータがあるかチェック
        max_data = scan_data[scan_data['Max'] == 1]
        
        if max_data.empty:
            # 代替として最大強度のm/z値を使用
            max_idx = scan_data['intensity'].idxmax()
            self.current_center_mz = scan_data.loc[max_idx, 'mz']
        else:
            self.current_center_mz = max_data['mz'].iloc[0]

        # MS1スペクトル（１）: 可変高さ
        self.ax_ms1_var.clear()
        self.ax_ms1_var.set_title(f"マススペクトル全体 Scan {scan_number}")
        self.ax_ms1_var.set_xlabel("m/z")
        self.ax_ms1_var.set_ylabel("Intensity (%)")
        self.ax_ms1_var.grid(True)
        
        intensity_percent_var = (intensity_values / current_max_intensity) * 100
        self.ax_ms1_var.vlines(mz_values, 0, intensity_percent_var, color='black', linewidth=1, alpha=0.7)
        self.ax_ms1_var.set_xlim(self.all_mz_min, self.all_mz_max)
        self.ax_ms1_var.set_ylim(0, 100)
        
        # Max中心±4の範囲を透明黄色で塗りつぶし
        zoom_min_left = self.current_center_mz - 1
        zoom_max_left = self.current_center_mz + 3
        self.ax_ms1_var.axvspan(zoom_min_left, zoom_max_left, color='yellow', alpha=0.7)

        # MS1スペクトル（２）: 固定高さ、ズーム表示
        self.ax_ms1_fixed.clear()
        self.ax_ms1_fixed.set_title(f"拡大して同位体パターンを見る　Scan {scan_number}")
        self.ax_ms1_fixed.set_xlabel("m/z")
        self.ax_ms1_fixed.set_ylabel("Intensity (%)")
        self.ax_ms1_fixed.grid(True)

        # Max中心±4の範囲を透明黄色で塗りつぶし
        zoom_min_left = self.current_center_mz - 0.02
        zoom_max_left = self.current_center_mz + 0.02
        self.ax_ms1_fixed.axvspan(zoom_min_left, zoom_max_left, color='yellow', alpha=0.7)

        # MS1スペクトル（３）: さらに拡大
        self.ax_ms1_zoom.clear()
        self.ax_ms1_zoom.set_title(f"さらに拡大して分解能を理解する　Scan {scan_number}")
        self.ax_ms1_zoom.set_xlabel("m/z")
        self.ax_ms1_zoom.set_ylabel("Intensity (%)")
        self.ax_ms1_zoom.grid(True)
        
        # 現在のスキャンでMax列が1のスペクトルの最大強度を取得
        current_max_spectra = scan_data[scan_data['Max'] == 1]
        if not current_max_spectra.empty:
            current_max_spectrum_intensity = current_max_spectra['intensity'].max()
        else:
            current_max_spectrum_intensity = current_max_intensity
        
        # ズーム範囲を設定
        zoom_min_1 = self.current_center_mz - 0.5
        zoom_max_1 = self.current_center_mz + 2.5
        zoom_min_2 = self.current_center_mz - 0.02
        zoom_max_2 = self.current_center_mz + 0.02
        zoom_mid_2 = (zoom_min_2 + zoom_max_2) / 2
        
        # 現在のスキャンのMax列が1のスペクトル強度を基準に100%変換
        intensity_percent_fixed = (intensity_values / current_max_spectrum_intensity) * 100
        self.ax_ms1_fixed.vlines(mz_values, 0, intensity_percent_fixed, color='black', linewidth=1, alpha=0.7)
        self.ax_ms1_fixed.set_xlim(zoom_min_1, zoom_max_1)
        self.ax_ms1_fixed.set_ylim(0, 15)

        # 更に拡大したビュー
        self.ax_ms1_zoom.plot(mz_values, intensity_percent_fixed, color='black', linewidth=0.8)
        self.ax_ms1_zoom.set_xlim(zoom_min_2, zoom_max_2)
        self.ax_ms1_zoom.set_xticks([zoom_min_2, zoom_mid_2, zoom_max_2])
        self.ax_ms1_zoom.xaxis.set_major_formatter(FormatStrFormatter('%.3f'))
        self.ax_ms1_zoom.tick_params(axis='x', labelsize=8)
        self.ax_ms1_zoom.set_ylim(0, 100)       

        self.figure.tight_layout()
        self.canvas.draw()
        
        # ステータス更新
        self.status_label.setText(f"Scan {scan_number} を表示中 (←→キーで移動可能)")