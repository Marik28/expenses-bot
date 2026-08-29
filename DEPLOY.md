# Деплой

Автодеплой на сервер через GitHub Actions — `.github/workflows/deploy.yml`.
Запуск **только вручную**: вкладка **Actions → Deploy → Run workflow**, поле `ref`
(ветка / тег / SHA, по умолчанию `main`).

## Что делает workflow

Заходит на сервер по SSH и в каталоге `DEPLOY_PATH`:

1. `git fetch` + `git reset --hard origin/<ref>` — обновляет код (локальные правки на сервере затираются; `.env` в `.gitignore`, не трогается);
2. полностью перезаписывает `.env` содержимым секрета `ENV_FILE`;
3. `docker compose build`;
4. поднимает `db` и `redis`, ждёт готовности Postgres;
5. `docker compose run --rm bot alembic upgrade head` — миграции;
6. `docker compose up -d bot` — перезапуск бота на новом образе;
7. `docker image prune -f`.

## Секреты репозитория

**Settings → Secrets and variables → Actions → New repository secret:**

| Секрет        | Значение                                                                 |
|---------------|-------------------------------------------------------------------------|
| `SSH_HOST`    | IP или домен сервера                                                    |
| `SSH_USER`    | пользователь для SSH (например `deploy`)                               |
| `SSH_PORT`    | порт SSH (`22`)                                                        |
| `SSH_KEY`     | **приватный** ключ деплой-пары (целиком, с `-----BEGIN…`)             |
| `DEPLOY_PATH` | абсолютный путь к клонированному репозиторию на сервере                |
| `ENV_FILE`    | полное содержимое `.env` для сервера (см. ниже)                        |

## Деплой-ключ SSH

На локальной машине:

```bash
ssh-keygen -t ed25519 -f deploy_key -N "" -C "github-actions-deploy"
```

На сервере — добавить публичный ключ пользователю деплоя:

```bash
cat deploy_key.pub >> ~/.ssh/authorized_keys
```

Приватный ключ положить в секрет `SSH_KEY`, затем удалить локальные файлы:

```bash
gh secret set SSH_KEY < deploy_key
rm deploy_key deploy_key.pub
```

## Переменные окружения (`ENV_FILE`)

Единый источник правды для серверного `.env` — секрет `ENV_FILE`. Workflow при
каждом запуске **перезаписывает** `.env` на сервере целиком, поэтому новые и
изменённые переменные подхватываются без правок workflow.

Залить/обновить (из корня репозитория, файл `.env` с боевыми значениями):

```bash
gh secret set ENV_FILE < .env
```

Порядок при добавлении новой переменной:

1. добавить её в `.env-example` (документация) и в свой боевой `.env`;
2. `gh secret set ENV_FILE < .env`;
3. запустить workflow **Deploy**.

Важно для боевого `.env` (сеть внутри compose):

```
DB_URL=postgresql://<POSTGRES_USER>:<POSTGRES_PASSWORD>@db:5432/<POSTGRES_DB>
REDIS_URL=redis://redis:6379/0
```

## Откат

Запустить **Deploy** с `ref` = предыдущий тег или SHA. Код и образ бота
вернутся к этой версии; миграции назад автоматически не откатываются —
при необходимости `docker compose run --rm bot alembic downgrade -1`.

## Первичная настройка сервера (справочно)

```bash
git clone git@github.com:Marik28/expenses-bot.git /opt/expenses-bot
cd /opt/expenses-bot
# создать .env (или дождаться первого деплоя — workflow его перезапишет)
```

`DEPLOY_PATH` = `/opt/expenses-bot`. Пользователь `SSH_USER` должен быть в группе
`docker` и иметь права на запись в этот каталог.
