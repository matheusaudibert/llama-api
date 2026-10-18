# Fortnite Account API

API HTTP para logar em contas Epic Games (device code flow) e ler os dados do Fortnite: conta, V-Bucks, estatísticas e locker completo. Feita para servir de backend a bots de Discord que mostram as skins dos jogadores.

## Endpoints

| Método | Rota | Descrição |
|---|---|---|
| `POST` | `/auth/device` | Inicia um login e devolve o link de autorização da Epic |
| `GET` | `/auth/{session_id}` | Status do login (`pending`, `completed`, `expired`, `error`) |
| `DELETE` | `/auth/{session_id}` | Encerra a sessão e invalida o token na Epic |
| `GET` | `/accounts/{session_id}/summary` | Dados da conta, V-Bucks, plataformas e estatísticas |
| `GET` | `/accounts/{session_id}/locker` | Todos os cosméticos, por categoria e ordenados por raridade |
| `POST` | `/render/{category}` | PNG do locker por categoria (`skins`, `backpacks`, `pickaxes`, `gliders`, `emotes`, `mythics`) |
| `GET` | `/health` | Healthcheck (sem API key) |

Todos os endpoints, menos `/health`, exigem o header `X-API-Key`.

## Rodando

```bash
pip install -r requirements.txt
API_KEY="sua-chave" uvicorn api.main:app --port 8000
```

Ou com Docker:

```bash
docker build -t fortnite-account-api .
docker run -p 8000:8000 -e API_KEY="sua-chave" fortnite-account-api
```

Swagger UI em `http://localhost:8000/docs`.

## Documentação

A documentação completa (guias, deploy com Docker, exemplo com discord.js e referência da API) fica em [`docs/`](docs) e é publicada com o [Mintlify](https://mintlify.com).

Para rodar a documentação localmente:

```bash
npm i -g mint
cd docs
mint dev
```

Depois de mudar endpoints ou modelos, regenere o spec:

```bash
python scripts/export_openapi.py
```

## Aviso

A API usa client IDs de apps oficiais da Epic (Switch e iOS) de forma não oficial. A Epic pode bloquear esse uso a qualquer momento, e ele não é permitido pelos termos de serviço da Epic. Use por sua conta e risco.