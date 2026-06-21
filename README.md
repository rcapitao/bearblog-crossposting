# bearblog-crossposting

Automação que crossposta novos posts do blog [rcapitao.com](https://www.rcapitao.com) (hospedado no Bear Blog) para o **Mastodon** e o **Bluesky**, lendo o feed RSS do blog.

## Visão geral

A automação corre como um workflow agendado no GitHub Actions:

1. A cada 20 minutos (ou manualmente), o workflow `.github/workflows/crosspost.yml` arranca uma máquina temporária, instala as dependências Python e corre `crosspost.py`.
2. `crosspost.py` lê o feed RSS configurado em `FEED_URL`.
3. Compara os links dos posts do feed com os já registados em `state.json` (o "registo do que já foi publicado").
4. Para cada post novo (do mais antigo para o mais recente), publica uma mensagem no Mastodon e no Bluesky.
5. Atualiza `state.json` com os links recém-publicados e o workflow faz commit + push automático desse ficheiro no repositório.

Não há servidor a correr 24/7 nem webhook do Bear Blog — a deteção é por **polling** do feed RSS.

## Formato da mensagem publicada

```
Título do post - link
Meta description do post
```

- A primeira linha junta o título e o link do post.
- A segunda linha é a meta description do post, extraída do campo `summary`/`description` do RSS (com tags HTML removidas).
- No Bluesky, o link na primeira linha é publicado como link clicável (rich text facet), não como texto simples.
- Se o post não tiver meta description, só é publicada a primeira linha.

## Redes suportadas

| Rede | Suportado | Autenticação |
|---|---|---|
| Mastodon | ✅ | Access token de uma aplicação OAuth |
| Bluesky | ✅ | App Password (AT Protocol) |
| Threads | ❌ (por agora) | — |

Cada rede é independente: se as variáveis/secrets de uma rede não estiverem definidas, o script simplesmente ignora essa rede e publica só nas restantes (ver `post_to_mastodon` e `post_to_bluesky` em `crosspost.py`).

### Sobre o Threads

O Threads (Meta) não tem uma forma simples de publicar sem usar a Threads API oficial, que exige criar uma app no Meta for Developers, associar uma conta Instagram Business e passar por processo de revisão. Por isso não está incluído por agora — pode ser adicionado mais tarde se quiseres avançar com esse processo.

## Setup

### 1. Descobrir o URL do feed RSS

O feed RSS deste blog está em `https://www.rcapitao.com/feed/`.

### 2. Criar o token do Mastodon

1. Entra na tua instância Mastodon (web).
2. Vai a **Preferências → Desenvolvimento → Nova aplicação**.
3. Dá um nome (ex: `bearblog-crossposting`) e marca o scope `write:statuses`.
4. Cria a aplicação e copia o **access token** gerado.
5. Anota também o URL base da tua instância (ex: `https://mastodon.social`).

### 3. Criar o App Password do Bluesky

1. Entra em [bsky.app](https://bsky.app) → **Settings → App Passwords**.
2. Cria um novo App Password (não usar a password principal da conta).
3. Anota o handle da conta (ex: `rcapitao.bsky.social`) e o App Password gerado.

### 4. Configurar variáveis e secrets no repositório GitHub

Em **Settings → Secrets and variables → Actions** deste repositório:

**Variables** (não sensíveis):
- `FEED_URL` — ex: `https://www.rcapitao.com/feed/`
- `MASTODON_BASE_URL` — ex: `https://mastodon.social`
- `BLUESKY_HANDLE` — ex: `rcapitao.bsky.social`

**Secrets** (sensíveis):
- `MASTODON_ACCESS_TOKEN`
- `BLUESKY_APP_PASSWORD`

Se quiseres usar só uma das duas redes, basta não definir as variáveis/secrets dessa rede — o script ignora-a automaticamente.

### 5. Seed inicial (evitar crosspostar todo o histórico)

Antes de ativar o agendamento, marca os posts já existentes como já publicados, sem os postar:

1. Vai a **Actions → Crosspost new blog posts → Run workflow**.
2. Marca a opção `seed_only`.
3. Corre o workflow.

Isto regista todos os posts atuais do feed em `state.json` e faz commit automático desse ficheiro. A partir daí, as execuções seguintes (agendadas ou manuais sem `seed_only`) só vão crosspostar posts realmente novos.

Alternativa local (se preferires correr fora do GitHub Actions):

```bash
pip install -r requirements.txt
export FEED_URL="https://www.rcapitao.com/feed/"
SEED_ONLY=1 python crosspost.py
git add state.json
git commit -m "Seed crosspost state with existing posts"
git push
```

### 6. Ativar o workflow

O workflow `.github/workflows/crosspost.yml` já corre automaticamente a cada 20 minutos depois do push para `main`. Também podes disparar manualmente em **Actions → Crosspost new blog posts → Run workflow**.

## Operação do dia a dia

- **Publicar um post novo no blog** é suficiente — na próxima execução agendada (até 20 min depois) o workflow deteta e crossposta automaticamente.
- **Forçar uma verificação imediata**: **Actions → Crosspost new blog posts → Run workflow** (sem marcar `seed_only`).
- **Ver o histórico de execuções e logs**: separador **Actions** do repositório.
- **Confirmar o que já foi publicado**: ficheiro `state.json` na raiz do repositório (lista de links já crosspostados).
- **Reenviar um post manualmente**: remover o link correspondente de `state.json`, fazer commit/push, e correr o workflow manualmente — o post volta a ser tratado como novo.
- **Desativar temporariamente**: em **Settings → Actions → General**, desativar as Actions do repositório, ou remover/comentar o gatilho `schedule` no workflow.

## Troubleshooting

- **Nada é publicado**: confirma que `FEED_URL` está correto e acessível publicamente, e que pelo menos um par de credenciais (Mastodon ou Bluesky) está configurado nas secrets/variables.
- **Erro de autenticação no Mastodon**: o access token pode ter expirado ou não ter o scope `write:statuses` — gera um novo token.
- **Erro de autenticação no Bluesky**: confirma que `BLUESKY_HANDLE` é o handle completo (ex: `rcapitao.bsky.social`) e que `BLUESKY_APP_PASSWORD` é um App Password válido (não a password da conta).
- **Posts antigos foram crosspostados de repente**: provavelmente o `state.json` foi perdido ou nunca foi seedado — repete o passo de seed inicial.
- **O workflow falha ao fazer commit do `state.json`**: confirma que a permissão `contents: write` está definida no workflow (já está por defeito neste repositório) e que não há proteção de branch a bloquear pushes diretos do `github-actions[bot]`.

## Estrutura

- `crosspost.py` — script principal: lê o feed, decide o que é novo, publica e atualiza o estado.
- `requirements.txt` — dependências Python (`feedparser`, `requests`).
- `state.json` — registo dos posts já crosspostados (atualizado automaticamente pelo workflow).
- `.github/workflows/crosspost.yml` — workflow agendado do GitHub Actions, com gatilho `schedule` e `workflow_dispatch` (incluindo a opção `seed_only`).
