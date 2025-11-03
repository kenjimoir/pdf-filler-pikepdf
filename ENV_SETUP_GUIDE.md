# Render.com 環境変数設定ガイド

## ❌ エラー内容

```
Error: Either GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS must be set
```

これは、Render.comで環境変数 `GOOGLE_CREDENTIALS_JSON` が設定されていないことを示しています。

---

## ✅ 解決方法：環境変数を設定

### ステップ1: Render.comのサービスページを開く

1. https://render.com にログイン
2. Dashboard → **`pdf-filler-pikepdf`** サービスをクリック

### ステップ2: 環境変数を追加

1. 左側のメニューから **"Environment"** をクリック
2. **"Add Environment Variable"** をクリック

### ステップ3: GOOGLE_CREDENTIALS_JSON を設定

**Key**: `GOOGLE_CREDENTIALS_JSON`

**Value**: GoogleサービスアカウントのJSON全体

#### GoogleサービスアカウントのJSONを取得する方法

1. **Google Cloud Console** にアクセス
   - https://console.cloud.google.com
2. **"IAM & Admin"** → **"サービスアカウント"** をクリック
3. 既存のサービスアカウントを選択（または新規作成）
4. **"キー"** タブをクリック
5. **"キーを追加"** → **"新しいキーを作成"** をクリック
6. **"JSON"** を選択 → **"作成"** をクリック
7. ダウンロードしたJSONファイルを開く
8. **ファイル全体をコピー**（1行でも複数行でもOK）

#### Render.comに貼り付け

1. Render.comの **"Add Environment Variable"** 画面で
2. **Key**: `GOOGLE_CREDENTIALS_JSON` を入力
3. **Value**: コピーしたJSON全体を貼り付け
4. **"Save Changes"** をクリック

**注意**: 
- JSON全体を1行で貼り付けても動作します
- 改行を含むJSONでも自動的に処理されます
- JSONの形式が正しいか確認してください（`{` で始まり `}` で終わる）

### ステップ4: オプションの環境変数（推奨）

以下も設定することを推奨します：

**`PORT`**
- **Key**: `PORT`
- **Value**: `10000`

**`OUTPUT_FOLDER_ID`**（オプション）
- **Key**: `OUTPUT_FOLDER_ID`
- **Value**: `1Q2DuIctvy1n4YyGSixA15BRQ-9gdWvot`（あなたのフォルダID）

### ステップ5: サービスを再起動

環境変数を設定した後、サービスが自動的に再起動されます。

または、手動で再起動：
1. **"Manual Deploy"** → **"Deploy latest commit"** をクリック

---

## ✅ 設定確認

### 1. 環境変数が設定されているか確認

Render.comの **"Environment"** タブで確認：
- ✅ `GOOGLE_CREDENTIALS_JSON` が表示されている
- ✅ 値が設定されている（値は非表示になっている場合があります）

### 2. ログで確認

サービスが再起動したら、**"Logs"** タブで以下のエラーが出ていないか確認：

✅ **成功のサイン**:
```
✅ pikepdf found: 10.0.0
🚀 PDF Filler (pikepdf) running on port 10000
```

❌ **エラーが出ている場合**:
```
Error: Either GOOGLE_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS must be set
```
→ 環境変数が正しく設定されていません

### 3. ヘルスチェック

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

---

## 🔒 セキュリティ注意事項

- ✅ 環境変数は暗号化されて保存されます
- ✅ 値は表示されません（セキュリティのため）
- ❌ JSONファイルをGitHubにプッシュしないでください
- ❌ 環境変数の値を直接ログに出力しないでください

---

## 🆘 トラブルシューティング

### エラーが続く場合

1. **JSONの形式を確認**
   - JSONが正しい形式か確認（`{` で始まり `}` で終わる）
   - コピー&ペースト時に文字が欠けていないか確認

2. **環境変数の再設定**
   - 一度削除して再追加してみる
   - 値の前後に余分なスペースがないか確認

3. **サービスを再起動**
   - 環境変数を設定した後、必ずサービスを再起動

4. **ログを確認**
   - Render.comの **"Logs"** タブで詳細なエラーメッセージを確認

---

以上です！環境変数を設定したら、サービスが自動的に再起動されます。

設定が完了したら、もう一度フォームからPDF生成を試してください。

