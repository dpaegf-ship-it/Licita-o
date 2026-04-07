# Automação de Peças Documentais de Licitação

Este projeto automatiza a geração de documentos com **fidelidade aos seus modelos** (sem alterar a estrutura do texto-base), apenas substituindo placeholders `{{campo}}` pelos dados da licitação atual.  
Para etapas como **Folder/Programação**, também aceita arquivo pronto da empresa (`.pdf`, `.jpg`, `.jpeg`, `.png`) e apenas copia para a pasta de saída.

## O que foi pensado para o seu cenário

- Você mantém seus modelos oficiais e seu rito processual.
- O script gera os documentos respeitando a ordem do rito.
- É possível consultar a próxima etapa pendente para você enviar o próximo modelo.
- O gerador valida se todos os campos exigidos pelo modelo existem no JSON de dados.
- Para anexos visuais (folder), o sistema mantém o arquivo exatamente como recebido.

## Estrutura

- `scripts/gerar_pecas.py`: gerador principal
- `modelos/`: seus modelos `.md`
- `dados/exemplo.json`: exemplo com os **Modelos 01, 02, 03, 04 e 05**
- `dados/rito_cmmdo.json`: rito completo baseado na sua lista de etapas
- `saida/`: destino dos documentos gerados (ignorado no git)

## Requisitos

- Python 3.9+

## Aplicativo com cliques (Windows)

Se preferir usar por botões (sem terminal), execute:

```bash
python app_licitacao.py
```

Fluxo no app:
1. **Recarregar rito**
2. **Próxima etapa**
3. **Inserir arquivos da etapa** (anexo ou modelo)
4. **Gerar etapa**
5. **Gerar ZIP final**

## 1) Descobrir próxima etapa para envio de modelo

```bash
python3 scripts/gerar_pecas.py \
  --modelos modelos \
  --rito dados/rito_cmmdo.json \
  --proxima-etapa
```

## 2) Gerar documentos conforme rito

```bash
python3 scripts/gerar_pecas.py \
  --dados dados/exemplo.json \
  --modelos modelos \
  --saida saida \
  --rito dados/rito_cmmdo.json
```

## 3) Gerar apenas uma etapa específica

```bash
python3 scripts/gerar_pecas.py \
  --dados dados/exemplo.json \
  --modelos modelos \
  --saida saida \
  --rito dados/rito_cmmdo.json \
  --etapa "01 - Termo de Abertura"
```

## 4) Levantar placeholders dos modelos (inventário)

```bash
python3 scripts/gerar_pecas.py \
  --modelos modelos \
  --inventario-placeholders saida/inventario_placeholders.json
```

> Observação: o inventário considera apenas arquivos textuais (`.md` e `.txt`). Anexos como PDF/JPEG não possuem placeholders.

> Dica: para itens anexos (ex.: **03 - Folder/Programação** e **06 - Portaria Responsáveis**), mantenha o arquivo em PDF/JPEG/PNG no `modelos/`; o sistema copiará o anexo sem alteração.  
> A etapa 06 pode receber mais de um anexo (ex.: `06_portaria_responsaveis.pdf` e `06_ficha_cadastral_portaria.pdf`).

## Formato dos placeholders

- `{{campo}}`
- `{{objeto.subcampo}}` (campos aninhados)

Exemplos:
- `{{numero_processo}}`
- `{{assunto}}`
- `{{autoridade_nome}}`
