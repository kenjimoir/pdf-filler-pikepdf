# Render.comでのデプロイガイド

このガイドでは、Render.comでpikepdfを使ったPDFフィラーサービスをデプロイする手順を説明します。

## 🎯 なぜRender.com？

- ✅ **料金体系が良い** - 無料プランから始められる
- ✅ **Dockerfileをサポート** - 現在の実装がそのまま動作
- ✅ **pikepdfが使える** - Python環境が整っている（PDFtkは不要）
- ✅ **自動デプロイ** - GitHubにプッシュすると自動デプロイ

## 📋 前提条件

1. GitHubアカウント（コードをプッシュするため）
2. Render.comアカウント（無料で作成可能）
3. Googleサービスアカウントの認証情報（JSON形式）

---

## ステップ1: Render.comアカウントの作成

1. https://render.com にアクセス
2. **"Get Started for Free"** をクリック
3. GitHubアカウントでログイン

---

## ステップ2: リポジトリの準備

GitHubにコードをプッシュ済みであることを確認：

```bash
cd "/Users/p56/Desktop/Cursor Projects/保険申込書自動作成/pdf-filler-pdftk"
git add .
git commit -m "Add pikepdf support"
git push
```

---

## ステップ3: Render.comでWeb Serviceを作成

### 3-1. 新しいWeb Serviceを作成

1. Render.com Dashboard → **"New +"** をクリック
2. **"Web Service"** を選択
3. **"Connect GitHub repository"** をクリック
4. リポジトリを選択（初回はGitHubの認証が必要）

### 3-2. 基本設定

以下の設定を行います：

| 項目 | 値 | 説明 |
|------|-----|------|
| **Name** | `pdf-filler-service` | サービス名（任意） |
| **Region** | `Oregon (US West)` | 最寄りのリージョンを選択 |
| **Branch** | `main` | Gitブランチ |
| **Root Directory** | `pdf-filler-pdftk` | リポジトリのルートディレクトリ |
| **Runtime** | `Docker` | **重要: Dockerを選択** |
| **Dockerfile Path** | `Dockerfile` | デフォルトのままでOK |
| **Instance Type** | `Starter ($7/月)` | 本番ならStarter以上を推奨 |

**重要**: 
- **Runtime は `Docker` を選択**
- **Root Directory はプロジェクトのルートを指定**（リポジトリ直下なら空欄でOK）

### 3-3. インスタンスタイプの選択

| プラン | 料金 | 特徴 | 推奨用途 |
|--------|------|------|----------|
| **Free** | $0/月 | スリープする可能性、制限あり | テスト環境 |
| **Starter** | $7/月 | 常時起動、512MB RAM | 小規模な本番環境 |
| **Standard** | $25/月 | 1GB RAM、高性能 | 中規模な本番環境 |

**推奨**: 本番環境なら **Starter** 以上を推奨

---

## ステップ4: 環境変数の設定

### 4-1. 環境変数の追加

1. サービスの設定画面で **"Environment"** タブを開く
2. **"Add Environment Variable"** をクリック

### 4-2. 必須の環境変数

#### GOOGLE_CREDENTIALS_JSON（必須）

**Key**: `GOOGLE_CREDENTIALS_JSON`  
**Value**: GoogleサービスアカウントのJSON全体

**取得方法**:
1. Google Cloud Console → **"IAM & Admin"** → **"サービスアカウント"**
2. 既存のサービスアカウントを選択
3. **"キー"** タブ → **"キーを追加"** → **"新しいキーを作成"**
4. **"JSON"** を選択 → **"作成"**
5. ダウンロードしたJSONファイルを開く
6. **全体をコピーして貼り付け**

**注意**: 
- Render.comでは改行を含むJSONでも自動的に処理されます
- JSON全体を1行で貼り付けても動作します

### 4-3. オプションの環境変数

#### PDF_FILL_METHOD（推奨）

**Key**: `PDF_FILL_METHOD`  
**Value**: `pikepdf`

**説明**: PDFフィル方法を指定（デフォルトは`pikepdf`なので設定しなくてもOK）

#### PORT（オプション）

**Key**: `PORT`  
**Value**: `10000`

**説明**: Render.comはデフォルトでポート10000を使用（設定しなくてもOK）

#### OUTPUT_FOLDER_ID（オプション）

**Key**: `OUTPUT_FOLDER_ID`  
**Value**: `1Q2DuIctvy1n4YyGSixA15BRQ-9gdWvot`（あなたのフォルダID）

**説明**: デフォルト出力フォルダID（API呼び出し時に`folderId`を指定すれば不要）

---

## ステップ5: デプロイ開始

### 5-1. デプロイを開始

1. 設定を確認
2. **"Create Web Service"** ボタンをクリック
3. 自動的にビルドが開始されます

### 5-2. ビルドログの確認

**"Logs"** タブでビルドの進行状況を確認：

✅ **成功のサイン**:
```
Step 1/10 : FROM node:18
...
Successfully installed pikepdf-8.10.0
✅ pikepdf found: 8.10.0
✅ PDFtk found: 3.3.3
🚀 PDF Filler PDFtk running on port 10000
```

❌ **エラーが出た場合**:
- `Dockerfile not found` → Root Directoryが正しいか確認
- `Python not found` → DockerfileのPythonインストール部分を確認
- `pikepdf installation failed` → Dockerfileのpipコマンドを確認

### 5-3. デプロイ時間

- **初回ビルド**: 5-10分程度（Dockerイメージのビルドのため）
- **2回目以降**: 2-5分程度（キャッシュが使われる）

---

## ステップ6: URLの確認

### 6-1. 自動生成URLの確認

デプロイが完了したら：

1. **"Settings"** タブ → **"Auto-generated URL"** を確認
2. URLが自動生成されます（例: `pdf-filler-service.onrender.com`）
3. このURLをGASコードで使用します

### 6-2. カスタムドメイン（オプション）

独自ドメインを使いたい場合：

1. **"Settings"** タブ → **"Custom Domain"** をクリック
2. ドメインを入力
3. DNS設定を追加（指示に従う）

---

## ステップ7: 動作確認

### 7-1. ヘルスチェック

ブラウザまたはcurlで確認：

```bash
curl https://pdf-filler-service.onrender.com/health
```

期待される応答：
```json
{
  "ok": true,
  "pdftkAvailable": true,
  "pikepdfAvailable": true,
  "preferredMethod": "pikepdf",
  "outputFolder": "1Q2DuIctvy1n4YyGSixA15BRQ-9gdWvot",
  "tempDir": "/tmp/pdf-filler-pdftk"
}
```

**重要**: `pikepdfAvailable: true` が表示されていればOK！

### 7-2. GASコードのエンドポイント更新

`Code.gs` のエンドポイントを更新：

```javascript
// Render.comの場合
const FILLER_ENDPOINT = 'https://pdf-filler-service.onrender.com';

// 既存のRailwayの場合（もしあれば）
// const FILLER_ENDPOINT = 'https://pdf-filler-service-production.up.railway.app';
```

---

## ステップ8: 実際にPDF生成をテスト

### 8-1. GAS Web Appからテスト

1. Google Apps Scriptエディタで `Code.gs` を開く
2. 実際のフォームから送信
3. ログを確認：
   ```javascript
   Logger.log('FILLER response %s: %s', code, text);
   ```

### 8-2. ログで確認すべき点

✅ **成功の場合**:
```
📝 Filling PDF with pikepdf...
✅ Filled 15 fields (skipped 0)
✅ PDF filled successfully with pikepdf
   Output size: 123456 bytes
method: "pikepdf"
```

### 8-3. 生成されたPDFを確認

1. Google Driveで生成されたPDFを開く
2. 以下の点を確認：
   - ✅ 日本語テキストが正しく表示されている
   - ✅ フォントが正しく表示されている（文字化けしていない）
   - ✅ チェックボックスが適切に表示されている
   - ✅ ラジオボタンが適切に選択されている

---

## トラブルシューティング

### 問題1: デプロイが失敗する

**症状**: ビルドログにエラーが出る

**解決方法**:
1. **"Logs"** タブでエラーメッセージを確認
2. Root Directoryが正しいか確認
3. Dockerfileが正しく存在するか確認
4. 再デプロイを実行（**"Manual Deploy"** → **"Deploy latest commit"**）

### 問題2: pikepdfが見つからない

**症状**: `/health` で `pikepdfAvailable: false`

**解決方法**:
1. **"Logs"** タブでビルドログを確認
2. DockerfileのPythonインストール部分を確認
3. 再デプロイを実行

### 問題3: サービスがスリープする（Freeプランの場合）

**症状**: リクエストに応答しない、起動に時間がかかる

**解決方法**:
1. **Starterプラン以上にアップグレード**（常時起動）
2. または、定期的にpingする仕組みを追加

### 問題4: ポートエラー

**症状**: ポート関連のエラー

**解決方法**:
1. 環境変数 `PORT=10000` を設定（Render.comはポート10000を使用）
2. または、環境変数を削除してデフォルト（8080）を使用し、Render.comの設定でポートマッピングを確認

---

## Render.comとRailwayの比較

| 項目 | Render.com | Railway |
|------|------------|---------|
| **料金** | 無料プランあり、$7/月から | 従量課金（無料クレジットあり） |
| **設定** | 簡単 | やや複雑 |
| **パフォーマンス** | 良好 | 良好 |
| **スリープ** | Freeプランはスリープ | スリープなし |
| **Dockerfile** | ✅ サポート | ✅ サポート |
| **pikepdf** | ✅ 動作 | ✅ 動作 |

**結論**: 両方とも問題なく動作します！料金体系が良いRender.comを推奨します。

---

## チェックリスト

- [ ] Render.comアカウントを作成した
- [ ] GitHubにコードをプッシュした
- [ ] Render.comでWeb Serviceを作成した
- [ ] 環境変数を設定した
- [ ] デプロイが成功した
- [ ] `/health` で `pikepdfAvailable: true` が確認できた
- [ ] GASコードのエンドポイントを更新した
- [ ] 実際にPDFを生成してテストした
- [ ] 生成されたPDFで日本語が正しく表示された

---

以上です！質問があれば教えてください。

