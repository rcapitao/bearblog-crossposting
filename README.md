# bearblog-crossposting

Automação que crossposta novos posts do blog [rcapitao.com](https://www.rcapitao.com) (hospedado no Bear Blog) para o **Mastodon** e o **Bluesky**, lendo o feed RSS do blog.

Funciona via GitHub Actions: a cada 20 minutos verifica o feed, deteta posts novos (comparando com `state.json`) e publica neles a mensagem no formato:

```
Título do post - link
Meta description do post
```

## Como funciona

1. `crosspost.py` lê o feed RSS (`FEED_URL`).
2. Compara os links com os já registados em `state.json`.
3. Para cada post novo, publica no Mastodon e no Bluesky.
4. Atualiza `state.json` e o workflow faz commit desse ficheiro.

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

O workflow `.github/workflows/crosspost.yml` já corre automaticamente a cada 20 minutos depois do push. Também podes disparar manualmente em **Actions → Crosspost new blog posts → Run workflow**.

## Sobre o Threads

O Threads (Meta) não tem uma forma simples de publicar sem usar a Threads API oficial, que exige criar uma app no Meta for Developers, associar uma conta Instagram Business e passar por processo de revisão. Por isso não está incluído por agora — pode ser adicionado mais tarde se quiseres avançar com esse processo.

## Estrutura

- `crosspost.py` — script principal.
- `requirements.txt` — dependências Python.
- `state.json` — registo dos posts já crosspostados (atualizado automaticamente).
- `.github/workflows/crosspost.yml` — workflow agendado.
