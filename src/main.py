import sys
import pandas as pd
from PySide6 import QtWidgets, QtCore
from PySide6.QtWidgets import (QApplication, QMainWindow, QTabWidget, 
                              QVBoxLayout, QWidget, QMenuBar, QFileDialog, 
                              QMessageBox, QStatusBar)

# 各タブのモジュールをインポート
from data_loader_tab import DataLoaderTab
from zoom_viewer_tab import ZoomViewerTab
from simple_ms1_tab import SimpleMS1Tab
from ms1_ms2_tab import MS1MS2Tab

class MSAnalysisApp(QMainWindow):
    # データが更新されたときに発信するシグナル
    data_updated = QtCore.Signal(pd.DataFrame)
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("質量分析　触って学ぶ'動く'教科書")
        self.setGeometry(100, 100, 1400, 900)
        
        # 共有データ
        self.shared_data = None
        
        # UI構築
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        
    def setup_ui(self):
        """UI要素の初期化"""
        # 中央ウィジェット
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # メインレイアウト
        layout = QVBoxLayout(central_widget)
        
        # タブウィジェット
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)
        
        # 各タブを作成
        self.data_loader_tab = DataLoaderTab()
        self.zoom_viewer_tab = ZoomViewerTab()
        self.simple_ms1_tab = SimpleMS1Tab()
        self.ms1_ms2_tab = MS1MS2Tab()
        
        # タブを追加
        self.tab_widget.addTab(self.data_loader_tab, "データ読み込み")
        self.tab_widget.addTab(self.simple_ms1_tab, "Y軸固定・可変")
        self.tab_widget.addTab(self.zoom_viewer_tab, "拡大表示")
        self.tab_widget.addTab(self.ms1_ms2_tab, "DDAの可視化")
        
        # シグナル接続
        self.data_loader_tab.data_loaded.connect(self.on_data_loaded)
        
    def setup_menu(self):
        """メニューバーの設定"""
        menubar = self.menuBar()
        
        # ファイルメニュー
        file_menu = menubar.addMenu('ファイル')
        
        # データ読み込みアクション
        load_action = file_menu.addAction('Parquetファイルを開く')
        load_action.triggered.connect(self.load_data_file)
        
        file_menu.addSeparator()
        
        # 終了アクション
        exit_action = file_menu.addAction('終了')
        exit_action.triggered.connect(self.close)
        
        # ヘルプメニュー
        help_menu = menubar.addMenu('アプリについて')
        about_action = help_menu.addAction('アプリについて')
        about_action.triggered.connect(self.show_about)
        
    def setup_status_bar(self):
        """ステータスバーの設定"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - データファイルを読み込んでください")
        
    def load_data_file(self):
        """ファイルダイアログからデータを読み込み"""
        fname, _ = QFileDialog.getOpenFileName(
            self, 
            "Parquetファイルを選択", 
            filter="Parquet Files (*.parquet)"
        )
        if fname:
            self.data_loader_tab.load_file(fname)
            
    def on_data_loaded(self, df):
        """データが読み込まれた時の処理"""
        self.shared_data = df
        self.status_bar.showMessage(f"データ読み込み完了 - {len(df)} 行, {len(df.columns)} 列")
        
        # 全てのタブにデータを通知
        self.data_updated.emit(df)
        
        # 各タブにデータを渡す
        self.zoom_viewer_tab.set_data(df)
        self.simple_ms1_tab.set_data(df)
        self.ms1_ms2_tab.set_data(df)
        
        print(f"データが読み込まれました: {df.shape}")
        
    def show_about(self):
        """このアプリについて"""
        QMessageBox.about(
            self, 
            "触って学ぶ'動く'教科書の使い方\n\n",
            ""
            "2025年7月15日　初版\n"
            "西野 耕平"

        )
        
    def get_shared_data(self):
        """共有データを取得"""
        return self.shared_data
        
    def closeEvent(self, event):
        """アプリ終了時の処理"""
        reply = QMessageBox.question(
            self, 
            '終了確認',
            'アプリケーションを終了しますか？',
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            event.accept()
        else:
            event.ignore()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # アプリケーションの詳細設定
    app.setApplicationName("MS Analysis Suite")
    app.setApplicationVersion("1.0")
    app.setOrganizationName("MS Analysis Team")
    
    # メインウィンドウを作成・表示
    main_window = MSAnalysisApp()
    main_window.show()
    
    sys.exit(app.exec())