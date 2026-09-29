#!/usr/bin/env bash
# =============================================================================
# Лабораторная работа №3. Сбор доказательств выполнения.
#
# Записывает реальные результаты git-команд, состав репозитория, проверку
# на отсутствие секретов и состояние удалённого репозитория GitHub в файл
# evidence/git_validation.txt.
#
# Запуск:  ./evidence/make_evidence.sh
# =============================================================================
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
OUT="evidence/git_validation.txt"

# шаблон поиска потенциальных секретов; учебный пароль контейнера PostgreSQL
# и служебные имена Data Vault исключаются из результата
SECRET_RE='(api[_-]?key|secret|password|passwd|token|BEGIN [A-Z ]*PRIVATE KEY|ghp_|gho_|sk-[A-Za-z0-9]{20})'
SECRET_SKIP='labpass|POSTGRES_PASSWORD|password=labpass|record_source|hashdiff|вхождения слова password'

{
echo "======================================================================"
echo " Лабораторная работа №3. Git и GitHub"
echo " Студент: Никитин Платон Алексеевич, группа 231-363"
echo " Реальные результаты выполнения git-команд"
echo " Зафиксировано: $(date '+%Y-%m-%d %H:%M:%S %Z')"
echo " Каталог репозитория: $(pwd)"
echo "======================================================================"
echo
echo "\$ git --version"
git --version
echo
echo "\$ git config --global user.name"
git config --global user.name
echo
echo "\$ git config --global user.email"
git config --global user.email
echo
echo "\$ git branch --show-current"
git branch --show-current
echo
echo "\$ git status"
# сам файл журнала перегенерируется прямо сейчас, поэтому его собственное
# изменение из вывода исключается: иначе снимок ссылается сам на себя
echo "  (файл evidence/git_validation.txt перезаписывается этим скриптом)"
git status --short --untracked-files=all -- . ':!evidence/git_validation.txt' \
  | sed 's/^/  /' || true
git status --branch --short -- . ':!evidence/git_validation.txt' | head -1
echo
echo "\$ git remote -v"
git remote -v
echo
echo "\$ git branch -vv"
git branch -vv
echo
echo "\$ git log --oneline --decorate --graph --all"
git log --oneline --decorate --graph --all
echo
echo "\$ git log --stat --oneline"
git log --stat --oneline
echo
echo "======================================================================"
echo " Список файлов под контролем версий (git ls-files)"
echo "======================================================================"
git ls-files
echo
echo "======================================================================"
echo " Проверка отсутствия секретов (поиск по tracked-файлам)"
echo "======================================================================"
git ls-files -z \
  | xargs -0 grep -nIiE "$SECRET_RE" 2>/dev/null \
  | grep -viE "$SECRET_SKIP" \
  || echo "Совпадений с потенциальными секретами не найдено."
echo
echo "======================================================================"
echo " Удалённый репозиторий GitHub"
echo "======================================================================"
echo "\$ gh repo view getyrno/lab-03-git-github"
gh repo view getyrno/lab-03-git-github \
  --json name,url,visibility,description 2>&1
echo
echo "\$ gh api repos/getyrno/lab-03-git-github/commits"
gh api repos/getyrno/lab-03-git-github/commits \
  --jq '.[] | "\(.sha[0:7])  \(.commit.author.date)  \(.commit.message | split("\n")[0])"' 2>&1
echo
echo "\$ gh api repos/getyrno/lab-03-git-github/contents  (корень удалённого репозитория)"
gh api repos/getyrno/lab-03-git-github/contents \
  --jq '.[] | "\(.type)\t\(.name)"' 2>&1
echo
echo "Проверка доступности URL по HTTPS:"
curl -sS -o /dev/null -w "  https://github.com/getyrno/lab-03-git-github -> HTTP %{http_code}\n" \
  https://github.com/getyrno/lab-03-git-github
curl -sS -o /dev/null -w "  raw README.md -> HTTP %{http_code}\n" \
  https://raw.githubusercontent.com/getyrno/lab-03-git-github/main/README.md
} > "$OUT" 2>&1

echo "Записано: $OUT"
