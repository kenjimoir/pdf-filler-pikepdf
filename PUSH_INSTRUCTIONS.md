# GitHubへのプッシュ手順

## Personal Access Tokenを使ってプッシュする方法

### ステップ1: Personal Access Tokenを作成

1. https://github.com/settings/tokens にアクセス
2. **"Generate new token"** → **"Generate new token (classic)"** をクリック
3. **Note**: `pdf-filler-pikepdf` を入力
4. **Expiration**: 適切な期間を選択（例: 90 days）
5. **Scopes**: `repo` にチェック
6. **"Generate token"** をクリック
7. **生成されたトークンをコピー**（重要：このトークンは一度しか表示されません）

### ステップ2: トークンを使ってプッシュ

以下のコマンドを実行してください（`YOUR_TOKEN` の部分を実際のトークンに置き換えてください）：

```bash
cd "/Users/p56/Desktop/Cursor Projects/保険申込書自動作成/pdf-filler-pikepdf"

# リモートURLにトークンを含める（一時的）
git remote set-url origin https://YOUR_TOKEN@github.com/kenjimoir/pdf-filler-pikepdf.git

# プッシュ
git push -u origin main

# プッシュ後、URLからトークンを削除（セキュリティのため）
git remote set-url origin https://github.com/kenjimoir/pdf-filler-pikepdf.git
```

**注意**: トークンを直接コマンドに入力するのはセキュリティ上推奨されません。以下の方法2を推奨します。

---

## 方法2: Git Credential Helperを使う（推奨）

### macOSの場合

```bash
cd "/Users/p56/Desktop/Cursor Projects/保険申込書自動作成/pdf-filler-pikepdf"

# Credential Helperを設定（Keychainを使用）
git config --global credential.helper osxkeychain

# プッシュを実行（初回のみ認証情報を入力）
git push -u origin main
```

**実行時の入力**:
- Username: `kenjimoir`
- Password: `（Personal Access Tokenを貼り付け）`

認証情報はmacOS Keychainに保存され、次回以降は自動的に使用されます。

---

## 方法3: SSH鍵を使う（既に設定済みの場合）

SSH鍵を設定している場合は：

```bash
cd "/Users/p56/Desktop/Cursor Projects/保険申込書自動作成/pdf-filler-pikepdf"

# リモートURLをSSHに変更
git remote set-url origin git@github.com:kenjimoir/pdf-filler-pikepdf.git

# プッシュ
git push -u origin main
```

---

## 確認

プッシュが成功したら、GitHubのリポジトリページでファイルが表示されているか確認してください：

https://github.com/kenjimoir/pdf-filler-pikepdf

---

## トラブルシューティング

### 認証エラーが出る場合

1. Personal Access Tokenが正しく作成されているか確認
2. トークンの有効期限が切れていないか確認
3. `repo` スコープが選択されているか確認

### プッシュできない場合

```bash
# リモートURLを確認
git remote -v

# リモートを削除して再追加
git remote remove origin
git remote add origin https://github.com/kenjimoir/pdf-filler-pikepdf.git
```

