#!/usr/bin/env bash
# 一次性配置：将本机 SSH 公钥部署到服务器，支持密钥登录（密码登录保留）
# 用法：./setup-ssh-keys.sh（会提示输入一次密码）或 DEPLOY_PASSWORD='...' ./setup-ssh-keys.sh（需安装 sshpass）
set -e
DEPLOY_HOST="${DEPLOY_HOST:-8.130.50.168}"
DEPLOY_USER="${DEPLOY_USER:-root}"
KEY_FILE="${HOME}/.ssh/id_ed25519"
PUB_FILE="${KEY_FILE}.pub"

# 1. 确保本机有密钥
if [[ ! -f "${PUB_FILE}" ]]; then
  echo ">>> 生成 SSH 密钥 ${KEY_FILE} ..."
  ssh-keygen -t ed25519 -N "" -f "${KEY_FILE}" -q
fi
echo ">>> 使用公钥: ${PUB_FILE}"

# 2. 将公钥写入服务器（仅此步需要密码）
if command -v sshpass &>/dev/null && [[ -n "${DEPLOY_PASSWORD}" ]]; then
  echo ">>> 使用 sshpass 上传公钥（一次性）..."
  sshpass -p "${DEPLOY_PASSWORD}" ssh-copy-id -o StrictHostKeyChecking=accept-new -i "${PUB_FILE}" "${DEPLOY_USER}@${DEPLOY_HOST}"
elif command -v ssh-copy-id &>/dev/null; then
  echo ">>> 请在弹出的提示中输入一次 root 密码..."
  ssh-copy-id -o StrictHostKeyChecking=accept-new -i "${PUB_FILE}" "${DEPLOY_USER}@${DEPLOY_HOST}"
else
  echo ">>> 请手动执行以下命令并输入一次密码："
  echo "   cat ${PUB_FILE} | ssh ${DEPLOY_USER}@${DEPLOY_HOST} 'mkdir -p ~/.ssh && chmod 700 ~/.ssh && cat >> ~/.ssh/authorized_keys && chmod 600 ~/.ssh/authorized_keys'"
  read -p "完成后按回车继续..."
fi

# 3. 验证密钥登录
echo ">>> 验证密钥登录..."
ssh -o BatchMode=yes -o ConnectTimeout=10 "${DEPLOY_USER}@${DEPLOY_HOST}" "echo '密钥登录成功'"

echo ">>> 完成。本机已支持密钥登录，ssh / deploy.sh 将不再询问密码（密码登录仍可用）。"
echo "    测试: ssh ${DEPLOY_USER}@${DEPLOY_HOST}"