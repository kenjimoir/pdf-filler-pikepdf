# Render.comデプロイ - クイックスタート

GitHubにコードをプッシュできたので、次はRender.comにデプロイしましょう！

## 🚀 デプロイ手順（5ステップ）

### ステップ1: Render.comにログイン

1. https://render.com にアクセス
2. **"Get Started for Free"** または **"Sign In"** をクリック
3. **GitHubアカウントでログイン**（推奨）

### ステップ2: 新しいWeb Serviceを作成

1. Render.com Dashboard → **"New +"** をクリック
2. **"Web Service"** を選択
3. **"Connect GitHub repository"** をクリック
4. **`kenjimoir/pdf-filler-pikepdf`** リポジトリを選択

### ステップ3: 基本設定

以下の設定を行います：

| 項目 | 値 |
|------|-----|
| **Name** | `pdf-filler-pikepdf` |
| **Region** | `Oregon (US West)` または最寄りのリージョン |
| **Branch** | `main` |
| **Root Directory** | （空欄のまま - リポジトリのルートを使用） |
| **Runtime** | **`Docker`** ← **重要！** |
| **Dockerfile Path** | `Dockerfile`（デフォルト） |
| **Instance Type** | **`Starter ($7/月)`** を推奨（Freeプランはスリープします） |

**重要**: 
- **Runtime は `Docker` を選択してください**
- Root Directory は空欄のまま

### ステップ4: 環境変数を設定

1. **"Environment"** セクションまでスクロール
2. **"Add Environment Variable"** をクリック

**設定する環境変数:**

#### 必須

**`GOOGLE_CREDENTIALS_JSON`**
- **Key**: `GOOGLE_CREDENTIALS_JSON`
- **Value**: GoogleサービスアカウントのJSON全体

**取得方法**:
1. Google Cloud Console → **"IAM & Admin"** → **"サービスアカウント"**
2. 既存のサービスアカウントを選択
3. **"キー"** タブ → **"キーを追加"** → **"新しいキーを作成"**
4. **"JSON"** を選択 → **"作成"**
5. ダウンロードしたJSONファイルを開く
6. **全体をコピーして貼り付け**

#### オプション（推奨）

**`PORT`**
- **Key**: `PORT`
- **Value**: `10000`（Render.comのデフォルトポート）

**`OUTPUT_FOLDER_ID`**（オプション）
- **Key**: `OUTPUT_FOLDER_ID`
- **Value**: `1Q2DuIctvy1n4YyGSixA15BRQ-9gdWvot`（あなたのフォルダID）

### ステップ5: デプロイ開始

1. 設定を確認
2. **"Create Web Service"** ボタンをクリック
3. 自動的にビルドが開始されます

---

## ⏱️ デプロイ時間

- **初回ビルド**: 5-10分程度（Dockerイメージのビルド）
- **2回目以降**: 2-5分程度（キャッシュが使われる）

---

## ✅ デプロイ成功の確認

### 1. ビルドログを確認

Render.comの **"Logs"** タブで以下のようなログが出ていればOK：

```
Successfully installed pikepdf-x.x.x
✅ pikepdf found: x.x.x
🚀 PDF Filler (pikepdf) running on port 10000
```

### 2. ヘルスチェック

デプロイが完了したら、**"Settings"** タブ → **"Auto-generated URL"** を確認

ブラウザまたはcurlで確認：

```bash
curl https://pdf-filler-pikepdf.onrender.com/health
```

期待される応答：
```json
{
  "ok": true,
  "pikepdfAvailable": true,
  "method": "pikepdf"
}
```

**重要**: `pikepdfAvailable: true` が表示されていればOK！

---

## 📝 次のステップ

デプロイが成功したら：

1. **URLを確認**: Render.comの **"Settings"** → **"Auto-generated URL"**
2. **GASコードを更新**: `Code.gs` の `FILLER_ENDPOINT` を更新
3. **動作確認**: 実際にPDFを生成してテスト

---

## 🆘 トラブルシューティング

### ビルドエラーが出る場合

- **"Logs"** タブでエラーメッセージを確認
- Dockerfileが正しく存在するか確認
- Python/pikepdfのインストールエラーがないか確認

### サービスが起動しない場合

- 環境変数 `GOOGLE_CREDENTIALS_JSON` が正しく設定されているか確認
- ポート設定（`PORT=10000`）を確認

### pikepdfが見つからない場合

- ビルドログで `Successfully installed pikepdf` が表示されているか確認
- Dockerfileが正しくビルドされているか確認

---

以上です！Render.comでデプロイを開始してください。

