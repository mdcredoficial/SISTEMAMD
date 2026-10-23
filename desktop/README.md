# ControlCred para Windows

Este aplicativo abre o ControlCred online em uma janela própria do Windows. Ele
usa a mesma conta, banco de dados Supabase e arquivos do site; precisa de conexão
com a internet e não mantém uma cópia local dos dados.

## Gerar o instalador no Linux

Na pasta `desktop`:

```bash
npm ci
npm run dist:win
```

O instalador Windows x64 será criado em `desktop/dist/`. Para compilar o instalador
NSIS no Linux, o electron-builder usa Wine.

## Desenvolvimento

```bash
npm install
npm start
```

O aplicativo sempre se conecta a `https://sistemamd.vercel.app`.
