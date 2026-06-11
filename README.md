# Swift NPS Analytics

Projeto de análise de NPS da Swift com backend Python (Flask) e frontend HTML.

## Estrutura

```
SwiftNPS/
├── backend/
│   ├── api.py            # API Flask com todos os endpoints
│   └── requirements.txt  # Dependências Python
├── frontend/
│   └── index.html        # Dashboard (consome a API via fetch)
└── run.sh                # Script para subir tudo com um comando
```

## Como rodar

```bash
cd SwiftNPS
chmod +x run.sh
./run.sh
```

O script instala as dependências, sobe o backend na porta `5000`, o frontend na porta `8080` e abre o navegador automaticamente.

## Endpoints da API

| Endpoint | Descrição | Filtros |
|---|---|---|
| `GET /api/big-numbers` | KPIs gerais (NPS, totais, %) | `from`, `to`, `flag` |
| `GET /api/nps-mensal` | NPS e distribuição por mês | `from`, `to`, `flag` |
| `GET /api/volume-mensal` | Volume de avaliações por mês | `from`, `to`, `flag` |
| `GET /api/ranking-lojas` | Top 5 e bottom 5 por NPS | `from`, `to`, `flag` |
| `GET /api/volume-lojas` | Lojas mais/menos avaliadas | — |
| `GET /api/detratores-regiao` | % detratores por região | — |
| `GET /api/flag-comparison` | Regular vs. Tocadora | — |
| `GET /api/word-cloud` | Top 80 palavras dos detratores | — |
| `GET /api/temas` | Categorias BERTopic | — |
| `GET /api/comprimento-comentarios` | Média/mediana palavras por classe | — |
| `GET /api/cobertura-comentarios` | % avaliações com comentário | — |

## Bases de dados

Esperadas em `../BasesDadosUtilizadas/`:
- `Dados para o Grillo.xlsx`
- `Transacoes Lojas.xlsx`
