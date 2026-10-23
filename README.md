# ControlCred

Sistema web completo em Flask para gestão de empréstimos pessoais, clientes, pagamentos, cobranças e dashboard financeiro.

## Requisitos

```bash
pip install -r requirements.txt
```

## Como rodar

```bash
python app.py
```

ou

```bash
python start_app.py
```

## Estrutura

- `app.py`
- `templates/`
- `static/`
- `uploads/`
- `backups/`
- `requirements.txt`
- `README.md`

## Recursos principais

- Login com perfis Admin e Funcionário
- Dashboard com cards e gráficos em barra
- Cadastro completo de clientes com anexos
- Busca por nome, CPF e telefone
- Empréstimos com vencimento mensal
- Regras de pagar hoje, atraso e multa diária de R$ 20
- Pagamentos com renovação, quitação e negociações
- Cobrança via WhatsApp
- Exclusão protegida por perfil
- Backups automáticos e manuais com exportação Excel
- Interface responsiva para desktop e celular

## Observações

- O total emprestado é a soma dos contratos cadastrados e só reduz quando um empréstimo é excluído.
- Renovação não cria novo contrato.
- Ao excluir um pagamento, o empréstimo volta ao estado anterior salvo no histórico do pagamento.
- A pasta `uploads/` guarda anexos de clientes.
- As pastas `backups/db` e `backups/excel` guardam o histórico de backups.

## Preparação para Vercel (sem publicação)

O projeto pode ser servido como Flask Function no Vercel, mas a hospedagem não
deve usar o arquivo SQLite local. Configure um PostgreSQL persistente em
`DATABASE_URL` e um bucket **privado** no Supabase Storage para anexos. O
Vercel não recebe o `controlcred.db`, a pasta `uploads/` nem backups locais;
isso é filtrado por `.vercelignore` e `vercel.json`. Os arquivos estáticos
servidos pelo Vercel ficam em `public/static/`; ao atualizar CSS, JavaScript,
logo ou favicon, sincronize-os com `static/` antes da futura publicação:

```bash
cp -a static/. public/static/
```

### Rodar e validar localmente

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python start_app.py
```

Abra `http://127.0.0.1:5000`. Sem `DATABASE_URL`, o app usa SQLite local. Para
isolar uma cópia de dados durante testes, defina `LOCAL_DATA_DIR` para uma
pasta separada.

### Preparar dados para hospedagem

1. Crie um PostgreSQL vazio e um bucket privado no Supabase Storage.
   Para `DATABASE_URL`, prefira a URL do pooler de conexões do provedor, própria
   para funções serverless.
2. Configure `DATABASE_URL`, `SECRET_KEY`, `STORAGE_BACKEND=supabase`,
   `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` e
   `SUPABASE_STORAGE_BUCKET` no ambiente local de preparação.
3. Faça uma cópia de segurança do SQLite. Migre a cópia com:

   ```bash
   python migrate_sqlite_to_postgres.py /caminho/para/controlcred.db
   ```

4. Revise os arquivos locais antes de transferi-los. O comando de transferência
   precisa da opção explícita `--upload`:

   ```bash
   python migrate_uploads_to_supabase.py /caminho/para/uploads --upload
   ```

5. Antes de qualquer futura publicação, configure senhas fortes em
   `INITIAL_ADMIN_PASSWORD` e `INITIAL_TENANT_ADMIN_PASSWORD`, use uma
   `SECRET_KEY` aleatória e configure os mesmos valores nas variáveis de
   ambiente do Vercel. Se algum desses usuários ainda estiver com `123456`, o
   primeiro acesso online troca a senha usando esses valores; sem eles, o
   acesso é bloqueado. O schema não é inicializado automaticamente por padrão
   (`AUTO_INIT_DB=0`).

O painel de backups locais fica desativado no Vercel; configure e confira os
backups do provedor PostgreSQL antes de disponibilizar dados reais. Nunca
versione `.env`, bancos SQLite, anexos ou cópias de segurança. Configure as
credenciais administrativas com senhas próprias antes de liberar acesso.


## Atualização visual

- login redesenhado
- sidebar responsiva com botão de backup
- ficha do cliente com preview de imagens e bloco PDF
- listas mobile em formato de cards
- máscaras de CPF, telefone e CEP em JavaScript


## SaaS multi-tenant

O sistema suporta tenants, assinatura, branding por tenant e alertas
compartilhados por CPF. Em desenvolvimento local, configure credenciais
administrativas próprias antes de inicializar um banco novo.
