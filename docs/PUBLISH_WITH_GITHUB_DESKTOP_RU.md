# Публикация и обновление Hermes MTP Lab через GitHub Desktop

**Без ручного пересчёта SHA-256, манифеста хешей и редактирования отдельных файлов на GitHub.**

## Если репозиторий `Hermes-MTP-Lab` уже опубликован

1. Распакуйте полный комплект. Откройте существующий локальный репозиторий в GitHub Desktop → **Repository → Show in Explorer**.
2. Скопируйте **всё содержимое** папки `Hermes-MTP-Lab/` из нового комплекта в эту папку с заменой. Чтобы убрать устаревшие проверки, удалите старый `BUILD-MANIFEST.json`, если он ещё остался. Скрытую папку **`.git` не удаляйте**.
3. Вернитесь в GitHub Desktop. Во вкладке Changes убедитесь, что видны ожидаемые изменения и удаление `BUILD-MANIFEST.json`. Не копируйте `RELEASE_ASSETS` в репозиторий.
4. Создайте коммит, например `Remove manual SHA tracking from build and CI`, и нажмите **Push origin**.
5. Откройте Actions → `Validate Hermes MTP Lab source release`. Дождитесь успешных `source-tests` и `windows-package`.

После этого меняйте README, Python, JS и другие исходники обычными коммитами. Больше **не нужно обновлять SHA-файл или BUILD-MANIFEST**. CI сам проверяет структуру, версии, тесты, синтаксис и содержимое собранных ZIP.

## Если создаёте новый репозиторий

1. В GitHub Desktop откройте File → Add local repository → Choose, укажите только `Hermes-MTP-Lab/`.
2. Подтвердите создание локального репозитория в этой папке, если предложено. Существующие README, `.gitignore` и лицензию не дублируйте.
3. Создайте первый коммит и нажмите Publish repository. Для публичного проекта снимите Keep this code private.
4. После зелёного CI создайте GitHub Release с тегом `v0.3.0`, прикрепите `RELEASE_ASSETS/Hermes_MTP_Lab_v0.3.0_PORTABLE_INSTALL.zip`. Отдельный FULL_SOURCE.zip необязателен: GitHub автоматически предоставляет Source code.
5. Отметьте Pre-release: v0.3.0 пока не подтверждена реальным универсальным тестом в Hermes Desktop.

**Состав комплекта:** исходники `Hermes-MTP-Lab/`, готовые архивы `RELEASE_ASSETS/` и инструкция. Архивы релиза не включайте в Git-коммит.

## Необязательные локальные проверки (без хешей)

```text
python tools/verify_repo.py
python -m unittest discover -s hermes-mtp-lab/tests -p "test_*.py" -v
node hermes-mtp-lab/tests/test_desktop_registration.cjs
python tools/package_release.py --output dist
python tools/check_dist.py --directory dist
```

`check_dist.py` автоматически открывает оба ZIP и сравнивает их файлы с текущими исходниками. От вас никаких контрольных сумм не требуется.
