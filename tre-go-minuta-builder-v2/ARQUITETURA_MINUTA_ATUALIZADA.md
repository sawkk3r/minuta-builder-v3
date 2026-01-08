# 🏗️ Arquitetura: Geração de Minuta Atualizada por Sessão

## 📋 Visão Geral

Sistema que permite gerar versões atualizadas da minuta (`minuta.txt`) baseadas nas interações de cada sessão, **sem alterar o arquivo original**.

## 🎯 Objetivo

- **Preservar original**: `minuta.txt` nunca é alterado
- **Versões por sessão**: Cada sessão gera `minuta{session_id}.txt`
- **Team consolida**: O Team Coordenador (gpt-5.2) faz a redação final
- **Agente #5 fornece contexto**: Lê a minuta original e fornece ao Team
- **Outros agentes contribuem**: Cada um com seu conhecimento específico

## 🔄 Fluxo de Trabalho

```
┌─────────────────────────────────────────────────────────────┐
│ 1. USUÁRIO: Conversa com agentes sobre um tema/capítulo     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 2. AGENTES: Contribuem com conhecimento específico          │
│    - Agente #1 (1997): Versão histórica                     │
│    - Agente #2 (2007): Versão intermediária                 │
│    - Agente #3 (2017): Versão vigente                      │
│    - Agente #4 (Alterações): Mudanças recentes              │
│    - Agente #5 (Minuta V2): Contexto da minuta original     │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 3. TEAM COORDENADOR: Consolida todas as contribuições      │
│    - Analisa respostas de todos os agentes                  │
│    - Identifica gaps e inconsistências                     │
│    - Gera proposta consolidada                             │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 4. USUÁRIO: Solicita geração de minuta atualizada          │
│    POST /sessao/{session_id}/gerar-minuta                   │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 5. AGENTE #5: Fornece contexto completo da minuta original │
│    - Lê minuta.txt via knowledge base                      │
│    - Extrai estrutura, artigos, formatação                │
│    - Fornece ao Team como contexto base                    │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 6. TEAM COORDENADOR: Gera minuta atualizada                │
│    - Recebe: minuta original (Agente #5)                  │
│    - Recebe: consolidação da sessão                        │
│    - Recebe: contribuições dos outros agentes             │
│    - Gera: minuta completa atualizada                      │
└─────────────────────────────────────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────────────┐
│ 7. SISTEMA: Salva arquivo minuta{session_id}.txt           │
│    - Exemplo: minuta01.txt, minuta02.txt, etc.             │
│    - Local: files/regulamentos/minutas_sessao/             │
└─────────────────────────────────────────────────────────────┘
```

## 📁 Estrutura de Arquivos

```
tre-go-minuta-builder-v2/
├── files/
│   └── regulamentos/
│       ├── minuta.txt                    # ← ORIGINAL (nunca alterado)
│       └── minutas_sessao/               # ← NOVO diretório
│           ├── minuta01.txt              # Minuta da sessão 01
│           ├── minuta02.txt              # Minuta da sessão 02
│           └── minuta{session_id}.txt    # Minuta da sessão N
├── backend/
│   ├── agents.py                         # ← MODIFICAR: Adicionar método gerar_minuta_atualizada()
│   ├── minuta_generator.py              # ← NOVO: Gerenciador de geração de minutas
│   └── api.py                            # ← MODIFICAR: Adicionar endpoint
```

## 🔧 Componentes a Implementar

### 1. `MinutaGenerator` (novo arquivo)

Classe responsável por:
- Ler a minuta original (`minuta.txt`)
- Coordenar geração com Team + Agente #5
- Salvar arquivo `minuta{session_id}.txt`
- Validar estrutura e formatação

### 2. Modificações no `TeamCoordenador`

Adicionar método:
```python
async def gerar_minuta_atualizada(
    self,
    minuta_original: str,      # Contexto do Agente #5
    consolidacao: AnaliseEvolutiva,  # Consolidação da sessão
    instrucoes_usuario: Optional[str] = None
) -> str:
    """
    Gera minuta atualizada baseada em:
    - Minuta original (fornecida pelo Agente #5)
    - Consolidação da sessão
    - Contribuições dos agentes
    """
```

### 3. Modificações no `AgenteEspecialista` (Agente #5)

Adicionar método para fornecer contexto completo:
```python
async def fornecer_contexto_minuta_completa(self) -> str:
    """
    Fornece contexto completo da minuta original.
    Lê todo o arquivo minuta.txt e retorna estruturado.
    """
```

### 4. Novo Endpoint na API

```python
@router.post("/sessao/{session_id}/gerar-minuta")
async def gerar_minuta_atualizada(
    session_id: str,
    instrucoes: Optional[str] = None
):
    """
    Gera minuta atualizada baseada nas interações da sessão.
    
    Fluxo:
    1. Obtém sessão e consolidação
    2. Agente #5 fornece contexto da minuta original
    3. Team gera minuta atualizada
    4. Salva como minuta{session_id}.txt
    """
```

### 5. WebSocket Handler (opcional)

```python
async def handle_gerar_minuta(
    websocket: WebSocket,
    session_id: str,
    instrucoes: Optional[str]
):
    """
    Handler WebSocket para gerar minuta atualizada.
    Envia progresso em tempo real.
    """
```

## 📝 Instruções do Team para Redação

O Team Coordenador precisa de instruções específicas para redação:

```python
instructions_redacao = [
    "## Modo de Redação de Minuta:",
    "",
    "Quando solicitado para gerar uma minuta atualizada:",
    "",
    "1. **Base**: Use a minuta original (fornecida pelo Agente #5) como base estrutural",
    "",
    "2. **Aplicar Alterações**:",
    "   - Incorpore as alterações propostas na consolidação da sessão",
    "   - Mantenha estrutura, numeração e formatação original",
    "   - Aplique apenas as mudanças discutidas e consolidadas",
    "",
    "3. **Preservar Formato**:",
    "   - Mantenha formatação de artigos, parágrafos, incisos",
    "   - Preserve estrutura de títulos e capítulos",
    "   - Mantenha estilo normativo (linguagem jurídica)",
    "",
    "4. **Validação**:",
    "   - Verifique que todas as alterações foram aplicadas",
    "   - Garanta que não há quebras de estrutura",
    "   - Confirme que numeração está correta",
    "",
    "5. **Output**:",
    "   - Retorne o texto COMPLETO da minuta atualizada",
    "   - Não retorne apenas as alterações",
    "   - Mantenha todo o conteúdo original + alterações aplicadas",
]
```

## 🔐 Segurança e Validação

### Validações Necessárias:

1. **Estrutura**: Verificar que artigos, parágrafos, incisos estão corretos
2. **Numeração**: Garantir sequência correta de artigos
3. **Formatação**: Manter padrão de formatação normativa
4. **Completude**: Verificar que não há conteúdo perdido

### Backup Automático:

- Antes de gerar, fazer backup da minuta original (se necessário)
- Manter histórico de versões geradas
- Permitir comparação entre versões

## 📊 Exemplo de Uso

```python
# 1. Usuário conversa com agentes
# 2. Team consolida
# 3. Usuário solicita geração

POST /sessao/abc123/gerar-minuta
{
    "instrucoes": "Aplicar todas as alterações consolidadas sobre Diretoria Geral"
}

# Resposta:
{
    "arquivo": "files/regulamentos/minutas_sessao/minuta_abc123.txt",
    "tamanho": 1042,
    "linhas": 1042,
    "alteracoes_aplicadas": 15,
    "timestamp": "2026-01-07T23:00:00"
}
```

## 🎯 Benefícios desta Arquitetura

1. ✅ **Segurança**: Original nunca é alterado
2. ✅ **Rastreabilidade**: Cada sessão gera sua própria versão
3. ✅ **Comparação**: Permite comparar versões diferentes
4. ✅ **Reversão**: Sempre pode voltar ao original
5. ✅ **Colaboração**: Múltiplas sessões podem trabalhar em paralelo
6. ✅ **Histórico**: Mantém histórico de todas as versões geradas

## 🚀 Próximos Passos

1. Implementar `MinutaGenerator`
2. Modificar `TeamCoordenador` com método de redação
3. Adicionar método no `AgenteEspecialista` (Agente #5)
4. Criar endpoint na API
5. Adicionar validações e testes
6. Documentar uso no README
