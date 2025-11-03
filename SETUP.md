# セットアップガイド - pikepdf専用PDFフィラー

このディレクトリはpikepdfのみを使用するシンプルな構成です。

## 📁 ファイル構成

```
pdf-filler-pikepdf/
├── package.json          # Node.js依存関係
├── index.js             # メインサーバー（pikepdf専用）
├── Dockerfile           # Docker設定（Python/pikepdfのみ）
├── pdf_filler_pikepdf.py # pikepdf Pythonスクリプト
├── requirements.txt     # Python依存関係
├── .gitignore          # Git無視設定
├── README.md           # プロジェクト説明
├── RENDER_GUIDE.md     # Render.comデプロイガイド
└── SETUP.md           # このファイル
```

**合計: 9ファイル**（必要最小限の構成）

---

## 🚀 GitHubへのプッシュ手順

### ステップ1: Gitリポジトリを初期化

```bash
cd "/Users/p56/Desktop/Cursor Projects/保険申込書自動作成/pdf-filler-pikepdf"
git init
```

### ステップ2: 全てのファイルを追加

```bash
git add .
```

### ステップ3: 初回コミット

```bash
git commit -m "Initial commit: pikepdf-only PDF filler service"
```

### ステップ4: GitHubでリポジトリを作成

1. https://github.com にアクセス
2. **"New repository"** をクリック
3. リポジトリ名を入力（例: `pdf-filler-pikepdf`）
4. **"Create repository"** をクリック

### ステップ5: リモートリポジトリを追加してプッシュ

```bash
# リモートリポジトリを追加（あなたのGitHubユーザー名に置き換えてください）
git remote add origin https://github.com/あなたのユーザー名/pdf-filler-pikepdf.git

# メインブランチにプッシュ
git branch -M main
git push -u origin main
```

---

## ✅ 確認事項

プッシュ前に以下を確認してください：

- [x] `.gitignore` が存在し、`node_modules/` と `.env` が除外されている
- [x] `index.js` に機密情報がハードコードされていない（環境変数を使用）
- [x] 全ての必須ファイル（8ファイル）が含まれている
- [x] 不要なJavaファイル（`.java`）が含まれていない

---

## 📝 ファイル一覧（最終確認）

プッシュするファイル：

```
✅ package.json
✅ index.js
✅ Dockerfile
✅ pdf_filler_pikepdf.py
✅ requirements.txt
✅ .gitignore
✅ README.md
✅ RENDER_GUIDE.md
✅ SETUP.md
```

**合計: 9ファイル**

---

## 🔒 セキュリティ確認

### ✅ 安全

- ✅ 環境変数は `process.env` から読み込む
- ✅ `.env` ファイルは `.gitignore` に含まれている
- ✅ 認証情報はコードにハードコードされていない

### ❌ 避けるべき

- ❌ 認証情報をコードにハードコード
- ❌ `.env` ファイルをプッシュ
- ❌ JSON形式の認証ファイルをプッシュ

---

## 🎯 次のステップ

GitHubにプッシュしたら：

1. **Render.comでWeb Serviceを作成**
   - `RENDER_GUIDE.md` を参照
   - GitHubリポジトリを接続
   - 環境変数を設定

2. **動作確認**
   - `/health` エンドポイントで確認
   - 実際にPDFを生成してテスト

---

以上です！`RENDER_GUIDE.md` を参照してRender.comにデプロイしてください。

