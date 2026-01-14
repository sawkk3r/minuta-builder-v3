# 🚀 Guia de Deploy - TRE-GO Minuta Builder v2.0

Este guia explica como fazer deploy do MVP na internet para que seus colegas possam usar o sistema online.

---

## 📋 Pré-requisitos

- Conta em uma plataforma de deploy (Render, Railway, Fly.io, etc.)
- Repositório Git (GitHub, GitLab, etc.) com o código
- Chave da API OpenAI configurada

---

## 🎯 Opções de Deploy

### Opção 1: Render.com (Recomendado - Grátis)

**Vantagens:**
- ✅ Plano gratuito disponível
- ✅ Deploy automático via GitHub
- ✅ SSL/HTTPS automático
- ✅ Fácil configuração

**Passos:**

1. **Criar conta no Render**
   - Acesse https://render.com
   - Faça login com GitHub

2. **Conectar repositório**
   - Clique em "New +" → "Web Service"
   - Conecte seu repositório GitHub
   - Selecione o repositório `Minuta-Builder-v3`

3. **Configurar serviço**
   - **Name**: `tre-go-minuta-builder`
   - **Region**: Escolha a mais próxima (ex: `Oregon`)
   - **Branch**: `main` (ou sua branch principal)
   - **Root Directory**: Deixe vazio (raiz do projeto)
   - **Runtime**: `Docker`
   - **Dockerfile Path**: `Dockerfile`
   - **Docker Context**: `.` (ponto)

4. **Configurar variáveis de ambiente**
   ```
   OPENAI_API_KEY=sua-chave-aqui
   MODEL_AGENTES=gpt-5-mini-2025-08-07
   MODEL_COORDENADOR=gpt-5.2-2025-12-11
   EMBEDDING_MODEL=text-embedding-3-small
   ENVIRONMENT=production
   ```

5. **Configurar plano**
   - **Starter Plan** (grátis): 512MB RAM, 0.5 CPU
   - **Standard Plan** (pago): 2GB RAM, 1 CPU (recomendado para produção)

6. **Deploy**
   - Clique em "Create Web Service"
   - Aguarde o build e deploy (5-10 minutos)
   - Anote a URL gerada (ex: `https://tre-go-minuta-builder.onrender.com`)

7. **Configurar frontend**
   - O frontend detecta automaticamente a URL da API
   - Se o frontend estiver em outro lugar, edite `frontend/index.html` e ajuste as URLs

---

### Opção 2: Railway.app

**Vantagens:**
- ✅ Muito fácil de usar
- ✅ Deploy com um clique
- ✅ $5 grátis por mês

**Passos:**

1. **Criar conta**
   - Acesse https://railway.app
   - Faça login com GitHub

2. **Criar novo projeto**
   - Clique em "New Project"
   - Selecione "Deploy from GitHub repo"
   - Escolha seu repositório

3. **Configurar variáveis de ambiente**
   - Vá em "Variables"
   - Adicione:
     ```
     OPENAI_API_KEY=sua-chave-aqui
     MODEL_AGENTES=gpt-5-mini-2025-08-07
     MODEL_COORDENADOR=gpt-5.2-2025-12-11
     EMBEDDING_MODEL=text-embedding-3-small
     ```

4. **Deploy automático**
   - Railway detecta o `railway.json` automaticamente
   - O deploy inicia automaticamente
   - Aguarde o build (5-10 minutos)

5. **Obter URL**
   - Vá em "Settings" → "Generate Domain"
   - Anote a URL gerada

---

### Opção 3: Fly.io

**Vantagens:**
- ✅ Muito rápido
- ✅ Global edge network
- ✅ Plano gratuito generoso

**Passos:**

1. **Instalar Fly CLI**
   ```bash
   # Mac
   brew install flyctl
   
   # Windows (PowerShell)
   powershell -Command "iwr https://fly.io/install.ps1 -useb | iex"
   
   # Linux
   curl -L https://fly.io/install.sh | sh
   ```

2. **Login**
   ```bash
   fly auth login
   ```

3. **Criar app**
   ```bash
   cd tre-go-minuta-builder-v2
   fly launch
   ```
   - Siga as instruções interativas
   - Escolha região próxima
   - Não crie banco de dados (não necessário)

4. **Configurar secrets**
   ```bash
   fly secrets set OPENAI_API_KEY=sua-chave-aqui
   fly secrets set MODEL_AGENTES=gpt-5-mini-2025-08-07
   fly secrets set MODEL_COORDENADOR=gpt-5.2-2025-12-11
   ```

5. **Deploy**
   ```bash
   fly deploy
   ```

6. **Obter URL**
   ```bash
   fly open
   ```

---

### Opção 4: Deploy com Docker Compose (VPS/Servidor próprio)

Se você tem um servidor próprio (VPS, AWS EC2, etc.):

**Passos:**

1. **Preparar servidor**
   ```bash
   # Instalar Docker e Docker Compose
   curl -fsSL https://get.docker.com -o get-docker.sh
   sh get-docker.sh
   
   # Instalar Docker Compose
   sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   ```

2. **Clonar repositório**
   ```bash
   git clone https://github.com/seu-usuario/Minuta-Builder-v3.git
   cd Minuta-Builder-v3/tre-go-minuta-builder-v2
   ```

3. **Criar arquivo .env**
   ```bash
   cp .env.example .env
   nano .env
   ```
   
   Adicione:
   ```env
   OPENAI_API_KEY=sua-chave-aqui
   MODEL_AGENTES=gpt-5-mini-2025-08-07
   MODEL_COORDENADOR=gpt-5.2-2025-12-11
   EMBEDDING_MODEL=text-embedding-3-small
   API_PORT=8000
   ```

4. **Iniciar serviços**
   ```bash
   docker-compose up -d
   ```

5. **Configurar Nginx (opcional, para HTTPS)**
   ```nginx
   server {
       listen 80;
       server_name seu-dominio.com;
       
       location / {
           proxy_pass http://localhost:8000;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
       }
   }
   ```

---

## 🌐 Configurar Frontend para Produção

O frontend detecta automaticamente se está rodando localmente ou em produção. Se você quiser servir o frontend separadamente:

### Opção A: Frontend no mesmo domínio (Recomendado)

1. **Modificar FastAPI para servir arquivos estáticos**
   
   Adicione em `backend/api.py`:
   ```python
   from fastapi.staticfiles import StaticFiles
   
   # Servir frontend
   app.mount("/", StaticFiles(directory="frontend", html=True), name="static")
   ```

2. **Rebuild e redeploy**

### Opção B: Frontend em serviço separado (Netlify, Vercel)

1. **Fazer deploy do frontend**
   - Netlify: Arraste a pasta `frontend/` para https://app.netlify.com/drop
   - Vercel: `vercel deploy frontend/`

2. **Configurar variáveis de ambiente no frontend**
   - Crie um arquivo `frontend/config.js`:
     ```javascript
     window.API_URL = 'https://sua-api-url.com';
     window.WS_URL = 'wss://sua-api-url.com';
     ```
   - Inclua no `index.html` antes do script principal:
     ```html
     <script src="config.js"></script>
     ```

---

## ✅ Verificação Pós-Deploy

Após o deploy, verifique:

1. **Health Check**
   ```bash
   curl https://sua-url.com/status
   ```
   Deve retornar JSON com status do sistema.

2. **API Docs**
   Acesse: `https://sua-url.com/docs`
   Deve mostrar a documentação Swagger.

3. **Frontend**
   Acesse a URL do frontend e teste criar uma sessão.

---

## 🔧 Troubleshooting

### Erro: "OPENAI_API_KEY não encontrada"
- Verifique se a variável de ambiente está configurada na plataforma
- Reinicie o serviço após adicionar variáveis

### Erro: "Port already in use"
- Verifique se outra aplicação não está usando a porta
- Configure `PORT` como variável de ambiente (algumas plataformas exigem)

### Erro: "Module not found"
- Verifique se todas as dependências estão no `requirements.txt`
- Rebuild o container Docker

### WebSocket não conecta
- Verifique se a plataforma suporta WebSockets
- Algumas plataformas exigem configuração adicional para WebSockets

### Frontend não encontra API
- Verifique se as URLs estão corretas
- Verifique CORS no backend (já configurado para `*`)

---

## 📊 Monitoramento

### Logs

- **Render**: Vá em "Logs" no painel
- **Railway**: Vá em "Deployments" → "View Logs"
- **Fly.io**: `fly logs`

### Métricas

- **Render**: Dashboard mostra CPU, RAM, requisições
- **Railway**: Dashboard mostra uso de recursos
- **Fly.io**: `fly metrics`

---

## 🔒 Segurança em Produção

⚠️ **IMPORTANTE**: Para produção, considere:

1. **CORS Restritivo**
   - Edite `backend/api.py`:
     ```python
     allow_origins=["https://seu-dominio.com"]  # Apenas seu domínio
     ```

2. **Rate Limiting**
   - Adicione middleware de rate limiting (veja `ANALISE_MELHORIAS.md`)

3. **HTTPS Obrigatório**
   - Todas as plataformas modernas fornecem HTTPS automático

4. **Variáveis de Ambiente Seguras**
   - Nunca commite `.env` no Git
   - Use secrets da plataforma

---

## 📝 Checklist de Deploy

- [ ] Código commitado no repositório Git
- [ ] Variáveis de ambiente configuradas
- [ ] Dockerfile testado localmente
- [ ] Deploy realizado com sucesso
- [ ] Health check passando
- [ ] Frontend acessível
- [ ] WebSocket funcionando
- [ ] Teste completo de criação de sessão
- [ ] Documentação atualizada com URL de produção

---

## 🆘 Suporte

Se encontrar problemas:

1. Verifique os logs da plataforma
2. Teste localmente com Docker: `docker-compose up`
3. Verifique a documentação da plataforma escolhida
4. Consulte `ANALISE_MELHORIAS.md` para melhorias de segurança

---

**Boa sorte com o deploy! 🚀**
