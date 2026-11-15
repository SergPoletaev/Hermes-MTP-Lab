# Публикация и обновление Hermes MTP Lab через GitHub Desktop

**Без ручного пересчёта SHA-256, манифеста хешей и редактирования отдельных файлов на GitHub.**

## Если репозиторий `Hermes-MTP-Lab` уже опубликован

Не удаляйте репозиторий и не пересоздавайте Git-историю. Это обновление исправляет структуру пакета для обычного Hermes → **Install from Git**.

1. Распакуйте комплект `v0.3.2`. В GitHub Desktop выберите текущий `Hermes-MTP-Lab` → **Repository → Show in Explorer**.
2. В проводнике **удалите старую папку `hermes-mtp-lab/`** внутри репозитория: исходники теперь находятся в его корне. Удаляйте именно эту подпапку, **не репозиторий и не `.git`**.
3. Скопируйте **всё содержимое** новой папки `Hermes-MTP-Lab/` из архива поверх существующего репозитория с заменой файлов. `RELEASE_ASSETS` копировать в Git не нужно.
4. GitHub Desktop покажет перемещения/удаления старых путей, добавление `plugin.yaml`, `__init__.py`, `desktop/`, `dashboard/`, `data/`, `tests/`, а также изменения CI, установщика и документации.
5. Commit `Make plugin discoverable at Git repository root v0.3.2` → **Push origin**. Дождитесь двух зелёных заданий Actions.
6. В Hermes Desktop выберите Install from Git с обычным URL: `https://github.com/SergPoletaev/Hermes-MTP-Lab.git` — **без `#hermes-mtp-lab`**. При уже установленном плагине может понадобиться подтверждение замены/переустановки.

Старый релиз `v0.3.0` остаётся историческим. Если выпускаете новую архивную сборку, используйте отдельный тег `v0.3.2`, не подменяйте вложения опубликованного тега.

## Если создаёте новый репозиторий

1. В GitHub Desktop откройте File → Add local repository → Choose, укажите только `Hermes-MTP-Lab/`.
2. Подтвердите создание локального репозитория в этой папке, если предложено. Существующие README, `.gitignore` и лицензию не дублируйте.
3. Создайте первый коммит и нажмите Publish repository. Для публичного проекта снимите Keep this code private.
4. После зелёного CI создайте GitHub Release с тегом `v0.3.2`, прикрепите `RELEASE_ASSETS/Hermes_MTP_Lab_v0.3.2_PORTABLE_INSTALL.zip`. Отдельный FULL_SOURCE.zip необязателен: GitHub автоматически предоставляет Source code.
5. Отметьте Pre-release: v0.3.2 пока не подтверждена реальным универсальным тестом в Hermes Desktop.

**Состав комплекта:** исходники `Hermes-MTP-Lab/`, готовые архивы `RELEASE_ASSETS/` и инструкция. Архивы релиза не включайте в Git-коммит.

## Необязательные локальные проверки (без хешей)

```text
python tools/verify_repo.py
python -m unittest discover -s tests -p "test_*.py" -v
node tests/test_desktop_registration.cjs
python tools/package_release.py --output dist
python tools/check_dist.py --directory dist
```

`check_dist.py` автоматически открывает оба ZIP и сравнивает их файлы с текущими исходниками. От вас никаких контрольных сумм не требуется.
