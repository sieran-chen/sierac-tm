# 用 yeemio 账号 + SSH 密钥推送到 sieran-chen/sierac-tm

不换登录账号，用 **yeemio** 通过 SSH 推送。需要两步。

---

## 1. 仓库所有者：给 yeemio 写权限

**sieran-chen** 登录 GitHub → 打开 [sieran-chen/sierac-tm](https://github.com/sieran-chen/sierac-tm) → **Settings** → **Collaborators** → **Add people**，添加 **yeemio**。  
yeemio 接受邀请后即拥有 push 权限。

---

## 2. yeemio：把本机 SSH 公钥加到 GitHub

你本机已有密钥（之前配服务器时用的），一般是 `~/.ssh/id_ed25519.pub`。

**2.1 复制公钥内容**

- Git Bash / WSL：`cat ~/.ssh/id_ed25519.pub`
- Windows 用户目录下：`C:\Users\你的用户名\.ssh\id_ed25519.pub` 用记事本打开，复制全部内容

**2.2 添加到 GitHub**

- 用 **yeemio** 登录 [GitHub](https://github.com) → 右上角头像 → **Settings** → **SSH and GPG keys**
- **New SSH key**：Title 填例如 `Cursor Win`，Key 粘贴刚才的公钥 → **Add SSH key**

详见：[Adding a new SSH key to your GitHub account](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/adding-a-new-ssh-key-to-your-github-account)

**2.3 本仓库改用 SSH 地址**

在项目根目录执行（已可代你执行）：

```bash
git remote set-url origin git@github.com:sieran-chen/sierac-tm.git
git push -u origin main
```

之后都用 `git push` 即可，不再输 GitHub 密码。
