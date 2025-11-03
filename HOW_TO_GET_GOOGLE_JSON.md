# GoogleサービスアカウントのJSONを取得する方法

## 📋 手順

### ステップ1: Google Cloud Consoleにアクセス

1. **Google Cloud Console** を開く
   - https://console.cloud.google.com
2. プロジェクトを選択（既存のプロジェクトがある場合）

### ステップ2: サービスアカウントに移動

1. 左側のメニューから **"IAM & Admin"** → **"サービスアカウント"** をクリック
   - または直接: https://console.cloud.google.com/iam-admin/serviceaccounts

### ステップ3: サービスアカウントを選択（または作成）

#### 既存のサービスアカウントがある場合

1. サービスアカウントの一覧から、使用したいアカウントをクリック
2. ステップ4に進む

#### 新規でサービスアカウントを作成する場合

1. 上部の **"サービスアカウントを作成"** をクリック
2. **サービスアカウント名** を入力（例: `pdf-filler-service`）
3. **"作成して続行"** をクリック
4. **役割** を選択（例: `Editor` または `Storage Admin`）
5. **"完了"** をクリック

### ステップ4: キーを作成

1. サービスアカウントの詳細ページで、**"キー"** タブをクリック
2. **"キーを追加"** → **"新しいキーを作成"** をクリック
3. **"JSON"** を選択
4. **"作成"** をクリック

### ステップ5: JSONファイルをダウンロード

1. JSONファイルが自動的にダウンロードされます（例: `project-name-xxxxx.json`）
2. このファイルを開く（テキストエディタで開く）

### ステップ6: JSONファイルの内容をコピー

JSONファイルを開くと、以下のような形式のJSONが表示されます：

```json
{
  "type": "service_account",
  "project_id": "your-project-id",
  "private_key_id": "xxxxx",
  "private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n",
  "client_email": "xxxxx@xxxxx.iam.gserviceaccount.com",
  "client_id": "xxxxx",
  "auth_uri": "https://accounts.google.com/o/oauth2/auth",
  "token_uri": "https://oauth2.googleapis.com/token",
  "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
  "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/xxxxx"
}
```

**このJSON全体をコピー**してください。

### ステップ7: Render.comに貼り付け

1. Render.comのサービスページ → **"Environment"** タブ
2. **"Edit"** をクリック
3. `GOOGLE_CREDENTIALS_JSON` の値を編集
4. コピーしたJSON全体を貼り付け
5. **"Save Changes"** をクリック

---

## ✅ 確認ポイント

### JSONファイルの形式確認

正しいJSONファイルには以下が含まれています：

- ✅ `"type": "service_account"`
- ✅ `"project_id": "..."`（プロジェクトID）
- ✅ `"private_key": "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"`
- ✅ `"client_email": "...@....iam.gserviceaccount.com"`

### 重要な注意事項

- ⚠️ **JSONファイルは機密情報**です。GitHubにプッシュしないでください
- ⚠️ **JSONファイルは1回しか表示されません**。ダウンロードしたファイルを安全に保管してください
- ⚠️ **キーを紛失した場合**は、新しいキーを作成する必要があります

---

## 🔑 必要な権限

サービスアカウントには以下の権限が必要です：

- **Google Drive API** へのアクセス権限
- PDFテンプレートと出力フォルダへのアクセス権限

### 権限の設定方法

1. Google Cloud Console → **"APIとサービス"** → **"有効なAPI"**
2. **"Google Drive API"** が有効になっているか確認
3. サービスアカウントのメールアドレスを、PDFテンプレートと出力フォルダに共有
   - Google Driveでファイル/フォルダを右クリック → **"共有"**
   - サービスアカウントのメールアドレスを追加

---

## 📝 まとめ

1. Google Cloud Console → **"IAM & Admin"** → **"サービスアカウント"**
2. サービスアカウントを選択
3. **"キー"** タブ → **"キーを追加"** → **"新しいキーを作成"**
4. **"JSON"** を選択 → **"作成"**
5. ダウンロードしたJSONファイルを開く
6. **JSON全体をコピー**
7. Render.comの環境変数 `GOOGLE_CREDENTIALS_JSON` に貼り付け

---

以上です！JSONファイルを取得して、Render.comに設定してください。

