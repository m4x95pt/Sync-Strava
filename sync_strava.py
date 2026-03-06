import os
import requests
from datetime import datetime, timezone

# ─── Config ──────────────────────────────────────────────────────────────────
STRAVA_CLIENT_ID     = os.environ["STRAVA_CLIENT_ID"]
STRAVA_CLIENT_SECRET = os.environ["STRAVA_CLIENT_SECRET"]
STRAVA_REFRESH_TOKEN = os.environ["STRAVA_REFRESH_TOKEN"]
NOTION_TOKEN         = os.environ["NOTION_TOKEN"]
STRAVA_DB_ID         = "75bd9681-1606-4d95-9a05-bf1b3d59d162"

NOTION_HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Notion-Version": "2022-06-28",
    "Content-Type": "application/json",
}

# Tipos de actividade Strava → Notion
TIPO_MAP = {
    "Run":           "Corrida",
    "TrailRun":      "Corrida",
    "Ride":          "Ciclismo",
    "VirtualRide":   "Ciclismo",
    "Walk":          "Caminhada",
    "Hike":          "Caminhada",
    "Swim":          "Natação",
}


# ─── Strava: obter access token ──────────────────────────────────────────────

def get_access_token():
    resp = requests.post(
        "https://www.strava.com/oauth/token",
        data={
            "client_id":     STRAVA_CLIENT_ID,
            "client_secret": STRAVA_CLIENT_SECRET,
            "refresh_token": STRAVA_REFRESH_TOKEN,
            "grant_type":    "refresh_token",
        },
    )
    resp.raise_for_status()
    token = resp.json()["access_token"]
    print("✅ Strava: token obtido")
    return token


# ─── Strava: buscar actividades recentes ─────────────────────────────────────

def get_strava_activities(token, per_page=20):
    resp = requests.get(
        "https://www.strava.com/api/v3/athlete/activities",
        headers={"Authorization": f"Bearer {token}"},
        params={"per_page": per_page, "page": 1},
    )
    resp.raise_for_status()
    activities = resp.json()
    print(f"✅ Strava: {len(activities)} actividade(s) encontradas")
    return activities


# ─── Strava: buscar detalhes completos de uma actividade ─────────────────────

def get_activity_detail(token, activity_id):
    resp = requests.get(
        f"https://www.strava.com/api/v3/activities/{activity_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    resp.raise_for_status()
    return resp.json()


# ─── Formatters ──────────────────────────────────────────────────────────────

def format_tempo(seconds):
    """Converte segundos em HH:MM:SS ou MM:SS."""
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    return f"{m}m {s:02d}s"


def format_pace(speed_ms, tipo):
    """Converte m/s em pace min/km (para corrida/caminhada) ou km/h (para ciclismo)."""
    if speed_ms == 0:
        return "—"
    if tipo in ("Corrida", "Caminhada"):
        pace_s = 1000 / speed_ms  # segundos por km
        m = int(pace_s // 60)
        s = int(pace_s % 60)
        return f"{m}:{s:02d} /km"
    else:
        return f"{speed_ms * 3.6:.1f} km/h"


# ─── Notion: verificar actividades já existentes ─────────────────────────────

def get_existing_strava_ids():
    """Busca os IDs do Strava já registados no Notion (via Link Strava)."""
    existing = set()
    has_more = True
    cursor = None

    while has_more:
        body = {"page_size": 100}
        if cursor:
            body["start_cursor"] = cursor

        resp = requests.post(
            f"https://api.notion.com/v1/databases/{STRAVA_DB_ID}/query",
            headers=NOTION_HEADERS,
            json=body,
        )
        resp.raise_for_status()
        data = resp.json()

        for page in data.get("results", []):
            url = page.get("properties", {}).get("Link Strava", {}).get("url", "")
            if url:
                # Extrair ID do URL: https://www.strava.com/activities/12345678
                parts = url.rstrip("/").split("/")
                if parts:
                    existing.add(parts[-1])

        has_more = data.get("has_more", False)
        cursor = data.get("next_cursor")

    print(f"✅ Notion: {len(existing)} actividade(s) já registada(s)")
    return existing


# ─── Notion: criar entrada ────────────────────────────────────────────────────

def create_notion_entry(activity):
    tipo_strava = activity.get("sport_type") or activity.get("type", "")
    tipo = TIPO_MAP.get(tipo_strava, "Outro")

    distancia_km = round(activity.get("distance", 0) / 1000, 2)
    tempo_s      = activity.get("moving_time", 0)
    velocidade   = activity.get("average_speed", 0)
    bpm_medio    = activity.get("average_heartrate")
    bpm_max      = activity.get("max_heartrate")
    elevacao     = activity.get("total_elevation_gain")
    calorias     = activity.get("calories")
    titulo       = activity.get("name", "Treino")
    activity_id  = activity.get("id")

    # Data da actividade
    data_iso = activity.get("start_date_local", "")[:10]  # YYYY-MM-DD

    # Nome da entrada: "Corrida · 6 Mar"
    try:
        data_fmt = datetime.strptime(data_iso, "%Y-%m-%d").strftime("%-d %b")
    except Exception:
        data_fmt = data_iso
    nome = f"{tipo} · {data_fmt}"

    pace = format_pace(velocidade, tipo)
    tempo_fmt = format_tempo(tempo_s)
    velocidade_kmh = round(velocidade * 3.6, 1)
    link = f"https://www.strava.com/activities/{activity_id}"

    body = {
        "parent": {"database_id": "d81e0ca8455944eea8606190c31cb75b"},
        "properties": {
            "Name":               {"title": [{"text": {"content": nome}}]},
            "Tipo":               {"select": {"name": tipo}},
            "Título Strava":      {"rich_text": [{"text": {"content": titulo}}]},
            "Distância (km)":     {"number": distancia_km},
            "Tempo":              {"rich_text": [{"text": {"content": tempo_fmt}}]},
            "Pace Médio":         {"rich_text": [{"text": {"content": pace}}]},
            "Velocidade Média (km/h)": {"number": velocidade_kmh},
            "Link Strava":        {"url": link},
            "date:Data:start":    data_iso,
            "date:Data:is_datetime": 0,
        },
    }

    # Campos opcionais (podem não existir em todas as actividades)
    if bpm_medio:
        body["properties"]["BPM Médio"] = {"number": round(bpm_medio)}
    if bpm_max:
        body["properties"]["BPM Máximo"] = {"number": round(bpm_max)}
    if elevacao is not None:
        body["properties"]["Elevação (m)"] = {"number": round(elevacao)}
    if calorias:
        body["properties"]["Calorias"] = {"number": round(calorias)}

    # Fixme: a API do Notion não aceita date: como key directamente — usar properties normais
    body["properties"].pop("date:Data:start", None)
    body["properties"].pop("date:Data:is_datetime", None)
    body["properties"]["Data"] = {"date": {"start": data_iso}}

    resp = requests.post(
        "https://api.notion.com/v1/pages",
        headers=NOTION_HEADERS,
        json=body,
    )
    resp.raise_for_status()
    print(f"  ✅ Criada: {nome} — {distancia_km} km · {tempo_fmt} · {pace}")


# ─── Main ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("🔑 A obter token do Strava...")
    token = get_access_token()

    print("\n🏃 A buscar actividades do Strava...")
    activities = get_strava_activities(token, per_page=30)

    print("\n📋 A verificar o que já está no Notion...")
    existing_ids = get_existing_strava_ids()

    print("\n🔄 A sincronizar actividades novas...")
    criadas = 0
    ignoradas = 0

    for a in activities:
        activity_id = str(a.get("id", ""))
        if activity_id in existing_ids:
            ignoradas += 1
            continue

        try:
            create_notion_entry(a)
            criadas += 1
        except Exception as e:
            print(f"  ⚠️  Erro em {a.get('name', '?')}: {e}")

    print(f"\n✅ Sync concluído!")
    print(f"   → {criadas} actividade(s) nova(s) adicionada(s)")
    print(f"   → {ignoradas} actividade(s) já existiam")
