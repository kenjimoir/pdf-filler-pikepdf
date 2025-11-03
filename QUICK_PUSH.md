# クイックプッシュガイド

## 📝 手順

### 1. Personal Access Tokenを作成

1. https://github.com/settings/tokens にアクセス
2. **"Generate new token"** → **"Generate new token (classic)"**
3. **Note**: `pdf-filler-pikepdf`
4. **Expiration**: 90 days（または任意）
5. **Scopes**: `repo` にチェック ✅
6. **"Generate token"** をクリック
7. **トークンをコピー**（一度しか表示されません！）

### 2. ターミナルでプッシュ

以下のコマンドを実行してください：

```bash
cd "/Users/p56/Desktop/Cursor Projects/保険申込書自動作成/pdf-filler-pikepdf"
git push -u origin main
```

**入力が求められたら**:
- Username: `kenjimoir`
- Password: `（コピーしたPersonal Access Tokenを貼り付け）`

認証情報はmacOS Keychainに保存され、次回以降は自動的に使用されます。

---

## ✅ プッシュ成功の確認

プッシュが成功したら、以下のURLでファイルが表示されていることを確認してください：

https://github.com/kenjimoir/pdf-filler-pikepdf

9つのファイルが表示されていればOKです！

---

Personal Access Tokenを作成したら、上記のコマンドを実行してください。

