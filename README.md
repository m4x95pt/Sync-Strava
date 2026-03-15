# Sync-Strava

Script Python que sincroniza automaticamente atividades do Strava para uma base de dados Notion. Corre via GitHub Actions duas vezes por dia.

## O que faz

- Autentica na API do Strava via OAuth2 (refresh token)
- Busca atividades recentes (corridas, treinos, etc.)
- Cria ou atualiza entradas na base de dados Notion correspondente
- Evita duplicados verificando atividades já existentes

## Stack

- **Linguagem:** Python 3
- **APIs:** Strava API v3, Notion API
- **CI/CD:** GitHub Actions (cron job)

## Schedule

```
Corre todos os dias às 09:00 e 10:00 (hora de Lisboa)
```

## Variáveis de ambiente / Secrets

```env
STRAVA_CLIENT_ID=...
STRAVA_CLIENT_SECRET=...
STRAVA_REFRESH_TOKEN=...
NOTION_TOKEN=...
NOTION_DATABASE_ID=...
```

No GitHub: **Settings → Secrets and variables → Actions**

## Instalação local

```bash
git clone https://github.com/m4x95pt/Sync-Strava
cd Sync-Strava
pip install -r requirements.txt
cp .env.example .env
# Preenche as variáveis
python main.py
```

## GitHub Actions

O workflow `.github/workflows/sync.yml` corre automaticamente:

```yaml
schedule:
  - cron: "0 8 * * *"   # 09:00 Lisboa
  - cron: "0 9 * * *"   # 10:00 Lisboa
```

Também pode ser acionado manualmente via **Actions → Run workflow**.

## Notas

- O `STRAVA_REFRESH_TOKEN` expira se não for usado — se o sync parar, regenera o token na [Strava API settings](https://www.strava.com/settings/api)
- Certifica-te que a integração Notion tem acesso à base de dados correta
